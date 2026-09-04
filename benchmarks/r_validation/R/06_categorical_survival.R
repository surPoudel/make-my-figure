source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(survival) })
for (spec in list(c("O_contingency_2x2", "arm", "response"), c("P_contingency_3x4", "subtype", "grade"), c("Q_contingency_small_expected", "arm", "response"))) {
  ds <- spec[1]; d <- read_syn(paste0(ds, ".csv"))
  # pandas.crosstab sorts levels lexicographically -> match with factor(sort(unique()))
  r <- factor(d[[spec[2]]], levels = sort(unique(d[[spec[2]]]))); c <- factor(d[[spec[3]]], levels = sort(unique(d[[spec[3]]])))
  tab <- table(r, c); n <- sum(tab)
  cs <- suppressWarnings(chisq.test(tab))            # Yates only for 2x2 (as scipy correction=True)
  V <- sqrt(cs$statistic / (n * (min(dim(tab)) - 1)))
  emit_many(ds, "chi_square", "all", statistic = cs$statistic, df = cs$parameter, p_value = cs$p.value, effect_size = V, n_total = n,
            `extra.expected_min` = min(cs$expected))
  emit(ds, "chi_square", "all", "no_correction.statistic", suppressWarnings(chisq.test(tab, correct = FALSE))$statistic)
  emit(ds, "chi_square", "all", "no_correction.p_value", suppressWarnings(chisq.test(tab, correct = FALSE))$p.value)
  fe <- fisher.test(tab)
  emit_many(ds, "fishers_exact", "all", p_value = fe$p.value, n_total = n)
  if (all(dim(tab) == 2)) {
    emit(ds, "fishers_exact", "all", "estimate", (tab[1, 1] * tab[2, 2]) / (tab[1, 2] * tab[2, 1]))  # sample OR (scipy convention)
    emit(ds, "fishers_exact", "all", "effect_size", (tab[1, 1] * tab[2, 2]) / (tab[1, 2] * tab[2, 1]))
    emit(ds, "fishers_exact", "all", "statistic", (tab[1, 1] * tab[2, 2]) / (tab[1, 2] * tab[2, 1]))
    emit(ds, "fishers_exact", "all", "R_only.conditional_MLE_odds_ratio", fe$estimate)
    emit(ds, "fishers_exact", "all", "R_only.or_ci_low", fe$conf.int[1]); emit(ds, "fishers_exact", "all", "R_only.or_ci_high", fe$conf.int[2])
  }
}
for (ds in c("R_survival_two_groups", "S_survival_three_groups")) {
  d <- read_syn(paste0(ds, ".csv")); lv <- levels_first_seen(d$group); d$g <- factor(d$group, levels = lv)
  sd <- survdiff(Surv(time, event) ~ g, data = d, rho = 0)
  emit_many(ds, "logrank", "all", statistic = sd$chisq, df = length(lv) - 1, p_value = pchisq(sd$chisq, length(lv) - 1, lower.tail = FALSE), n_total = nrow(d))
  for (i in seq_along(lv)) { emit(ds, "logrank", "all", paste0("extra.observed_events.", lv[i]), sd$obs[i]); emit(ds, "logrank", "all", paste0("extra.expected_events.", lv[i]), sd$exp[i]) }
  for (ties in c("breslow", "efron")) {
    # coxph.control(eps = 1e-12): default eps = 1e-9 leaves ~1e-9 relative differences vs statsmodels PHReg
    cx <- coxph(Surv(time, event) ~ g, data = d, ties = ties, control = coxph.control(eps = 1e-12, iter.max = 100)); co <- summary(cx)$coefficients; ci <- summary(cx)$conf.int
    for (k in 2:length(lv)) {
      comp <- paste(lv[k], lv[1], sep = "|"); rn <- paste0("g", lv[k])
      if (ties == "breslow") emit_many(ds, "cox_ph", comp, statistic = co[rn, "z"], p_value = co[rn, "Pr(>|z|)"], estimate = co[rn, "exp(coef)"],
                                       effect_size = co[rn, "exp(coef)"], ci_low = ci[rn, "lower .95"], ci_high = ci[rn, "upper .95"], n_total = nrow(d))
      else emit_many(ds, "cox_ph", comp, efron.estimate = co[rn, "exp(coef)"], efron.p_value = co[rn, "Pr(>|z|)"])
    }
  }
}
flush_stats("statistics_R_06_categorical_survival.csv")
