source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma); library(matrixStats) })
# Reference implementations written from the METHOD DEFINITIONS (not from MakeMyFigure code), using base R /
# Bioconductor where a canonical implementation exists (edgeR cpm/calcNormFactors, limma voom, preprocessCore).
# Where MakeMyFigure documents a convention (e.g. ddof=0 z-scores, 2^k pseudocount), the same convention is applied
# so that the comparison isolates implementation correctness.
load_mat <- function(name, id) { d <- read_syn(name); m <- as.matrix(d[, setdiff(names(d), c(id, "biotype")), drop = FALSE]); rownames(m) <- d[[id]]; list(ids = d[[id]], m = m) }
zscore <- function(m, axis = "row", ddof = 0) {
  f <- function(x) { x <- x; mu <- mean(x, na.rm = TRUE); n <- sum(!is.na(x)); sd <- sqrt(sum((x - mu)^2, na.rm = TRUE) / (n - ddof)); if (!is.finite(sd) || sd == 0) sd <- 1; (x - mu) / sd }
  if (axis == "row") t(apply(m, 1, f)) else if (axis == "column") apply(m, 2, f) else { mu <- mean(m, na.rm = TRUE); n <- sum(!is.na(m)); sd <- sqrt(sum((m - mu)^2, na.rm = TRUE) / (n - ddof)); if (sd == 0) sd <- 1; (m - mu) / sd }
}
robust <- function(m, axis) {
  f <- function(x) { med <- median(x, na.rm = TRUE); q <- quantile(x, c(.25, .75), na.rm = TRUE, type = 7); iqr <- q[2] - q[1]; if (iqr == 0) iqr <- 1; (x - med) / iqr }
  if (axis == "row") t(apply(m, 1, f)) else if (axis == "column") apply(m, 2, f) else { med <- median(m, na.rm = TRUE); q <- quantile(m, c(.25, .75), na.rm = TRUE, type = 7); iqr <- q[2] - q[1]; if (iqr == 0) iqr <- 1; (m - med) / iqr }
}
scale_factor_norm <- function(m, stat) { s <- apply(m, 2, stat); grand <- median(s, na.rm = TRUE); if (grand == 0) grand <- 1; f <- s / grand; f[s == 0] <- NA; sweep(m, 2, f, "/") }
center <- function(m, mode) switch(mode,
  sample_median = sweep(m, 2, apply(m, 2, median, na.rm = TRUE)), feature_mean = sweep(m, 1, rowMeans(m, na.rm = TRUE)),
  feature_median = sweep(m, 1, apply(m, 1, median, na.rm = TRUE)), grand_median = m - median(m, na.rm = TRUE))
log_pc <- function(m, base, pc) { x <- m + pc; r <- if (base == 2) log2(x) else if (base == 10) log10(x) else log(x); r[!is.finite(r)] <- NA; r }
winsor <- function(m, lo = 1, hi = 99) { q <- quantile(m, c(lo, hi) / 100, na.rm = TRUE, type = 7); pmin(pmax(m, q[1]), q[2]) }
impute <- function(m, strategy, constant = 0) { if (strategy == "feature_median") { f <- apply(m, 1, median, na.rm = TRUE); idx <- which(is.na(m), arr.ind = TRUE); m[idx] <- f[idx[, 1]] }
  else if (strategy == "sample_median") { f <- apply(m, 2, median, na.rm = TRUE); idx <- which(is.na(m), arr.ind = TRUE); m[idx] <- f[idx[, 2]] } else m[is.na(m)] <- constant; m }
edger_logcpm <- function(m, lib, prior) { ps <- prior * lib / mean(lib); log2(sweep(sweep(m, 2, ps, "+"), 2, lib + 2 * ps, "/") * 1e6) }

# Quantile normalization. preprocessCore's compiled routine cannot start threads in this sandbox, so the canonical
# reference is limma::normalizeQuantiles (pure R, Bolstad et al. 2003; ties -> average of the target quantiles).
# qn_ordinal reproduces the documented MakeMyFigure convention (ties broken by row order, numpy argsort-of-argsort).
qn_canonical <- function(m) { q <- limma::normalizeQuantiles(m, ties = TRUE); dimnames(q) <- dimnames(m); q }
qn_ordinal <- function(m) { s <- apply(m, 2, sort, na.last = TRUE); ref <- rowMeans(s, na.rm = TRUE)
  out <- m; for (j in seq_len(ncol(m))) { r <- rank(m[, j], ties.method = "first", na.last = "keep"); out[, j] <- ref[r] }; out }
