#!/usr/bin/env Rscript
# pipeline_with_optional_ERCC_and_replicate_robust.R

suppressPackageStartupMessages({
  library(edgeR)
  library(limma)
  library(dplyr)
  library(readr)
  library(jsonlite)
})

# ---------- 1) Read config ----------
config      <- fromJSON("config.json")
meta_file   <- config$meta_file
count_file  <- config$count_file
output_dir  <- config$output_folder
comparisons <- config$comparisons
if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

# ---------- 2) Read meta & counts ----------
designData <- read_csv(meta_file, show_col_types = FALSE)
designData$Group <- gsub(" ", "_", designData$Group)

counts_all <- read.table(count_file, sep = "\t", header = TRUE,
                         row.names = 1, check.names = FALSE)

# first 3 annotation columns: geneSymbol, bioType, annotationLevel
annotations <- counts_all[, 1:3, drop = FALSE]
counts      <- counts_all[, -(1:3), drop = FALSE]

# align samples between meta and counts (preserve meta order)
keep.samples <- intersect(designData$SampleID, colnames(counts))
if (length(keep.samples) < nrow(designData)) {
  warning("Dropping metadata rows with no matching counts: ",
          paste(setdiff(designData$SampleID, keep.samples), collapse = ", "))
  designData <- dplyr::filter(designData, SampleID %in% keep.samples)
}
counts <- counts[, designData$SampleID, drop = FALSE]

# ---------- 3) Robust comparisons parsing ----------
to_comp_df <- function(x) {
  if (is.null(x)) stop("config$comparisons is NULL")
  if (is.data.frame(x)) {
    stopifnot(all(c("group1","group2") %in% names(x)))
    df <- x
  } else if (is.list(x)) {
    if (!is.null(x$group1) && !is.null(x$group2)) {
      df <- data.frame(group1 = as.character(x$group1),
                       group2 = as.character(x$group2),
                       stringsAsFactors = FALSE)
    } else {
      df <- do.call(rbind, lapply(x, function(e)
        data.frame(group1 = as.character(e[["group1"]]),
                   group2 = as.character(e[["group2"]]),
                   stringsAsFactors = FALSE)))
    }
  } else {
    stop("Unrecognized type for config$comparisons: ", class(x))
  }
  df
}
comp_df <- to_comp_df(comparisons)

# set Group levels: comparisons first, then anything else in meta
cmp_groups <- unique(c(comp_df$group1, comp_df$group2))
grp_levels <- unique(c(cmp_groups, designData$Group))
designData$Group <- factor(designData$Group, levels = grp_levels)
groupLabels      <- factor(designData$Group, levels = grp_levels)

# ---------- 4) Split ERCC vs genes ----------
ercc_mask    <- grepl("^ERCC", rownames(counts))
has_ercc     <- any(ercc_mask)
gene_counts  <- counts[!ercc_mask, , drop = FALSE]
ercc_counts  <- if (has_ercc) counts[ercc_mask, , drop = FALSE] else NULL

# ---------- 5) edgeR object, filter, normalize ----------
dge_gene <- DGEList(counts = gene_counts, group = groupLabels)
# your rule: CPM > 1 in >= min(group size) samples
keep <- rowSums(cpm(dge_gene) > 1) >= min(table(groupLabels))
dge_gene <- dge_gene[keep, , keep.lib.sizes = FALSE]
dge_gene <- calcNormFactors(dge_gene)

if (has_ercc) {
  dge_ercc <- DGEList(counts = ercc_counts, group = groupLabels)
  dge_ercc$samples$lib.size     <- dge_gene$samples$lib.size
  dge_ercc$samples$norm.factors <- dge_gene$samples$norm.factors
}

# ---------- 6) Design (adds Replicate if present) + (optional) BCV ----------
has_repl <- "Replicate" %in% colnames(designData)
if (has_repl) {
  designData$Replicate <- factor(designData$Replicate)
  design <- model.matrix(~ Replicate + Group, data = designData)
  # columns: (Intercept) Replicate... Group<level2> ...
} else {
  design <- model.matrix(~ Group, data = designData)
  # columns: (Intercept) Group<level2> ...
}

# optional BCV (GLM)
dge_gene <- estimateGLMCommonDisp(dge_gene, design)
dge_gene <- estimateGLMTrendedDisp(dge_gene, design)
dge_gene <- estimateGLMTagwiseDisp(dge_gene, design)
png(file.path(output_dir, "BCV_GLM_plot.png"), width = 700, height = 700)
plotBCV(dge_gene, main = "BCV Plot (GLM-based)")
dev.off()

# ---------- 7) voom + save normalized ----------
v <- voom(dge_gene, design, plot = FALSE)
E <- v$E
write.table(cbind(annotations[rownames(E), , drop = FALSE], E),
            file = file.path(output_dir, "voom_norm_annot.txt"),
            sep = "\t", quote = FALSE, row.names = TRUE)

# ---------- 8) MDS ----------
png(file.path(output_dir, "MDS_voom.png"), width = 700, height = 700)
plotMDS(v, labels = colnames(E), col = as.numeric(designData$Group))
legend("topright", legend = levels(designData$Group),
       col = seq_along(levels(designData$Group)), pch = 19, bty = "n")
dev.off()

# ---------- 9) limma fit ----------
fit <- lmFit(v, design)

