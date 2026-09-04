source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma) })
RSEM <- file.path(REPO, "GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt")
raw <- read.delim(RSEM, check.names = FALSE); annot <- c("geneID", "geneSymbol", "bioType", "annotationLevel"); cols <- setdiff(names(raw), annot)
m <- as.matrix(raw[, cols]); rownames(m) <- raw$geneID
cpm_raw <- sweep(m, 2, colSums(m), "/") * 1e6; keep <- rowSums(cpm_raw > 1) >= 4; mf <- m[keep, ]; ids <- rownames(mf); lib <- colSums(mf)
grp <- read.csv(file.path(META, "rsem_sample_groups.csv")); g <- factor(grp$group[match(cols, grp$sample)], levels = c("Parental", "ORP5/8 KD", "ATP11A/C KD", "CDC50A KD"))
put <- function(tag, x) write_matrix(tag, ids, "geneID", x)
# edgeR / limma handle non-integer expected counts (fractional counts are allowed in edgeR; DESeq2 does not).
put("RSEM__cpm", cpm(mf, lib.size = lib, log = FALSE))
put("RSEM__logcpm_prior0.5", cpm(mf, lib.size = lib, log = TRUE, prior.count = 0.5))
put("RSEM__logcpm_prior2", cpm(mf, lib.size = lib, log = TRUE, prior.count = 2))
nf <- calcNormFactors(mf, method = "TMM"); write.csv(data.frame(sample = cols, norm_factor = nf), file.path(OUTR, "tmm_factors__RSEM.csv"), row.names = FALSE)
put("RSEM__tmm_cpm", cpm(mf, lib.size = lib * nf, log = FALSE))
dge <- calcNormFactors(DGEList(counts = mf), method = "TMM"); design <- model.matrix(~g); v <- voom(dge, design)
put("RSEM__voom_logcpm", v$E)
put("RSEM__log2_pc1", log2(mf + 1)); put("RSEM__total_sum_1e6", sweep(mf, 2, lib, "/") * 1e6)
uq <- apply(mf, 2, quantile, .75, type = 7); put("RSEM__upper_quartile", sweep(mf, 2, uq / median(uq), "/"))
md <- apply(mf, 2, median); put("RSEM__median_scale", sweep(mf, 2, md / median(md), "/"))
# alternative edgeR normalisations for context
write.csv(data.frame(sample = cols, TMM = nf, TMMwsp = calcNormFactors(mf, method = "TMMwsp"), RLE = calcNormFactors(mf, method = "RLE"), upperquartile = calcNormFactors(mf, method = "upperquartile")),
          file.path(OUTR, "rsem_norm_factor_methods.csv"), row.names = FALSE)
# PCA + clustering on voom E (prcomp, centred, unscaled)
X <- t(v$E); p <- prcomp(X, center = TRUE, scale. = FALSE)
write.csv(data.frame(sample = rownames(X), PC1 = p$x[, 1], PC2 = p$x[, 2]), file.path(OUTR, "pca__RSEM_voom.csv"), row.names = FALSE)
write_json(list(explained_variance_ratio = (p$sdev^2 / sum(p$sdev^2))[1:10]), file.path(OUTR, "pca__RSEM_voom.json"), digits = NA, auto_unbox = TRUE)
for (mm in list(c("average", "euclidean"), c("complete", "euclidean"), c("ward", "euclidean"), c("average", "correlation"))) {
  d <- if (mm[2] == "euclidean") dist(X) else as.dist(1 - cor(t(X))); h <- hclust(d, method = if (mm[1] == "ward") "ward.D2" else mm[1]); cp <- as.matrix(cophenetic(h)); rows <- list(); k <- 0
  for (i in 1:(ncol(v$E) - 1)) for (j in (i + 1):ncol(v$E)) { k <- k + 1; rows[[k]] <- data.frame(a = cols[i], b = cols[j], cophenetic = cp[i, j]) }
  write.csv(do.call(rbind, rows), file.path(OUTR, paste0("cluster__RSEM_voom_samples__", mm[1], "_", mm[2], ".csv")), row.names = FALSE)
  write.csv(data.frame(height = sort(h$height)), file.path(OUTR, paste0("cluster_heights__RSEM_voom_samples__", mm[1], "_", mm[2], ".csv")), row.names = FALSE)
}
L <- cpm(mf, lib.size = lib, log = TRUE, prior.count = 0.5); XL <- t(L); pL <- prcomp(XL, center = TRUE, scale. = FALSE)
write.csv(data.frame(sample = rownames(XL), PC1 = pL$x[, 1], PC2 = pL$x[, 2]), file.path(OUTR, "pca__RSEM_logcpm.csv"), row.names = FALSE)
write_json(list(explained_variance_ratio = (pL$sdev^2 / sum(pL$sdev^2))[1:10]), file.path(OUTR, "pca__RSEM_logcpm.json"), digits = NA, auto_unbox = TRUE)
for (mm in list(c("average", "euclidean"), c("complete", "euclidean"), c("ward", "euclidean"), c("average", "correlation"))) {
  d <- if (mm[2] == "euclidean") dist(XL) else as.dist(1 - cor(t(XL))); h <- hclust(d, method = if (mm[1] == "ward") "ward.D2" else mm[1]); cp <- as.matrix(cophenetic(h)); rows <- list(); k <- 0
  for (i in 1:(ncol(L) - 1)) for (j in (i + 1):ncol(L)) { k <- k + 1; rows[[k]] <- data.frame(a = cols[i], b = cols[j], cophenetic = cp[i, j]) }
  write.csv(do.call(rbind, rows), file.path(OUTR, paste0("cluster__RSEM_logcpm_samples__", mm[1], "_", mm[2], ".csv")), row.names = FALSE)
  write.csv(data.frame(height = sort(h$height)), file.path(OUTR, paste0("cluster_heights__RSEM_logcpm_samples__", mm[1], "_", mm[2], ".csv")), row.names = FALSE)
}
saveRDS(list(v = v, design = design, g = g, dge = dge, mf = mf, cols = cols, L = L), file.path(OUTR, "rsem_objects.rds"))
cat("13 done\n")
