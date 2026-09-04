source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(rstatix); library(dunn.test) })
hedges_J <- function(n) 1 - 3 / (4 * n - 9)
cliffs <- function(a, b) { m <- outer(a, b, "-"); (sum(m > 0) - sum(m < 0)) / (length(a) * length(b)) }
for (spec in list(c("H_three_groups_balanced", "dose", "response"), c("I_five_groups_unbalanced", "group", "score"))) {
  ds <- spec[1]; g <- spec[2]; v <- spec[3]; d <- read_syn(paste0(ds, ".csv"))
  lv <- levels_first_seen(d[[g]]); d$grp <- factor(d[[g]], levels = lv); y <- d[[v]]
  # one-way ANOVA (classic, equal variances) + eta^2 / omega^2
  fit <- aov(y ~ grp, data = d); s <- summary(fit)[[1]]
  ssb <- s["grp", "Sum Sq"]; ssw <- s["Residuals", "Sum Sq"]; dfb <- s["grp", "Df"]; dfw <- s["Residuals", "Df"]
  emit_many(ds, "one_way_anova", "all", statistic = s["grp", "F value"], df = dfb, df2 = dfw, p_value = s["grp", "Pr(>F)"],
            effect_size = ssb / (ssb + ssw), n_total = length(y))
  emit(ds, "one_way_anova", "all", "extra.omega_squared", (ssb - dfb * (ssw / dfw)) / (ssb + ssw + ssw / dfw))
  emit(ds, "one_way_anova", "all", "oneway_test_var_equal.p_value", oneway.test(y ~ grp, data = d, var.equal = TRUE)$p.value)
  # Kruskal-Wallis + epsilon^2
  k <- kruskal.test(y ~ grp, data = d); n <- length(y); kk <- length(lv)
  emit_many(ds, "kruskal_wallis", "all", statistic = k$statistic, df = k$parameter, p_value = k$p.value,
            effect_size = (k$statistic - kk + 1) / (n - kk), n_total = n)
  # Dunn: manual (shared tie correction, two-sided normal) + rstatix + dunn.test
  r <- rank(y); N <- n; cnt <- table(y); C <- sum(cnt^3 - cnt); sig <- N * (N + 1) / 12 - C / (12 * (N - 1))
  mr <- tapply(r, d$grp, mean); ns <- tapply(r, d$grp, length)
  dt <- rstatix::dunn_test(d, as.formula(paste(v, "~ grp")), p.adjust.method = "BH")
  dtt <- capture.output(dd <- dunn.test::dunn.test(y, d$grp, method = "none", kw = FALSE, table = FALSE, list = FALSE))
  pr_raw <- c()
  for (i in 1:(kk - 1)) for (j in (i + 1):kk) {
    z <- (mr[i] - mr[j]) / sqrt(sig * (1 / ns[i] + 1 / ns[j])); p <- 2 * pnorm(-abs(z)); comp <- paste(lv[i], lv[j], sep = "|")
    pr_raw <- c(pr_raw, p)
    cd <- cliffs(y[d$grp == lv[i]], y[d$grp == lv[j]])
    emit_many(ds, "dunn", comp, statistic = z, p_value = p, effect_size = cd, n_total = ns[i] + ns[j])
    emit_many(ds, "dunn_bh", comp, statistic = z, p_value = p, effect_size = cd, n_total = ns[i] + ns[j])
    row <- dt[(dt$group1 == lv[i] & dt$group2 == lv[j]) | (dt$group1 == lv[j] & dt$group2 == lv[i]), ]
    if (nrow(row)) { emit(ds, "dunn", comp, "rstatix.p_value", row$p); emit(ds, "dunn", comp, "rstatix.statistic_abs", abs(row$statistic));
                     emit(ds, "dunn_bh", comp, "rstatix.adjusted_p_value_BH", row$p.adj) }
    cmp <- dd$comparisons; idx <- which(cmp == paste(lv[i], "-", lv[j]) | cmp == paste(lv[j], "-", lv[i]))
    if (length(idx)) emit(ds, "dunn", comp, "dunn.test.two_sided_p", 2 * dd$P[idx])
  }
  padj <- p.adjust(pr_raw, "BH"); ii <- 0
  for (i in 1:(kk - 1)) for (j in (i + 1):kk) { ii <- ii + 1; emit(ds, "dunn_bh", paste(lv[i], lv[j], sep = "|"), "adjusted_p_value", padj[ii]) }
  # pairwise Welch family with corrections (t.test per pair, then p.adjust across the family)
  praw <- c(); comps <- c(); stats <- list()
  for (i in 1:(kk - 1)) for (j in (i + 1):kk) {
    a <- y[d$grp == lv[i]]; b <- y[d$grp == lv[j]]; w <- t.test(a, b); comp <- paste(lv[i], lv[j], sep = "|")
    n1 <- length(a); n2 <- length(b); sp <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / (n1 + n2 - 2))
    praw <- c(praw, w$p.value); comps <- c(comps, comp)
    for (corr in c("welch_t_benjamini_hochberg", "welch_t_holm", "welch_t_bonferroni"))
      emit_many(ds, corr, comp, statistic = w$statistic, df = w$parameter, p_value = w$p.value,
                estimate = diff(rev(w$estimate)), ci_low = w$conf.int[1], ci_high = w$conf.int[2],
                effect_size = (mean(a) - mean(b)) / sp * hedges_J(n1 + n2), n_total = n1 + n2)
  }
  for (m in c(welch_t_benjamini_hochberg = "BH", welch_t_holm = "holm", welch_t_bonferroni = "bonferroni")) NULL
  for (nm in names(c(welch_t_benjamini_hochberg = "BH", welch_t_holm = "holm", welch_t_bonferroni = "bonferroni"))) {
    m <- c(welch_t_benjamini_hochberg = "BH", welch_t_holm = "holm", welch_t_bonferroni = "bonferroni")[[nm]]
    pa <- p.adjust(praw, m); for (q in seq_along(comps)) emit(ds, nm, comps[q], "adjusted_p_value", pa[q])
  }
}
flush_stats("statistics_R_03_multi_group.csv")
