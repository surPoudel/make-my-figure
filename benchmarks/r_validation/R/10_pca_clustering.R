source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma) })
pca_out <- function(tag, m_features_by_samples) {
  X <- t(m_features_by_samples)                          # samples x features
  X[is.na(X)] <- 0
  p <- prcomp(X, center = TRUE, scale. = FALSE)
  write.csv(data.frame(sample = rownames(X), PC1 = p$x[, 1], PC2 = p$x[, 2]), file.path(OUTR, paste0("pca__", tag, ".csv")), row.names = FALSE)
  ev <- p$sdev^2 / sum(p$sdev^2)
  write_json(list(explained_variance_ratio = ev[1:min(10, length(ev))]), file.path(OUTR, paste0("pca__", tag, ".json")), digits = NA, auto_unbox = TRUE)
}
clust_out <- function(tag, m, labels, method, metric) {
  # scipy: pdist(metric) + linkage(method). R: dist()/1-cor + hclust. 'ward' in scipy = Ward on Euclidean distances = R 'ward.D2'.
  X <- m; if (any(is.na(X))) { rm <- rowMeans(X, na.rm = TRUE); rm[is.na(rm)] <- 0; idx <- which(is.na(X), arr.ind = TRUE); X[idx] <- rm[idx[, 1]] }
  d <- switch(metric, euclidean = dist(X, "euclidean"), cityblock = dist(X, "manhattan"),
              correlation = as.dist(1 - cor(t(X))), cosine = { n <- sqrt(rowSums(X^2)); as.dist(1 - (X %*% t(X)) / outer(n, n)) })
  h <- hclust(d, method = if (method == "ward") "ward.D2" else method)
  cp <- as.matrix(cophenetic(h)); rows <- list(); k <- 0
  for (i in 1:(length(labels) - 1)) for (j in (i + 1):length(labels)) { k <- k + 1; rows[[k]] <- data.frame(a = labels[i], b = labels[j], cophenetic = cp[i, j]) }
  write.csv(do.call(rbind, rows), file.path(OUTR, paste0("cluster__", tag, "__", method, "_", metric, ".csv")), row.names = FALSE)
  write.csv(data.frame(height = sort(h$height)), file.path(OUTR, paste0("cluster_heights__", tag, "__", method, "_", metric, ".csv")), row.names = FALSE)
}
# W voom logCPM (limma) -> PCA + sample clustering
d <- read_syn("W_count_matrix.tsv"); m <- as.matrix(d[, setdiff(names(d), c("gene_id", "biotype"))]); rownames(m) <- d$gene_id
dge <- calcNormFactors(DGEList(counts = m), method = "TMM"); grp <- factor(ifelse(grepl("^A_", colnames(m)), "A", "B"))
E <- voom(dge, model.matrix(~grp))$E
pca_out("W_voom", E)
L <- cpm(m, lib.size = colSums(m), log = TRUE, prior.count = 0.5)   # plain log2-CPM: Class-A input
pca_out("W_logcpm", L)
for (mm in list(c("average", "euclidean"), c("complete", "euclidean"), c("ward", "euclidean"), c("average", "correlation"))) clust_out("W_logcpm_samples", t(L), colnames(L), mm[1], mm[2])
for (mm in list(c("average", "euclidean"), c("complete", "euclidean"), c("single", "euclidean"), c("ward", "euclidean"), c("average", "correlation"))) clust_out("W_voom_samples", t(E), colnames(E), mm[1], mm[2])
# Y
d <- read_syn("Y_log_matrix_negatives.tsv"); m <- as.matrix(d[, setdiff(names(d), "feature")]); rownames(m) <- d$feature
pca_out("Y", m)
for (mm in list(c("average", "euclidean"), c("complete", "euclidean"), c("single", "euclidean"), c("ward", "euclidean"), c("average", "correlation"), c("complete", "cityblock"), c("average", "cosine"))) {
  clust_out("Y_features", m, rownames(m), mm[1], mm[2]); clust_out("Y_samples", t(m), colnames(m), mm[1], mm[2]) }
cat("10 done\n")
