# Independent reference for MakeMyFigure's model diagnostics - base R only (plot.lm's quantities).
#   fitted(), residuals(), rstandard(), hatvalues(), cooks.distance(), lowess(f = 2/3, iter = 3),
#   row names of the model frame (row numbers of the full table), qqnorm positions (ppoints).
# Usage: Rscript validate_diagnostics.R <plant_growth_facets.csv> <unbalanced.csv> <out_dir>
args <- commandArgs(trailingOnly = TRUE)
options(digits = 17, contrasts = c("contr.sum", "contr.poly"))
d <- read.csv(args[[1]], stringsAsFactors = FALSE); out <- args[[3]]
y <- d[d$Age == "Young", ]
fit <- lm(Growth_cm ~ factor(Month) * factor(Nitrogen_Concentration), data = y)
q <- qqnorm(rstandard(fit), plot.it = FALSE)
write.csv(data.frame(row = as.integer(rownames(model.frame(fit))), fitted = fitted(fit), resid = residuals(fit),
                     rstd = rstandard(fit), hat = hatvalues(fit), cook = cooks.distance(fit), qq_x = q$x),
          file.path(out, "young_balanced.csv"), row.names = FALSE)
lw <- lowess(fitted(fit), residuals(fit))
lw3 <- lowess(fitted(fit), sqrt(abs(rstandard(fit))))
write.csv(data.frame(x = lw$x, resid_y = lw$y, scale_y = lw3$y), file.path(out, "young_lowess.csv"), row.names = FALSE)
u <- read.csv(args[[2]], stringsAsFactors = FALSE)
fu <- lm(quantity ~ factor(treatment) * factor(time) + body_size_mm, data = u)
write.csv(data.frame(row = as.integer(rownames(model.frame(fu))), fitted = fitted(fu), resid = residuals(fu),
                     rstd = rstandard(fu), hat = hatvalues(fu), cook = cooks.distance(fu)),
          file.path(out, "unbalanced_ancova.csv"), row.names = FALSE)
lw2 <- lowess(hatvalues(fu), rstandard(fu))
write.csv(data.frame(x = lw2$x, y = lw2$y), file.path(out, "unbalanced_leverage_lowess.csv"), row.names = FALSE)
cat(R.version.string, "\n", file = file.path(out, "r_version.txt"))
