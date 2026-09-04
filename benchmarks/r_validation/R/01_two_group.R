source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(effectsize) })
hedges_J <- function(n) 1 - 3 / (4 * n - 9)                 # MakeMyFigure's J (documented convention)
cliffs <- function(a, b) { m <- outer(a, b, "-"); (sum(m > 0) - sum(m < 0)) / (length(a) * length(b)) }
for (ds in c("A_two_group_normal", "B_two_group_unequal_var", "C_two_group_ties", "D_two_group_small_n", "E_two_group_one_constant")) {
  d <- read_syn(paste0(ds, ".csv")); lv <- levels_first_seen(d$group)
  a <- d$value[d$group == lv[1]]; b <- d$value[d$group == lv[2]]; comp <- paste(lv[1], lv[2], sep = "|")
  # Student
  s <- tryCatch(t.test(a, b, var.equal = TRUE), error = function(e) NULL)
  if (!is.null(s)) {
    n1 <- length(a); n2 <- length(b); sp <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / (n1 + n2 - 2))
    emit_many(ds, "students_t", comp, statistic = s$statistic, df = s$parameter, p_value = s$p.value,
              estimate = diff(rev(s$estimate)), ci_low = s$conf.int[1], ci_high = s$conf.int[2],
              effect_size = (mean(a) - mean(b)) / sp, n_total = n1 + n2)
    emit(ds, "students_t", comp, "effectsize_pkg.cohens_d", tryCatch(effectsize::cohens_d(a, b, pooled_sd = TRUE)$Cohens_d, error = function(e) NA))
  } else note(ds, "students_t", comp, "t.test error (degenerate)")
  # Welch
  w <- tryCatch(t.test(a, b), error = function(e) NULL)
  if (!is.null(w)) {
    n1 <- length(a); n2 <- length(b); sp <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / (n1 + n2 - 2))
    emit_many(ds, "welch_t", comp, statistic = w$statistic, df = w$parameter, p_value = w$p.value,
              estimate = diff(rev(w$estimate)), ci_low = w$conf.int[1], ci_high = w$conf.int[2],
              effect_size = (mean(a) - mean(b)) / sp * hedges_J(n1 + n2), n_total = n1 + n2)
    emit(ds, "welch_t", comp, "effectsize_pkg.hedges_g", tryCatch(effectsize::hedges_g(a, b, pooled_sd = TRUE)$Hedges_g, error = function(e) NA))
  } else note(ds, "welch_t", comp, "t.test error (degenerate)")
  # Mann-Whitney: R default, and convention-matched to scipy 'auto' (exact iff both n<=8 and no ties, else asymptotic + continuity)
  mw_def <- suppressWarnings(wilcox.test(a, b))
  ties <- any(duplicated(c(a, b))); use_exact <- (length(a) <= 8 && length(b) <= 8 && !ties)
  mw <- suppressWarnings(wilcox.test(a, b, exact = use_exact, correct = TRUE))
  emit_many(ds, "mann_whitney", comp, statistic = mw$statistic, p_value = mw$p.value,
            effect_size = 2 * mw$statistic / (length(a) * length(b)) - 1, n_total = length(a) + length(b))
  emit(ds, "mann_whitney", comp, "R_default.p_value", mw_def$p.value)
  emit(ds, "mann_whitney", comp, "R_only.cliffs_delta", cliffs(a, b))
  emit(ds, "mann_whitney", comp, "asymptotic_no_correction.p_value", suppressWarnings(wilcox.test(a, b, exact = FALSE, correct = FALSE))$p.value)
  note(ds, "mann_whitney", comp, sprintf("scipy-matched exact=%s (ties=%s); R default exact=%s", use_exact, ties, (length(a) < 50 && length(b) < 50 && !ties)))
}
flush_stats("statistics_R_01_two_group.csv")
