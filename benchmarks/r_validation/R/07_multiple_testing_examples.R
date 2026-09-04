source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(survival); library(car) })
rows <- list()
for (ds in c("U_pvalues", "V_pvalues_with_na")) {
  p <- read_syn(paste0(ds, ".csv"))$p
  for (m in c(bonferroni = "bonferroni", holm = "holm", benjamini_hochberg = "BH")) {
    pa <- p.adjust(p, method = m)   # n defaults to number of non-NA p-values
    rows[[length(rows) + 1]] <- data.frame(dataset_id = ds, method = names(which(c(bonferroni = "bonferroni", holm = "holm", benjamini_hochberg = "BH") == m)),
                                           index = seq_along(p), p = p, p_adj = pa)
  }
}
write.csv(do.call(rbind, rows), file.path(OUTR, "multiple_testing.csv"), row.names = FALSE)

# ---- bundled statistics examples (examples/statistics/<slug>) -------------------------------
EX <- file.path(REPO, "examples", "statistics")
hedges_J <- function(n) 1 - 3 / (4 * n - 9)
two_group <- function(ds, test, a, b, comp) {
  n1 <- length(a); n2 <- length(b); sp <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / (n1 + n2 - 2))
  if (test == "welch_t") { w <- t.test(a, b); emit_many(ds, test, comp, statistic = w$statistic, df = w$parameter, p_value = w$p.value,
                                                         estimate = diff(rev(w$estimate)), ci_low = w$conf.int[1], ci_high = w$conf.int[2],
                                                         effect_size = (mean(a) - mean(b)) / sp * hedges_J(n1 + n2), n_total = n1 + n2); return(w$p.value) }
  if (test == "students_t") { w <- t.test(a, b, var.equal = TRUE); emit_many(ds, test, comp, statistic = w$statistic, df = w$parameter, p_value = w$p.value,
                                                                                estimate = diff(rev(w$estimate)), effect_size = (mean(a) - mean(b)) / sp); return(w$p.value) }
  if (test == "mann_whitney") { ties <- any(duplicated(c(a, b))); ex <- (n1 <= 8 && n2 <= 8 && !ties)
    w <- suppressWarnings(wilcox.test(a, b, exact = ex, correct = TRUE)); emit_many(ds, test, comp, statistic = w$statistic, p_value = w$p.value,
                                                                                    effect_size = 2 * w$statistic / (n1 * n2) - 1, n_total = n1 + n2); return(w$p.value) }
}
for (slug in list.dirs(EX, full.names = FALSE, recursive = FALSE)) {
  ss <- fromJSON(file.path(EX, slug, "statsspec.json")); ps <- fromJSON(file.path(EX, slug, "plotspec.json"))
  d <- read.csv(file.path(EX, slug, "data.csv"), check.names = FALSE); ds <- paste0("ex_", slug); mp <- ps$mapping
  test <- ss$test
  gcol <- if (!is.null(ss$group_column)) ss$group_column else mp$x
  vcol <- if (!is.null(ss$value_column)) ss$value_column else mp$y
  if (test %in% c("welch_t", "students_t", "mann_whitney")) {
    sub_col <- if (!is.null(ss$subgroup_column)) ss$subgroup_column else NULL
    if (!is.null(sub_col) && identical(ss$comparison_mode, "within_x")) {
      praw <- c(); comps <- c()
      for (xl in levels_first_seen(d[[gcol]])) { sub <- d[d[[gcol]] == xl, ]; lv <- levels_first_seen(sub[[sub_col]])
        for (i in 1:(length(lv) - 1)) for (j in (i + 1):length(lv)) { comp <- paste0(xl, ":", lv[i], "|", lv[j])
          praw <- c(praw, two_group(ds, test, sub[[vcol]][sub[[sub_col]] == lv[i]], sub[[vcol]][sub[[sub_col]] == lv[j]], comp)); comps <- c(comps, comp) } }
      if (identical(ss$correction, "benjamini_hochberg")) { pa <- p.adjust(praw, "BH"); for (q in seq_along(comps)) emit(ds, test, comps[q], "adjusted_p_value", pa[q]) }
    } else {
      lv <- levels_first_seen(d[[gcol]])
      for (i in 1:(length(lv) - 1)) for (j in (i + 1):length(lv))
        two_group(ds, test, d[[vcol]][d[[gcol]] == lv[i]], d[[vcol]][d[[gcol]] == lv[j]], paste(lv[i], lv[j], sep = "|"))
    }
  } else if (test == "paired_t") {
    lv <- levels_first_seen(d[[gcol]]); sc <- ss$subject_column; ids <- unique(d[[sc]])
    a <- d[[vcol]][d[[gcol]] == lv[1]][match(ids, d[[sc]][d[[gcol]] == lv[1]])]; b <- d[[vcol]][d[[gcol]] == lv[2]][match(ids, d[[sc]][d[[gcol]] == lv[2]])]
    t <- t.test(a, b, paired = TRUE); dif <- a - b
    emit_many(ds, test, paste(lv[1], lv[2], sep = "|"), statistic = t$statistic, df = t$parameter, p_value = t$p.value, estimate = t$estimate,
              ci_low = t$conf.int[1], ci_high = t$conf.int[2], effect_size = mean(dif) / sd(dif), n_total = length(a))
  } else if (test == "one_way_anova") {
    d$grp <- factor(d[[gcol]], levels = levels_first_seen(d[[gcol]])); s <- summary(aov(d[[vcol]] ~ grp, data = d))[[1]]
    ssb <- s["grp", "Sum Sq"]; ssw <- s["Residuals", "Sum Sq"]
    emit_many(ds, test, "all", statistic = s["grp", "F value"], df = s["grp", "Df"], df2 = s["Residuals", "Df"], p_value = s["grp", "Pr(>F)"], effect_size = ssb / (ssb + ssw), n_total = nrow(d))
    if (isTRUE(ss$posthoc)) { lv <- levels(d$grp); praw <- c(); comps <- c()
      for (i in 1:(length(lv) - 1)) for (j in (i + 1):length(lv)) { comp <- paste(lv[i], lv[j], sep = "|"); comps <- c(comps, comp)
        praw <- c(praw, two_group(ds, ss$posthoc_test, d[[vcol]][d$grp == lv[i]], d[[vcol]][d$grp == lv[j]], comp)) }
      pa <- p.adjust(praw, "BH"); for (q in seq_along(comps)) emit(ds, ss$posthoc_test, comps[q], "adjusted_p_value", pa[q]) }
  } else if (test == "rm_anova") {
    d$w <- factor(d[[gcol]], levels = levels_first_seen(d[[gcol]])); d$s <- factor(d[[ss$subject_column]])
    s <- summary(aov(d[[vcol]] ~ w + Error(s / w), data = d)); w <- s[["Error: s:w"]][[1]]
    emit_many(ds, test, "all", statistic = w["w", "F value"], df = w["w", "Df"], df2 = w["Residuals", "Df"], p_value = w["w", "Pr(>F)"], n_total = nrow(d))
  } else if (test == "two_way_anova") {
    d$A <- factor(d[[gcol]], levels = levels_first_seen(d[[gcol]])); d$B <- factor(d[[ss$subgroup_column]], levels = levels_first_seen(d[[ss$subgroup_column]]))
    an <- car::Anova(lm(d[[vcol]] ~ A * B, data = d), type = 2); sst <- sum(an[["Sum Sq"]])
    terms <- c(A = gcol, B = ss$subgroup_column, `A:B` = paste(gcol, "x", ss$subgroup_column))
    for (t in names(terms)) emit_many(ds, test, terms[[t]], statistic = an[t, "F value"], df = an[t, "Df"], df2 = an["Residuals", "Df"], p_value = an[t, "Pr(>F)"], effect_size = an[t, "Sum Sq"] / sst, n_total = nrow(d))
  } else if (test == "pearson") {
    p <- cor.test(d[[ss$x_column]], d[[ss$y_column]]); emit_many(ds, test, "all", statistic = p$estimate, df = p$parameter, p_value = p$p.value, estimate = p$estimate, ci_low = p$conf.int[1], ci_high = p$conf.int[2], effect_size = p$estimate^2, n_total = nrow(d))
  } else if (test %in% c("chi_square", "fishers_exact")) {
    r <- factor(d[[ss$row_column]], levels = sort(unique(d[[ss$row_column]]))); c <- factor(d[[ss$col_column]], levels = sort(unique(d[[ss$col_column]]))); tab <- table(r, c)
    if (test == "chi_square") { cs <- suppressWarnings(chisq.test(tab)); emit_many(ds, test, "all", statistic = cs$statistic, df = cs$parameter, p_value = cs$p.value, effect_size = sqrt(cs$statistic / (sum(tab) * (min(dim(tab)) - 1))), n_total = sum(tab)) }
    else { fe <- fisher.test(tab); emit_many(ds, test, "all", p_value = fe$p.value, n_total = sum(tab)); if (all(dim(tab) == 2)) { o <- (tab[1, 1] * tab[2, 2]) / (tab[1, 2] * tab[2, 1]); emit_many(ds, test, "all", estimate = o, statistic = o, effect_size = o) } }
  } else if (test == "logrank") {
    d$g <- factor(d[[gcol]], levels = levels_first_seen(d[[gcol]])); sd <- survdiff(Surv(d[[ss$time_column]], d[[ss$event_column]]) ~ g, data = d)
    emit_many(ds, test, "all", statistic = sd$chisq, df = nlevels(d$g) - 1, p_value = pchisq(sd$chisq, nlevels(d$g) - 1, lower.tail = FALSE), n_total = nrow(d))
  }
}
flush_stats("statistics_R_07_examples.csv")
