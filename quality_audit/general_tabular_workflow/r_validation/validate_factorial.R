# Independent reference for MakeMyFigure's factorial ANOVA — base R only.
#
# Nothing here calls statsmodels or shares code with the Python implementation.
#   * Type II SS: computed from first principles as nested-model comparisons —
#     SS(T) = RSS(all terms not containing T) - RSS(that model + T)
#     (the definition car::Anova(type = 2) implements).
#   * Type III SS: drop1(fit, . ~ ., test = "F") on a fit with sum-to-zero
#     contrasts (options(contrasts = c("contr.sum", "contr.poly"))).
#   * Coefficients / SE / t / P / 95% CI: summary(lm) and confint(lm), sum contrasts.
#   * Estimability: aliased coefficients (NA), residual df, constant response,
#     complete confounding — reported so the Python refusals can be compared.
#
# Usage: Rscript validate_factorial.R <fixtures_dir> <out_dir>
args <- commandArgs(trailingOnly = TRUE)
fx <- args[[1]]; out <- args[[2]]
options(contrasts = c("contr.sum", "contr.poly"), digits = 17)
cases <- read.csv(file.path(fx, "cases.csv"), stringsAsFactors = FALSE)

split1 <- function(s) if (is.na(s) || s == "") character(0) else strsplit(s, ";", fixed = TRUE)[[1]]

anova_rows <- list(); coef_rows <- list(); design_rows <- list()
for (i in seq_len(nrow(cases))) {
  cs <- cases[i, ]
  d <- read.csv(file.path(fx, paste0(cs$dataset, ".csv")), stringsAsFactors = FALSE,
                na.strings = c("", "NA"))
  fac <- split1(cs$factors); cov <- split1(cs$covariates)
  d <- d[complete.cases(d[, c(cs$response, fac, cov)]), ]
  for (f in fac) d[[f]] <- factor(d[[f]], levels = sort(unique(d[[f]])))
  rhs <- paste(fac, collapse = if (cs$interactions == "full") " * " else " + ")
  if (length(cov)) rhs <- paste(c(rhs, cov), collapse = " + ")
  form <- as.formula(paste(cs$response, "~", rhs))
  fit <- lm(form, data = d)
  aliased <- sum(is.na(coef(fit)))
  y <- d[[cs$response]]
  constant <- isTRUE(all.equal(min(y), max(y)))
  confounded <- FALSE
  if (length(fac) >= 2) for (a in fac) for (b in fac) if (a < b) {
    tb <- table(d[[a]], d[[b]]) > 0
    if (all(rowSums(tb) == 1) && all(colSums(tb) == 1)) confounded <- TRUE
  }
  max_rows_per_colony <- if ("colony_id" %in% names(d)) max(table(d$colony_id)) else 1
  design_rows[[i]] <- data.frame(case_id = cs$case_id, n_used = nrow(d), residual_df = fit$df.residual,
                                 aliased_coefficients = aliased, constant_response = constant,
                                 confounded = confounded, max_rows_per_colony = max_rows_per_colony)
  if (aliased > 0 || fit$df.residual <= 0 || constant) next

  labs <- attr(terms(fit), "term.labels")
  rss_full <- deviance(fit); df_res <- fit$df.residual
  parts <- lapply(labs, function(t) strsplit(t, ":", fixed = TRUE)[[1]])
  contains <- function(big, small) all(small %in% big)
  if (cs$ss_type == 2) {
    for (k in seq_along(labs)) {
      keep <- labs[!vapply(parts, contains, logical(1), small = parts[[k]])]
      f0 <- if (length(keep)) reformulate(keep, response = cs$response) else
        as.formula(paste(cs$response, "~ 1"))
      m0 <- lm(f0, data = d); m1 <- update(m0, paste(". ~ . +", labs[k]))
      ss <- deviance(m0) - deviance(m1); dfk <- m0$df.residual - m1$df.residual
      Fv <- (ss / dfk) / (rss_full / df_res)
      anova_rows[[length(anova_rows) + 1]] <- data.frame(
        case_id = cs$case_id, term = labs[k], df = dfk, sum_sq = ss, F = Fv,
        p_value = pf(Fv, dfk, df_res, lower.tail = FALSE), residual_df = df_res)
    }
  } else {
    dr <- drop1(fit, . ~ ., test = "F")
    for (t in labs) {
      anova_rows[[length(anova_rows) + 1]] <- data.frame(
        case_id = cs$case_id, term = t, df = dr[t, "Df"], sum_sq = dr[t, "Sum of Sq"],
        F = dr[t, "F value"], p_value = dr[t, "Pr(>F)"], residual_df = df_res)
    }
  }
  sm <- summary(fit)$coefficients; ci <- confint(fit, level = 0.95)
  coef_rows[[length(coef_rows) + 1]] <- data.frame(
    case_id = cs$case_id, position = seq_len(nrow(sm)) - 1L, r_name = rownames(sm),
    estimate = sm[, 1], std_error = sm[, 2], t = sm[, 3], p_value = sm[, 4],
    ci_low = ci[, 1], ci_high = ci[, 2])
}
wr <- function(x, f) write.csv(do.call(rbind, x), file.path(out, f), row.names = FALSE)
wr(anova_rows, "r_anova.csv"); wr(coef_rows, "r_coefficients.csv"); wr(design_rows, "r_design.csv")
cat("R", R.version.string, "\n", file = file.path(out, "r_version.txt"))
