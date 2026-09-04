source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
# QC metrics recomputed from their definitions. Skewness = biased g1 = m3 / m2^(3/2) (scipy.stats.skew bias=True).
# MAD here is the RAW median absolute deviation (constant = 1), because the app's rule is |x - med| > k * rawMAD.
skew_g1 <- function(x) { x <- x[is.finite(x)]; if (length(x) < 3 || sd(x) == 0) return(0); m <- mean(x); mean((x - m)^3) / (mean((x - m)^2))^1.5 }
qc <- function(m, mad_k = 3.5) {
  fin <- m[is.finite(m)]; total <- length(m)
  cs <- colSums(m, na.rm = TRUE); fv <- apply(m, 1, function(x) { x <- x[is.finite(x)]; if (length(x) == 0) NA else mean((x - mean(x))^2) })  # numpy nanvar ddof=0
  rawmad <- function(v) { md <- median(v); r <- median(abs(v - md)); if (r == 0) 1 else r }
  out_s <- character(0); if (ncol(m) > 3) { md <- median(cs); r <- rawmad(cs); out_s <- colnames(m)[abs(cs - md) > mad_k * r] }
  out_f <- character(0); if (nrow(m) > 10) { md <- median(fv); r <- rawmad(fv); out_f <- head(rownames(m)[fv - md > mad_k * r], 50) }
  per_skew <- apply(m, 2, function(x) { x <- x[is.finite(x)]; if (length(x) > 2 && sd(x) > 0) skew_g1(x) else NA }); per_skew <- per_skew[!is.na(per_skew)]
  list(n_features = nrow(m), n_samples = ncol(m), missing_values = sum(is.na(m)), zero_fraction = sum(fin == 0) / total,
       negative_value_fraction = sum(fin < 0) / total, min = min(fin), max = max(fin), mean = mean(fin), median = median(fin),
       integer_like = all(fin %% 1 == 0), variance_summary = list(min = min(fv, na.rm = TRUE), median = median(fv, na.rm = TRUE), max = max(fv, na.rm = TRUE)),
       sample_total_summary = list(min = min(cs), median = median(cs), max = max(cs)),
       sample_median_summary = { cm <- apply(m, 2, median, na.rm = TRUE); list(min = min(cm), median = median(cm), max = max(cm)) },
       skewness_summary = list(overall = skew_g1(fin), median_per_sample = if (length(per_skew)) median(per_skew) else skew_g1(fin)),
       outlier_samples = out_s, outlier_features = out_f, looks_log_scale = (min(fin) < 0 || max(fin) < 40))
}
for (spec in list(c("W_count_matrix.tsv", "gene_id", "W"), c("X_intensity_matrix_missing.tsv", "protein", "X"), c("Y_log_matrix_negatives.tsv", "feature", "Y"), c("Z_small_integer_matrix_ties.tsv", "id", "Z"))) {
  d <- read_syn(spec[1]); m <- as.matrix(d[, setdiff(names(d), c(spec[2], "biotype")), drop = FALSE]); rownames(m) <- d[[spec[2]]]
  write_json(qc(m), file.path(OUTR, paste0("qc__", spec[3], ".json")), auto_unbox = TRUE, digits = NA, pretty = TRUE)
}
cat("09 done\n")
