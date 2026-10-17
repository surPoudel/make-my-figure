# Independent reference for MakeMyFigure's assumption checks - base R only.
#   * Shapiro-Wilk: shapiro.test().
#   * Levene, median-centred (Brown-Forsythe; car::leveneTest's default), from its
#     definition: one-way ANOVA of |y - median(y in its group)| on the groups.
#   * Model residuals: residuals(lm(y ~ A * B)) with the factors as factors.
# Usage: Rscript validate_assumptions.R <plant_growth_facets.csv> <unbalanced.csv> <out.csv>
args <- commandArgs(trailingOnly = TRUE)
options(digits = 17)
plants <- read.csv(args[[1]], stringsAsFactors = FALSE)
unbal <- read.csv(args[[2]], stringsAsFactors = FALSE)
rows <- list()
add <- function(case, method, stat, p, df1 = NA, df2 = NA)
  rows[[length(rows) + 1]] <<- data.frame(case = case, method = method, statistic = stat, p_value = p,
                                          df1 = df1, df2 = df2)
sw <- function(case, x) { t <- shapiro.test(x); add(case, "shapiro", unname(t$statistic), t$p.value) }
lev <- function(case, y, g) {
  g <- factor(g); d <- abs(y - ave(y, g, FUN = median)); a <- anova(lm(d ~ g))
  add(case, "levene", a[1, "F value"], a[1, "Pr(>F)"], a[1, "Df"], a[2, "Df"])
}
# 1 factorial residuals, plants, Month x Nitrogen within Age = Young
y <- plants[plants$Age == "Young", ]
fit <- lm(Growth_cm ~ factor(Month) * factor(Nitrogen_Concentration), data = y)
sw("young_factorial_residuals", residuals(fit))
lev("young_factorial_levene", y$Growth_cm, interaction(y$Month, y$Nitrogen_Concentration))
# 2 whole plant table, three factors
fit3 <- lm(Growth_cm ~ factor(Month) * factor(Nitrogen_Concentration) * factor(Age), data = plants)
sw("all_three_way_residuals", residuals(fit3))
lev("all_three_way_levene", plants$Growth_cm, interaction(plants$Month, plants$Nitrogen_Concentration, plants$Age))
# 3 one-way: residuals = value - group mean, Nitrogen
r1 <- plants$Growth_cm - ave(plants$Growth_cm, plants$Nitrogen_Concentration)
sw("oneway_residuals", r1)
lev("oneway_levene", plants$Growth_cm, plants$Nitrogen_Concentration)
# 4 per-group Shapiro, Month 10 x Nitrogen (t-test groups)
m10 <- plants[plants$Month == 10, ]
for (lv in c("Low N", "Medium N", "High N")) sw(paste0("m10_group_", lv), m10$Growth_cm[m10$Nitrogen_Concentration == lv])
# 5 unbalanced design, treatment x time
u <- unbal[complete.cases(unbal[, c("quantity", "treatment", "time")]), ]
fu <- lm(quantity ~ factor(treatment) * factor(time), data = u)
sw("unbalanced_residuals", residuals(fu))
lev("unbalanced_levene", u$quantity, interaction(u$treatment, u$time))
write.csv(do.call(rbind, rows), args[[3]], row.names = FALSE)
cat(R.version.string, "\n")
