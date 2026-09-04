source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
for (ds in c("F_paired_normal", "G_paired_zeros_ties")) {
  d <- read_syn(paste0(ds, ".csv")); lv <- levels_first_seen(d$condition)
  a <- d$value[d$condition == lv[1]][match(unique(d$subject), d$subject[d$condition == lv[1]])]
  b <- d$value[d$condition == lv[2]][match(unique(d$subject), d$subject[d$condition == lv[2]])]
  comp <- paste(lv[1], lv[2], sep = "|"); dif <- a - b
  t <- t.test(a, b, paired = TRUE)
  emit_many(ds, "paired_t", comp, statistic = t$statistic, df = t$parameter, p_value = t$p.value,
            estimate = t$estimate, ci_low = t$conf.int[1], ci_high = t$conf.int[2],
            effect_size = mean(dif) / sd(dif), n_total = length(a))
  # Wilcoxon signed-rank. scipy: zero_method='wilcox' (drop zeros), correction=False, method auto
  # (exact when n<=50 and no ties among |d| after zero removal, else normal approx WITHOUT continuity).
  dz <- dif[dif != 0]; ties <- any(duplicated(abs(dz))); use_exact <- (length(dz) <= 50 && !ties)
  w_def <- suppressWarnings(wilcox.test(a, b, paired = TRUE))
  w <- suppressWarnings(wilcox.test(a, b, paired = TRUE, exact = use_exact, correct = FALSE))
  r <- rank(abs(dz)); wpos <- sum(r[dz > 0]); wneg <- sum(r[dz < 0])
  emit_many(ds, "wilcoxon", comp, statistic = min(wpos, wneg), p_value = w$p.value,
            effect_size = (wpos - wneg) / (wpos + wneg), n_total = length(a))
  emit(ds, "wilcoxon", comp, "R_only.V_positive_ranks", w$statistic)
  emit(ds, "wilcoxon", comp, "R_default.p_value", w_def$p.value)
  emit(ds, "wilcoxon", comp, "R_only.n_nonzero", length(dz))
  note(ds, "wilcoxon", comp, sprintf("zeros dropped=%d; ties in |d|=%s; scipy-matched exact=%s", sum(dif == 0), ties, use_exact))
}
flush_stats("statistics_R_02_paired.csv")
