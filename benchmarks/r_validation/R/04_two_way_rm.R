source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(car) })
hedges_J <- function(n) 1 - 3 / (4 * n - 9)
for (ds in c("J_two_way_balanced", "K_two_way_unbalanced")) {
  d <- read_syn(paste0(ds, ".csv")); d$A <- factor(d$genotype, levels = levels_first_seen(d$genotype))
  d$B <- factor(d$treatment, levels = levels_first_seen(d$treatment))
  fit <- lm(value ~ A * B, data = d); an <- car::Anova(fit, type = 2)   # type II SS (statsmodels anova_lm typ=2)
  sst <- sum(an[["Sum Sq"]])
  terms <- c(A = "genotype", B = "treatment", `A:B` = "genotype x treatment")
  for (t in names(terms)) emit_many(ds, "two_way_anova", terms[[t]], statistic = an[t, "F value"], df = an[t, "Df"],
                                    df2 = an["Residuals", "Df"], p_value = an[t, "Pr(>F)"], effect_size = an[t, "Sum Sq"] / sst,
                                    `extra.sum_sq` = an[t, "Sum Sq"], n_total = nrow(d))
  an1 <- anova(fit)  # type I for reference
  for (t in names(terms)) emit(ds, "two_way_anova", terms[[t]], "typeI.p_value", an1[t, "Pr(>F)"])
  # within-x Welch family: for each genotype level, compare treatment levels (BH not applied: correction 'none')
  for (xl in levels(d$A)) {
    sub <- d[d$A == xl, ]; lv <- levels(d$B); a <- sub$value[sub$B == lv[1]]; b <- sub$value[sub$B == lv[2]]
    w <- t.test(a, b); n1 <- length(a); n2 <- length(b); sp <- sqrt(((n1 - 1) * var(a) + (n2 - 1) * var(b)) / (n1 + n2 - 2))
    emit_many(ds, "welch_t", paste0(xl, ":", lv[1], "|", lv[2]), statistic = w$statistic, df = w$parameter, p_value = w$p.value,
              estimate = diff(rev(w$estimate)), ci_low = w$conf.int[1], ci_high = w$conf.int[2],
              effect_size = (mean(a) - mean(b)) / sp * hedges_J(n1 + n2), n_total = n1 + n2)
  }
}
# repeated measures: univariate within-subject ANOVA (no sphericity correction), as AnovaRM reports
d <- read_syn("L_repeated_measures.csv"); d$time <- factor(d$time, levels = levels_first_seen(d$time)); d$subject <- factor(d$subject)
fit <- aov(value ~ time + Error(subject / time), data = d); s <- summary(fit)
w <- s[["Error: subject:time"]][[1]]
emit_many("L_repeated_measures", "rm_anova", "all", statistic = w["time", "F value"], df = w["time", "Df"], df2 = w["Residuals", "Df"],
          p_value = w["time", "Pr(>F)"], `extra.n_subjects` = nlevels(d$subject), `extra.n_levels` = nlevels(d$time), n_total = nrow(d))
flush_stats("statistics_R_04_two_way_rm.csv")
