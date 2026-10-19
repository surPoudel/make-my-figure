# Reference console output for MakeMyFigure's R-style report: print(summary(aov(...))) and
# print(TukeyHSD(...)), base R only, written verbatim to text files.
# Usage: Rscript validate_anova_report.R <plant_growth_facets.csv> <unbalanced.csv> <out_dir>
args <- commandArgs(trailingOnly = TRUE)
plants <- read.csv(args[[1]], stringsAsFactors = TRUE)
plants$Month <- factor(plants$Month)
u <- read.csv(args[[2]], stringsAsFactors = TRUE)
out <- args[[3]]
young <- plants[plants$Age == "Young", ]
cases <- list(
  young_two_way = list(f = Growth_cm ~ Month * Nitrogen_Concentration, d = young, name = "young"),
  plants_one_way = list(f = Growth_cm ~ Nitrogen_Concentration, d = plants, name = "plants"),
  plants_three_way = list(f = Growth_cm ~ Month * Nitrogen_Concentration * Age, d = plants, name = "plants"),
  unbalanced_two_way = list(f = quantity ~ treatment * time, d = u, name = "u"),
  unbalanced_reversed = list(f = quantity ~ time * treatment, d = u, name = "u"))
for (nm in names(cases)) {
  cs <- cases[[nm]]
  d <- cs$d
  assign(cs$name, d)
  m <- eval(bquote(aov(.(cs$f), data = .(as.name(cs$name)))))
  txt <- c(capture.output(print(summary(m))), capture.output(print(TukeyHSD(m))))
  writeLines(txt, file.path(out, paste0(nm, ".txt")))
}
cat(R.version.string, "\n", file = file.path(out, "r_version.txt"))
# ptukey / qtukey reference (studentized range), for the port in statistics/_tukey_dist.py
options(digits = 17)
q <- c(0.5, 1, 2.5, 3.7, 5, 8, 12)
lines <- character()
for (k in c(2, 3, 6, 12, 48)) for (df in c(5, 44, 108, 192, 1000))
  lines <- c(lines, paste(k, df, format(qtukey(0.95, k, df), digits = 17),
                          paste(format(ptukey(q, k, df, lower.tail = FALSE), digits = 17), collapse = " ")))
writeLines(lines, file.path(out, "ptukey_qtukey.txt"))
