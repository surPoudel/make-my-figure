source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma); library(DESeq2); library(survival); library(car); library(rstatix); library(effectsize); library(MASS); library(dunn.test); library(pROC) })
sink(file.path(ROOT, "results", "R_sessionInfo.txt")); print(sessionInfo()); cat("\nR_HOME:", R.home(), "\n"); sink()
cat("15 done\n")
