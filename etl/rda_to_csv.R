args <- commandArgs(trailingOnly = TRUE)
rda_path <- args[1]
object_name <- args[2]
csv_path <- args[3]

load(rda_path)
obj <- get(object_name)
obj$geometry <- NULL
class(obj) <- "data.frame"
write.csv(obj, csv_path, row.names = FALSE, na = "")
