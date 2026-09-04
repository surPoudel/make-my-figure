source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma); library(DESeq2) })
o <- readRDS(file.path(OUTR, "rsem_objects.rds")); v <- o$v; g <- o$g; E <- v$E; cols <- o$cols
tt_safe <- function(...) tryCatch(t.test(...), error = function(e) list(statistic = NA_real_, p.value = NA_real_))
tag <- function(x) gsub(" ", "_", gsub("/", "-", x))
# (1) exact-equivalence reference: per-gene Welch t on voom logCPM (KD vs Parental), log2FC = mean_KD - mean_Parental, BH
for (kd in levels(g)[-1]) {
  A <- E[, g == "Parental"]; B <- E[, g == kd]
  res <- t(apply(cbind(A, B), 1, function(x) { a <- x[1:4]; b <- x[5:8]; tt <- tt_safe(b, a); c(tt$statistic, tt$p.value) }))
  out <- data.frame(geneID = rownames(E), log2FoldChange = rowMeans(B) - rowMeans(A), AveExpr = rowMeans(cbind(A, B)), stat = res[, 1], pvalue = res[, 2], padj = p.adjust(res[, 2], "BH"))
  write.csv(out, file.path(OUTR, paste0("de_screen__RSEM_voom__welch_t__", gsub(" ", "_", tag(kd)), "_vs_Parental.csv")), row.names = FALSE)
}
L <- o$L
for (kd in levels(g)[-1]) {
  A <- L[, g == "Parental"]; B <- L[, g == kd]
  res <- t(apply(cbind(A, B), 1, function(x) { a <- x[1:4]; b <- x[5:8]; tt <- tt_safe(b, a); c(tt$statistic, tt$p.value) }))
  out <- data.frame(geneID = rownames(L), log2FoldChange = rowMeans(B) - rowMeans(A), AveExpr = rowMeans(cbind(A, B)), stat = res[, 1], pvalue = res[, 2], padj = p.adjust(res[, 2], "BH"))
  write.csv(out, file.path(OUTR, paste0("de_screen__RSEM_logcpm__welch_t__", gsub(" ", "_", tag(kd)), "_vs_Parental.csv")), row.names = FALSE)
}
# (2) scientific-concordance references: limma-voom (eBayes), edgeR QL, DESeq2 on ROUNDED expected counts
fit <- eBayes(lmFit(v, o$design))
for (k in 2:4) { tt <- topTable(fit, coef = k, number = Inf, sort.by = "none"); write.csv(data.frame(geneID = rownames(tt), tt), file.path(OUTR, paste0("de_ref__RSEM__limma_voom__", gsub(" ", "_", tag(levels(g)[k])), "_vs_Parental.csv")), row.names = FALSE) }
dge <- estimateDisp(o$dge, o$design); qf <- glmQLFit(dge, o$design)
for (k in 2:4) { tq <- topTags(glmQLFTest(qf, coef = k), n = Inf, sort.by = "none")$table; write.csv(data.frame(geneID = rownames(tq), tq), file.path(OUTR, paste0("de_ref__RSEM__edgeR_QL__", gsub(" ", "_", tag(levels(g)[k])), "_vs_Parental.csv")), row.names = FALSE) }
# DESeq2 requires integer counts: RSEM expected counts are fractional (4.6% of cells). Rounding is an explicit, documented
# derived representation (the tximport convention) and is applied ONLY for this reference model, never to the source matrix.
cd <- data.frame(g = factor(make.names(as.character(g)), levels = make.names(levels(g))), row.names = cols)
dds <- DESeqDataSetFromMatrix(countData = round(o$mf), colData = cd, design = ~g); dds <- DESeq(dds, quiet = TRUE)
for (k in 2:4) { r <- results(dds, contrast = c("g", make.names(levels(g)[k]), "Parental")); write.csv(data.frame(geneID = rownames(r), as.data.frame(r)), file.path(OUTR, paste0("de_ref__RSEM__DESeq2__", gsub(" ", "_", tag(levels(g)[k])), "_vs_Parental.csv")), row.names = FALSE) }
cat("14 done\n")
