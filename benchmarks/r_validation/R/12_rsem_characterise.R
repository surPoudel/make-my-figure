source(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), "00_setup.R"))
# Independent characterisation of the RSEM matrix. The file is read verbatim; nothing is rounded or altered.
RSEM <- file.path(REPO, "GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt")
raw <- read.delim(RSEM, check.names = FALSE, stringsAsFactors = FALSE)
annot <- c("geneID", "geneSymbol", "bioType", "annotationLevel"); stopifnot(all(annot %in% names(raw)))
cols <- setdiff(names(raw), annot); m <- as.matrix(raw[, cols]); rownames(m) <- raw$geneID
sha <- sub(" .*", "", system2("sha256sum", shQuote(RSEM), stdout = TRUE))
frac <- m %% 1 != 0
info <- list(file = basename(RSEM), sha256 = sha, bytes = file.info(RSEM)$size, shape = dim(raw), n_samples = length(cols),
             min = min(m), max = max(m), n_cells = length(m), n_nonzero = sum(m != 0), fraction_zero = mean(m == 0),
             fraction_non_integer = mean(frac), n_non_integer_cells = sum(frac), fraction_rows_all_zero = mean(rowSums(m) == 0),
             n_rows_with_any_fraction = sum(rowSums(frac) > 0), fraction_of_nonzero_cells_non_integer = sum(frac) / sum(m != 0),
             library_sizes = as.list(setNames(colSums(m), cols)), duplicate_geneID = sum(duplicated(raw$geneID)),
             duplicate_geneSymbol = sum(duplicated(raw$geneSymbol)), biotype_counts = as.list(table(raw$bioType)),
             annotationLevel_counts = as.list(table(raw$annotationLevel)),
             examples_fractional = head(raw[rowSums(frac) > 0, c("geneID", "geneSymbol", cols[1:3])], 5))
write_json(info, file.path(OUTR, "rsem_characterisation.json"), auto_unbox = TRUE, digits = NA, pretty = TRUE)
# per-sample: total, zero fraction, non-integer fraction, detected genes (count > 0)
per <- data.frame(sample = cols, library_size = colSums(m), zero_fraction = colMeans(m == 0), non_integer_fraction = colMeans(frac), detected_genes = colSums(m > 0))
write.csv(per, file.path(OUTR, "rsem_per_sample.csv"), row.names = FALSE)
# same deterministic gene filter as documented in README: raw CPM > 1 in >= 4 samples
cpm_raw <- sweep(m, 2, colSums(m), "/") * 1e6; keep <- rowSums(cpm_raw > 1) >= 4
write.csv(data.frame(geneID = rownames(m)[keep]), file.path(OUTR, "rsem_filtered_genes.csv"), row.names = FALSE)
cat("12 done; kept", sum(keep), "genes\n")
