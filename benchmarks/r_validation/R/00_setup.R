# Shared helpers for the independent R reference implementations.
# INDEPENDENCE RULE: these scripts read ONLY data/synthetic, data/metadata, the bundled
# examples/ folders and the RSEM matrix. They never open anything under results/python.
suppressPackageStartupMessages({ library(jsonlite) })
options(stringsAsFactors = FALSE, digits = 15, warn = 1)
ROOT <- normalizePath(file.path(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE)[1])), ".."))
REPO <- normalizePath(file.path(ROOT, "..", ".."))
DATA <- file.path(ROOT, "data", "synthetic")
META <- file.path(ROOT, "data", "metadata")
OUTR <- file.path(ROOT, "results", "R")
dir.create(OUTR, showWarnings = FALSE, recursive = TRUE)
stopifnot(!grepl("results/python", DATA))

.rows <- new.env(); .rows$stat <- list(); .rows$label <- list()
emit <- function(ds, test, comp, quantity, value) {
  v <- suppressWarnings(as.numeric(value)); if (length(v) != 1) v <- NA_real_
  .rows$stat[[length(.rows$stat) + 1]] <- data.frame(dataset_id = ds, test_id = test, comparison = comp,
                                                     quantity = quantity, value = v)
}
emit_many <- function(ds, test, comp, ...) { q <- list(...); for (n in names(q)) emit(ds, test, comp, n, q[[n]]) }
note <- function(ds, test, comp, txt) .rows$label[[length(.rows$label) + 1]] <-
  data.frame(dataset_id = ds, test_id = test, comparison = comp, note = txt)
flush_stats <- function(name) {
  df <- do.call(rbind, .rows$stat); write.csv(df, file.path(OUTR, name), row.names = FALSE)
  if (length(.rows$label)) write.csv(do.call(rbind, .rows$label), file.path(OUTR, sub("\\.csv$", "_notes.csv", name)), row.names = FALSE)
  .rows$stat <- list(); .rows$label <- list(); invisible(df)
}
read_syn <- function(name) read.csv(file.path(DATA, name), sep = if (grepl("\\.tsv$", name)) "\t" else ",", check.names = FALSE)
levels_first_seen <- function(x) unique(as.character(x[!is.na(x)]))
write_matrix <- function(tag, ids, id_name, m) {
  out <- data.frame(ids, as.data.frame(m, check.names = FALSE), check.names = FALSE); names(out)[1] <- id_name
  write.csv(out, file.path(OUTR, paste0("transform__", tag, ".csv")), row.names = FALSE)
}
fmt <- function(x) format(x, digits = 15)