# ---------------- W (counts) ----------------
W <- load_mat("W_count_matrix.tsv", "gene_id"); m <- W$m; lib <- colSums(m)
put <- function(tag, x) write_matrix(tag, W$ids, "gene_id", x)
put("W__total_sum_1e6", sweep(m, 2, lib, "/") * 1e6)
put("W__cpm", edgeR::cpm(m, lib.size = lib, log = FALSE))
put("W__logcpm_prior0.5", edgeR::cpm(m, lib.size = lib, log = TRUE, prior.count = 0.5))
put("W__logcpm_prior2", edgeR::cpm(m, lib.size = lib, log = TRUE, prior.count = 2))
nf <- edgeR::calcNormFactors(m, method = "TMM")
write.csv(data.frame(sample = colnames(m), norm_factor = nf), file.path(OUTR, "tmm_factors__W.csv"), row.names = FALSE)
put("W__tmm_cpm", edgeR::cpm(m, lib.size = lib * nf, log = FALSE))
put("W__tmm_logcpm_prior0.5", edgeR::cpm(m, lib.size = lib * nf, log = TRUE, prior.count = 0.5))
dge <- edgeR::DGEList(counts = m); dge <- edgeR::calcNormFactors(dge, method = "TMM")
grp <- factor(ifelse(grepl("^A_", colnames(m)), "A", "B"), levels = c("A", "B"))
v <- limma::voom(dge, design = model.matrix(~grp))
put("W__voom_logcpm", v$E)                                   # limma voom E = log2-CPM on TMM effective libs, prior 0.5
write.csv(data.frame(gene_id = W$ids, as.data.frame(v$weights)), file.path(OUTR, "voom_weights__W.csv"), row.names = FALSE)
put("W__log2_pc1", log_pc(m, 2, 1)); put("W__log10_pc1", log_pc(m, 10, 1)); put("W__ln_pc1", log_pc(m, exp(1), 1))
put("W__upper_quartile", scale_factor_norm(m, function(x) quantile(x, .75, na.rm = TRUE, type = 7)))
put("W__median_scale", scale_factor_norm(m, function(x) median(x, na.rm = TRUE)))
put("W__quantile", qn_canonical(m)); put("W__quantile_ordinal", qn_ordinal(m))
put("W__sqrt", sqrt(pmax(m, 0))); put("W__arcsinh_cf5", asinh(m / 5)); put("W__winsorize_1_99", winsor(m))
put("W__row_zscore_ddof0", zscore(m, "row", 0)); put("W__zscore_row_ddof1", zscore(m, "row", 1))
put("W__column_zscore_ddof0", zscore(m, "column", 0)); put("W__global_zscore_ddof0", zscore(m, "global", 0)); put("W__standard_scale", zscore(m, "column", 0))
put("W__robust_scale_row", robust(m, "row")); put("W__robust_scale_column", robust(m, "column")); put("W__robust_scale_global", robust(m, "global"))
for (mode in c("sample_median", "feature_mean", "feature_median", "grand_median")) put(paste0("W__center_", mode), center(m, mode))
ctrl <- c("gene0100", "gene0101", "gene0102", "gene0103", "gene0104"); f <- apply(m[ctrl, ], 2, median); put("W__control_features_median_divide", sweep(m, 2, f, "/"))
f <- colMeans(m[ctrl[1:3], ]); put("W__internal_standard_features_mean_subtract", sweep(m, 2, f, "-"))
ref <- apply(m[, c("A_1", "A_2")], 1, median); ref[ref == 0] <- NA; put("W__internal_standard_columns_median_divide", m / ref)
r <- m[, "A_1"]; r[r == 0] <- NA; put("W__reference_sample_A_1_divide", m / r)
keep <- rowMeans(m == 0) <= 0.5 & apply(m, 1, sd) > 0
write.csv(data.frame(gene_id = W$ids[keep]), file.path(OUTR, "filter__W__maxzero0.5_dropconst.csv"), row.names = FALSE)
v100 <- apply(m, 1, var); write.csv(data.frame(gene_id = W$ids[order(-v100)][1:100]), file.path(OUTR, "filter__W__top100var.csv"), row.names = FALSE)