# helper: valid contrast for intercept model
make_group_contrast <- function(g1, g2, design_cols) {
  c1 <- paste0("Group", g1)
  c2 <- paste0("Group", g2)
  has1 <- c1 %in% design_cols
  has2 <- c2 %in% design_cols
  if (has1 && has2) {
    paste0(c1, " - ", c2)     # both non-baseline
  } else if (has1 && !has2) {
    c1                         # g2 is baseline
  } else if (!has1 && has2) {
    paste0("-(", c2, ")")      # g1 is baseline
  } else {
    stop("Contrast groups not in design: ", g1, " / ", g2,
         " | design cols: ", paste(design_cols, collapse = ", "))
  }
}

design_cols <- colnames(design)
contrast_vec <- setNames(vector("list", nrow(comp_df)),
                         paste0(comp_df$group1, "_vs_", comp_df$group2))
for (i in seq_len(nrow(comp_df))) {
  g1 <- as.character(comp_df$group1[i])
  g2 <- as.character(comp_df$group2[i])
  contrast_vec[[i]] <- make_group_contrast(g1, g2, design_cols)
}
cont_mat <- makeContrasts(contrasts = unlist(contrast_vec), levels = design)

# After you build cont_mat, force friendly names like "ctr_vs_GC7"
friendly_names <- paste0(comp_df$group1, "_vs_", comp_df$group2)
if (length(friendly_names) == ncol(cont_mat)) {
  colnames(cont_mat) <- friendly_names
} else {
  warning("Number of comparisons doesn't match contrast columns; keeping original names.")
}




fit2 <- contrasts.fit(fit, cont_mat)
fit2 <- eBayes(fit2)

sanitize <- function(x) {
  x <- gsub("\\s*-\\s*", "_vs_", x)
  x <- gsub("\\s+", "_", x)
  x <- gsub("[/\\\\:;,\'\"()\\[\\]]+", "_", x)
  x
}

# ---------- 10) Write DE tables ----------
for (cn in colnames(cont_mat)) {
  tt  <- topTable(fit2, coef = cn, number = Inf, sort.by = "P")
  out <- cbind(annotations[rownames(tt), , drop = FALSE], tt)

  cn_safe <- sanitize(cn)                    # e.g., "WT_vs_KO" or "ctr_vs_GC7"
  outfile <- file.path(output_dir, paste0(cn_safe, "_DE.txt"))
  write.table(out, file = outfile, sep = "\t", quote = FALSE, row.names = TRUE)
}


# ---------- 11) ERCC QC (only if present) ----------
if (has_ercc) {
  message("ERCC rows detected — producing ERCC QC.")
  log2_ercc <- log2(cpm(dge_ercc) + 1)

  ercc_expected_path <- "cms_095046.txt"
  have_expected <- file.exists(ercc_expected_path)

  if (have_expected) {
    ercc_info <- read.table(ercc_expected_path, header = TRUE, sep = "\t",
                            check.names = FALSE, stringsAsFactors = FALSE)
    if ("ERCC ID" %in% names(ercc_info)) {
      ercc_info$ERCC_ID <- ercc_info$`ERCC ID`
    }
    if (all(c("ERCC_ID","concentration in Mix 1 (attomoles/ul)") %in% names(ercc_info))) {
      exp1 <- setNames(ercc_info$`concentration in Mix 1 (attomoles/ul)`,
                       ercc_info$ERCC_ID)
      obs1 <- rowMeans(log2_ercc)
      png(file.path(output_dir, "ERCC_obs_vs_exp.png"), 800, 600)
      plot(log2(exp1[names(obs1)] + 1), obs1,
           xlab = "log2(Expected+1)", ylab = "log2(Observed CPM+1)",
           main = "ERCC Observed vs Expected", xaxs = "i", yaxs = "i")
      abline(0, 1, col = "red")
      dev.off()
    }
  }

  png(file.path(output_dir, "ERCC_boxplot.png"), 800, 600)
  par(mar = c(8,4,4,2))
  boxplot(log2_ercc, las = 2, cex.axis = 0.8,
          main = "ERCC log2(CPM+1)", ylab = "log2(CPM+1)")
  dev.off()

  vars <- apply(log2_ercc, 2, var)
  if (sum(vars > 0) >= 2) {
    pca <- prcomp(t(log2_ercc), center = TRUE, scale. = TRUE)
    png(file.path(output_dir, "ERCC_pca.png"), 800, 600)
    plot(pca$x[,1], pca$x[,2],
         xlab = sprintf("PC1 (%.1f%%)", 100*summary(pca)$importance[2,1]),
         ylab = sprintf("PC2 (%.1f%%)", 100*summary(pca)$importance[2,2]),
         main = "ERCC PCA", pch = 19)
    text(pca$x[,1], pca$x[,2], labels = colnames(log2_ercc), pos = 3, cex = 0.8)
    dev.off()
  }

  if (ncol(log2_ercc) >= 2) {
    corrm <- cor(log2_ercc, use = "pairwise.complete.obs")
    png(file.path(output_dir, "ERCC_corr_heatmap.png"), 800, 800)
    heatmap(corrm, Rowv = NA, Colv = NA, scale = "none",
            col = colorRampPalette(c("navy","white","firebrick3"))(50),
            margins = c(6,6), main = "ERCC Sample Corr")
    dev.off()
  }
} else {
  message("No ERCC rows found — skipping ERCC QC.")
}

message("Pipeline complete. Results in: ", output_dir)

