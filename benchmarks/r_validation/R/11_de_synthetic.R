source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
suppressPackageStartupMessages({ library(edgeR); library(limma); library(DESeq2) })
d <- read_syn("W_count_matrix.tsv"); m <- as.matrix(d[, setdiff(names(d), c("gene_id", "biotype"))]); rownames(m) <- d$gene_id
tt_safe <- function(...) tryCatch(t.test(...), error = function(e) list(statistic = NA_real_, p.value = NA_real_))
grp <- factor(ifelse(grepl("^A_", colnames(m)), "A", "B"), levels = c("A", "B")); design <- model.matrix(~grp)
dge <- calcNormFactors(DGEList(counts = m), method = "TMM"); v <- voom(dge, design); E <- v$E
# (1) Exact-equivalence reference: per-gene Welch t on voom logCPM, B vs A, log2FC = mean_B - mean_A, BH.
A <- E[, grp == "A"]; B <- E[, grp == "B"]
welch <- t(apply(E, 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; tt <- tt_safe(b, a); c(tt$statistic, tt$p.value) }))
student <- t(apply(E, 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; tt <- tt_safe(b, a, var.equal = TRUE); c(tt$statistic, tt$p.value) }))
mwu <- t(apply(E, 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; w <- suppressWarnings(wilcox.test(b, a, exact = (length(a) <= 8 && length(b) <= 8 && !any(duplicated(c(a, b)))), correct = TRUE)); c(w$statistic, w$p.value) }))
base <- data.frame(gene_id = rownames(E), log2FoldChange = rowMeans(B) - rowMeans(A), AveExpr = rowMeans(E), mean_A = rowMeans(A), mean_B = rowMeans(B))
write.csv(cbind(base, stat = welch[, 1], pvalue = welch[, 2], padj = p.adjust(welch[, 2], "BH")), file.path(OUTR, "de_screen__W_voom__welch_t.csv"), row.names = FALSE)
write.csv(cbind(base, stat = student[, 1], pvalue = student[, 2], padj = p.adjust(student[, 2], "BH")), file.path(OUTR, "de_screen__W_voom__students_t.csv"), row.names = FALSE)
write.csv(cbind(base, stat = mwu[, 1], pvalue = mwu[, 2], padj = p.adjust(mwu[, 2], "BH")), file.path(OUTR, "de_screen__W_voom__mann_whitney.csv"), row.names = FALSE)
# (1b) the same per-gene tests on plain log2-CPM (prior 0.5) — the Class-A input shared exactly with Python
L <- cpm(m, lib.size = colSums(m), log = TRUE, prior.count = 0.5); A <- L[, grp == "A"]; B <- L[, grp == "B"]
baseL <- data.frame(gene_id = rownames(L), log2FoldChange = rowMeans(B) - rowMeans(A), AveExpr = rowMeans(L), mean_A = rowMeans(A), mean_B = rowMeans(B))
w2 <- t(apply(L, 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; tt <- tt_safe(b, a); c(tt$statistic, tt$p.value) }))
s2 <- t(apply(L, 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; tt <- tt_safe(b, a, var.equal = TRUE); c(tt$statistic, tt$p.value) }))
# Rank tests: log-CPM of zero counts is one value in exact arithmetic but edgeR::cpm yields 2 distinct doubles for the
# 195 zero-count cells (last-bit differences). Round to 12 decimals so mathematically tied values are ties (same
# canonicalisation as MakeMyFigure's differential screen).
m2 <- t(apply(round(L, 12), 1, function(x) { a <- x[grp == "A"]; b <- x[grp == "B"]; w <- suppressWarnings(wilcox.test(b, a, exact = (length(a) <= 8 && length(b) <= 8 && !any(duplicated(c(a, b)))), correct = TRUE)); c(w$statistic, w$p.value) }))
write.csv(cbind(baseL, stat = w2[, 1], pvalue = w2[, 2], padj = p.adjust(w2[, 2], "BH")), file.path(OUTR, "de_screen__W_logcpm__welch_t.csv"), row.names = FALSE)
write.csv(cbind(baseL, stat = s2[, 1], pvalue = s2[, 2], padj = p.adjust(s2[, 2], "BH")), file.path(OUTR, "de_screen__W_logcpm__students_t.csv"), row.names = FALSE)
write.csv(cbind(baseL, stat = m2[, 1], pvalue = m2[, 2], padj = p.adjust(m2[, 2], "BH")), file.path(OUTR, "de_screen__W_logcpm__mann_whitney.csv"), row.names = FALSE)
# (2) Scientific-concordance references: limma-voom, edgeR QL, DESeq2 (integer counts here, so DESeq2 is legitimate).
fit <- eBayes(lmFit(v, design)); tt <- topTable(fit, coef = 2, number = Inf, sort.by = "none")
write.csv(data.frame(gene_id = rownames(tt), tt), file.path(OUTR, "de_ref__W__limma_voom.csv"), row.names = FALSE)
dge2 <- estimateDisp(dge, design); qf <- glmQLFit(dge2, design); ql <- glmQLFTest(qf, coef = 2); tq <- topTags(ql, n = Inf, sort.by = "none")$table
write.csv(data.frame(gene_id = rownames(tq), tq), file.path(OUTR, "de_ref__W__edgeR_QL.csv"), row.names = FALSE)
dds <- DESeqDataSetFromMatrix(countData = round(m), colData = data.frame(grp = grp, row.names = colnames(m)), design = ~grp)
dds <- DESeq(dds, quiet = TRUE); res <- results(dds, contrast = c("grp", "B", "A"))
write.csv(data.frame(gene_id = rownames(res), as.data.frame(res)), file.path(OUTR, "de_ref__W__DESeq2.csv"), row.names = FALSE)
# (3) Y (already log): feature summaries with anova / kruskal (Holm) and welch/paired/wilcoxon g1 vs g2 (Bonferroni)
d <- read_syn("Y_log_matrix_negatives.tsv"); m <- as.matrix(d[, setdiff(names(d), "feature")]); rownames(m) <- d$feature
g <- factor(rep(c("g1", "g2", "g3"), c(3, 3, 4)), levels = c("g1", "g2", "g3"))
an <- t(apply(m, 1, function(x) { s <- summary(aov(x ~ g))[[1]]; c(s["g", "F value"], s["g", "Pr(>F)"]) }))
kw <- t(apply(m, 1, function(x) { k <- kruskal.test(x ~ g); c(k$statistic, k$p.value) }))
write.csv(data.frame(feature = rownames(m), statistic = an[, 1], p_value = an[, 2], adjusted_p_value = p.adjust(an[, 2], "holm")), file.path(OUTR, "de_summary__Y__anova.csv"), row.names = FALSE)
write.csv(data.frame(feature = rownames(m), statistic = kw[, 1], p_value = kw[, 2], adjusted_p_value = p.adjust(kw[, 2], "holm")), file.path(OUTR, "de_summary__Y__kruskal.csv"), row.names = FALSE)
a <- m[, g == "g1"]; b <- m[, g == "g2"]
w <- t(apply(cbind(a, b), 1, function(x) { tt <- tt_safe(x[1:3], x[4:6]); c(tt$statistic, tt$p.value, mean(x[1:3]) - mean(x[4:6])) }))
write.csv(data.frame(feature = rownames(m), statistic = w[, 1], p_value = w[, 2], mean_difference = w[, 3], adjusted_p_value = p.adjust(w[, 2], "bonferroni")), file.path(OUTR, "de_summary__Y__welch_t.csv"), row.names = FALSE)
pt <- t(apply(cbind(a, b), 1, function(x) { tt <- tt_safe(x[1:3], x[4:6], paired = TRUE); c(tt$statistic, tt$p.value) }))
write.csv(data.frame(feature = rownames(m), statistic = pt[, 1], p_value = pt[, 2], adjusted_p_value = p.adjust(pt[, 2], "bonferroni")), file.path(OUTR, "de_summary__Y__paired_t.csv"), row.names = FALSE)
wx <- t(apply(cbind(a, b), 1, function(x) { ww <- suppressWarnings(wilcox.test(x[1:3], x[4:6], paired = TRUE, exact = TRUE, correct = FALSE)); c(ww$statistic, ww$p.value) }))
write.csv(data.frame(feature = rownames(m), V = wx[, 1], p_value = wx[, 2], adjusted_p_value = p.adjust(wx[, 2], "bonferroni")), file.path(OUTR, "de_summary__Y__wilcoxon.csv"), row.names = FALSE)
cat("11 done\n")
