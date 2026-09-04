source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(MASS) })
for (ds in c("M_linear_xy", "N_monotone_nonlinear_ties")) {
  d <- read_syn(paste0(ds, ".csv")); x <- d$x; y <- d$y; n <- length(x)
  p <- cor.test(x, y, method = "pearson")
  # MakeMyFigure reports statistic = r and effect_size = R^2 for Pearson; R's t is kept as context.
  emit_many(ds, "pearson", "all", statistic = p$estimate, df = p$parameter, p_value = p$p.value, estimate = p$estimate,
            ci_low = p$conf.int[1], ci_high = p$conf.int[2], effect_size = p$estimate^2, n_total = n)
  emit(ds, "pearson", "all", "R_only.t_statistic", p$statistic)
  s_def <- suppressWarnings(cor.test(x, y, method = "spearman"))                 # R default (exact/AS89 when no ties)
  rho <- cor(x, y, method = "spearman"); t_rho <- rho * sqrt((n - 2) / (1 - rho^2))
  emit_many(ds, "spearman", "all", estimate = rho, effect_size = rho, p_value = 2 * pt(-abs(t_rho), n - 2), n_total = n,
            statistic = rho)  # scipy spearmanr: statistic = rho, t-approximation p-value
  emit(ds, "spearman", "all", "R_only.t_statistic", t_rho)
  emit(ds, "spearman", "all", "R_default.p_value", s_def$p.value)
  emit(ds, "spearman", "all", "R_default.S", s_def$statistic)
  fit <- lm(y ~ x); co <- summary(fit)$coefficients; ci <- confint(fit)
  emit_many(ds, "linear_regression", "all", statistic = co["x", "Estimate"], df = n - 2, p_value = co["x", "Pr(>|t|)"],
            estimate = co["x", "Estimate"], ci_low = ci["x", 1], ci_high = ci["x", 2], effect_size = summary(fit)$r.squared, n_total = n,
            `extra.intercept` = co["(Intercept)", "Estimate"], `extra.stderr` = co["x", "Std. Error"],
            `R_only.intercept_stderr` = co["(Intercept)", "Std. Error"], `extra.pearson_r` = cor(x, y))
  emit(ds, "linear_regression", "all", "R_only.t_statistic", co["x", "t value"])
}
# GLM: statsmodels GLM with add_constant; families gaussian / binomial(logit) / poisson(log) / NB(alpha fixed = 1) / Gamma(log)
d <- read_syn("T_glm_predictors.csv")
fams <- list(gaussian = list(y = "y_gauss", f = gaussian()), binomial = list(y = "y_binom", f = binomial()),
             poisson = list(y = "y_pois", f = poisson()), gamma = list(y = "y_gamma", f = Gamma(link = "log")),
             negativebinomial = list(y = "y_negbin", f = MASS::negative.binomial(theta = 1)))
for (nm in names(fams)) {
  # glm.control(epsilon = 1e-14): R's default IRLS stop rule (relative deviance change < 1e-8) halts one or two iterations
  # before statsmodels' default; the default-tolerance fit is reported as context (R_default.*).
  fo <- as.formula(paste(fams[[nm]]$y, "~ x1 + x2")); fit <- glm(fo, data = d, family = fams[[nm]]$f, control = glm.control(epsilon = 1e-14, maxit = 200))
  fit0 <- glm(fo, data = d, family = fams[[nm]]$f)
  # statsmodels' GLM fixes scale = 1 for the NegativeBinomial family (dispersion enters only through alpha);
  # R's summary.glm estimates a Pearson dispersion on top of theta. Like-for-like: dispersion = 1 for NB.
  co <- if (nm == "negativebinomial") summary(fit, dispersion = 1)$coefficients else summary(fit)$coefficients
  if (nm == "negativebinomial") { co_est <- summary(fit)$coefficients; for (term in rownames(co_est)) emit("T_glm_predictors", "glm_negativebinomial", if (term == "(Intercept)") "const" else term, "R_default.statistic_estimated_dispersion", co_est[term, 3]) }
  # statsmodels uses the z (normal) distribution for Wald p-values in all families (scale estimated or not);
  # R uses t for gaussian/Gamma (estimated dispersion) and z for binomial/poisson. Emit both.
  for (term in rownames(co)) {
    comp <- if (term == "(Intercept)") "const" else term
    est <- co[term, "Estimate"]; se <- co[term, "Std. Error"]
    emit_many("T_glm_predictors", paste0("glm_", nm), comp, estimate = est, statistic = est / se, p_value = 2 * pnorm(-abs(est / se)),
              ci_low = est - qnorm(0.975) * se, ci_high = est + qnorm(0.975) * se, n_total = nrow(d))
    emit("T_glm_predictors", paste0("glm_", nm), comp, "R_only.stderr", se)
    emit("T_glm_predictors", paste0("glm_", nm), comp, "R_summary.p_value", co[term, 4])
    emit("T_glm_predictors", paste0("glm_", nm), comp, "R_default.estimate", coef(fit0)[term])
    emit("T_glm_predictors", paste0("glm_", nm), comp, "R_default.statistic", coef(summary(fit0))[term, 3])
  }
  emit("T_glm_predictors", paste0("glm_", nm), "model", "R_only.deviance", fit$deviance)
  emit("T_glm_predictors", paste0("glm_", nm), "model", "R_only.aic", fit$aic)
  emit("T_glm_predictors", paste0("glm_", nm), "model", "R_only.dispersion", summary(fit)$dispersion)
  if (nm == "negativebinomial") { nb <- MASS::glm.nb(fo, data = d); emit("T_glm_predictors", "glm_negativebinomial", "model", "glm.nb_theta", nb$theta)
    for (term in rownames(coef(summary(nb)))) emit("T_glm_predictors", "glm_negativebinomial", if (term == "(Intercept)") "const" else term, "glm.nb.estimate", coef(nb)[term]) }
}
flush_stats("statistics_R_05_correlation_regression_glm.csv")
