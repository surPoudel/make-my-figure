# Reference values for the table transformations (base R only).
args <- commandArgs(trailingOnly = TRUE)
x <- c(1e-300, 1e-12, 0.001, 0.5, 1, 2, 10, 123.456, 1e6, 1e12, 1e300, 0, -1, NA)
off <- c(0, 1, 0.5)
rows <- list()
for (o in off) {
  y <- x + o
  for (m in c("log2", "log10", "ln", "sqrt")) {
    v <- switch(m, log2 = suppressWarnings(log2(y)), log10 = suppressWarnings(log10(y)),
                ln = suppressWarnings(log(y)), sqrt = suppressWarnings(sqrt(y)))
    rows[[length(rows) + 1]] <- data.frame(method = m, offset = o, x = x, r_value = v)
  }
}
# z-score with sample SD (n - 1): an ordinary vector, then one spanning 1e-300..1e300,
# where R's SD overflows to Inf and scale() returns 0 for every value.
zx <- c(0.5, 1, 2, 10, 123.456, -1, 0, 3.25)
rows[[length(rows) + 1]] <- data.frame(method = "zscore", offset = 0, x = zx, r_value = as.numeric(scale(zx)))
pos <- x[!is.na(x)]
rows[[length(rows) + 1]] <- data.frame(method = "zscore_extreme", offset = 0, x = pos,
                                       r_value = as.numeric(scale(pos)))
out <- do.call(rbind, rows)
out$x <- sprintf("%.17g", out$x); out$r_value <- sprintf("%.17g", out$r_value)
write.csv(out, args[[1]], row.names = FALSE)