# ---------------- X (intensities with NA) ----------------
X <- load_mat("X_intensity_matrix_missing.tsv", "protein"); m <- X$m
put <- function(tag, x) write_matrix(tag, X$ids, "protein", x)
put("X__log2_pc1", log_pc(m, 2, 1)); put("X__ln_pc1", log_pc(m, exp(1), 1)); put("X__log10_pc1", log_pc(m, 10, 1))
put("X__arcsinh_cf5", asinh(m / 5)); put("X__sqrt", sqrt(pmax(m, 0)))
put("X__median_scale", scale_factor_norm(m, function(x) median(x, na.rm = TRUE)))
put("X__total_sum_1e6", sweep(m, 2, colSums(m, na.rm = TRUE), "/") * 1e6)
put("X__upper_quartile", scale_factor_norm(m, function(x) quantile(x, .75, na.rm = TRUE, type = 7)))
put("X__row_zscore_ddof0", zscore(m, "row", 0)); put("X__column_zscore_ddof0", zscore(m, "column", 0))
put("X__robust_scale_row", robust(m, "row")); put("X__robust_scale_column", robust(m, "column"))
put("X__impute_feature_median", impute(m, "feature_median")); put("X__impute_sample_median", impute(m, "sample_median")); put("X__impute_constant0", impute(m, "constant", 0))
put("X__winsorize_1_99", winsor(m))
put("X__quantile", qn_canonical(m)); put("X__quantile_ordinal", qn_ordinal(m))
put("X__center_sample_median", center(m, "sample_median")); put("X__center_feature_median", center(m, "feature_median"))
write.csv(data.frame(protein = X$ids[rowMeans(is.na(m)) <= 0.1]), file.path(OUTR, "filter__X__maxmissing0.1.csv"), row.names = FALSE)

# ---------------- Y (log-like, negatives) ----------------
Y <- load_mat("Y_log_matrix_negatives.tsv", "feature"); m <- Y$m
put <- function(tag, x) write_matrix(tag, Y$ids, "feature", x)
put("Y__row_zscore_ddof0", zscore(m, "row", 0)); put("Y__zscore_row_ddof1", zscore(m, "row", 1)); put("Y__column_zscore_ddof0", zscore(m, "column", 0))
put("Y__global_zscore_ddof0", zscore(m, "global", 0)); put("Y__standard_scale", zscore(m, "column", 0))
put("Y__center_feature_mean", center(m, "feature_mean")); put("Y__center_grand_median", center(m, "grand_median"))
put("Y__robust_scale_row", robust(m, "row")); put("Y__arcsinh_cf5", asinh(m / 5))
put("Y__quantile", qn_canonical(m)); put("Y__quantile_ordinal", qn_ordinal(m))
put("Y__log2_pc1", log_pc(m, 2, 1))
# heatmap-side scaling (clustering.scale_matrix): log = log1p(clip>=0); zscores ddof 0, sd 0 -> 1
put("Y__heatmap_scale_row_zscore", zscore(m, "row", 0)); put("Y__heatmap_scale_column_zscore", zscore(m, "column", 0))
put("Y__heatmap_scale_center_rows", center(m, "feature_mean")); put("Y__heatmap_scale_log", log1p(pmax(m, 0)))
put("Y__heatmap_scale_log_zscore", zscore(log1p(pmax(m, 0)), "row", 0))

# ---------------- Z (ties, constant row) ----------------
Z <- load_mat("Z_small_integer_matrix_ties.tsv", "id"); m <- Z$m
put <- function(tag, x) write_matrix(tag, Z$ids, "id", x)
put("Z__quantile", qn_canonical(m)); put("Z__quantile_ordinal", qn_ordinal(m))
put("Z__row_zscore_ddof0", zscore(m, "row", 0)); put("Z__robust_scale_row", robust(m, "row"))
put("Z__median_scale", scale_factor_norm(m, function(x) median(x, na.rm = TRUE)))
put("Z__upper_quartile", scale_factor_norm(m, function(x) quantile(x, .75, na.rm = TRUE, type = 7)))
put("Z__total_sum_1e6", sweep(m, 2, colSums(m), "/") * 1e6)
cat("08 done\n")
