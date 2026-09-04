source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(pROC); library(survival) })
EX <- file.path(REPO, "examples", "by_plot_type"); rd <- function(s) read.csv(file.path(EX, s, "data.csv"), check.names = FALSE)
out <- list()
d <- rd("roc"); out$roc_auc <- list(score_model_a = as.numeric(auc(roc(d$true_label, d$score_model_a, quiet = TRUE, direction = "<"))),
                                   score_model_b = as.numeric(auc(roc(d$true_label, d$score_model_b, quiet = TRUE, direction = "<"))))
ap <- function(y, s) { o <- order(-s); y <- y[o]; s <- s[o]; last <- c(which(diff(s) != 0), length(s)); tp <- cumsum(y == 1)[last]; fp <- cumsum(y == 0)[last]
  prec <- tp / (tp + fp); rec <- tp / sum(y == 1); sum(diff(c(0, rec)) * prec) }
d <- rd("precision_recall"); out$average_precision <- list(score_model_a = ap(d$true_label, d$score_model_a), score_model_b = ap(d$true_label, d$score_model_b))
d <- rd("calibration"); out$brier <- mean((d$predicted_prob - d$true_label)^2)
d <- rd("confusion_matrix"); out$accuracy <- mean(d$true_label == d$predicted_label)
d <- rd("bland_altman"); dif <- d$device_A - d$device_B; out$bland_altman <- list(bias = mean(dif), sd_diff = sd(dif), loa_upper = mean(dif) + 1.96 * sd(dif), loa_lower = mean(dif) - 1.96 * sd(dif))
d <- rd("qq"); p <- d$p_value[is.finite(d$p_value) & d$p_value > 0 & d$p_value <= 1]; out$lambda_gc <- qchisq(median(p), 1, lower.tail = FALSE) / qchisq(0.5, 1)
d <- rd("scatter"); out$regression <- list()
for (g in unique(d$group)) { s <- d[d$group == g, ]; f <- lm(y_response ~ x_marker, data = s); co <- summary(f)$coefficients
  out$regression[[g]] <- list(slope = co[2, 1], intercept = co[1, 1], pearson_r = cor(s$x_marker, s$y_response), r_squared = summary(f)$r.squared, p_value = co[2, 4], slope_stderr = co[2, 2], intercept_stderr = co[1, 2], n = nrow(s)) }
d <- rd("kaplan_meier"); out$km <- list()
for (g in unique(d$group)) { s <- d[d$group == g, ]; sf <- survfit(Surv(time_months, event) ~ 1, data = s); out$km[[g]] <- list(time = sf$time, surv = sf$surv) }
d <- rd("dose_response"); names(d)[names(d) == "drug"] <- "group"; names(d)[names(d) == "concentration_uM"] <- "dose"; names(d)[names(d) == "viability_pct"] <- "response"; out$dose_response <- list()
for (g in unique(d$group)) { s <- d[d$group == g, ]
  fit <- tryCatch(nls(response ~ bottom + (top - bottom) / (1 + (dose / ec50)^hill), data = s, start = list(bottom = min(s$response), top = max(s$response), ec50 = median(s$dose), hill = 1),
                      algorithm = "port", lower = c(-Inf, -Inf, min(s$dose) * 1e-3, 0.1), upper = c(Inf, Inf, max(s$dose) * 1e3, 10), control = nls.control(maxiter = 500)), error = function(e) NULL)
  if (!is.null(fit)) out$dose_response[[g]] <- as.list(coef(fit)) }
write_json(out, file.path(OUTR, "plot_derived_R.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
cat("16 done\n")
