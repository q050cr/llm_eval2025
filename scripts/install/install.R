pkgs <- c(
  "tidyverse",
  "quanteda",
  "quanteda.textstats",
  "quanteda.textmodels",
  "quanteda.textplots",
  "quanteda.sentiment",
  "knitr",
  "kableExtra",
  "gt",
  "ggplot2",
  "patchwork",
  "viridis",
  "corrplot",
  # "topicmodels",          # commented out in your list
  "ggrepel",
  "stringr"
)

# Identify packages that aren’t installed yet
missing <- pkgs[!pkgs %in% rownames(installed.packages())]

# Install the missing ones with renv
if (length(missing)) {
  renv::install(missing)
  message("Installed: ", paste(missing, collapse = ", "))
} else {
  message("All requested packages are already installed.")
}
