args <- commandArgs(trailingOnly = TRUE)
rda_path <- args[1]
object_name <- args[2]
csv_path <- args[3]

load(rda_path)
obj <- get(object_name)
geom <- obj$geometry

ring_wkt <- function(ring) {
  coords <- apply(ring, 1, function(r) paste(r[1], r[2]))
  paste0("(", paste(coords, collapse = ", "), ")")
}
poly_wkt <- function(poly) {
  paste0("(", paste(vapply(poly, ring_wkt, character(1)), collapse = ", "), ")")
}
mp_wkt <- function(mp) {
  paste0("MULTIPOLYGON(", paste(vapply(mp, poly_wkt, character(1)), collapse = ", "), ")")
}

wkt <- vapply(geom, mp_wkt, character(1))
out <- data.frame(
  LOCATIONID = as.character(obj$LOCATIONID),
  LOCATIONNAME = as.character(obj$LOCATIONNAME),
  ZONELEVELID = obj$ZONELEVELID,
  wkt = wkt,
  stringsAsFactors = FALSE
)
write.csv(out, csv_path, row.names = FALSE, na = "")
