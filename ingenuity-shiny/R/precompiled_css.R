# R/precompiled_css.R — use CSS compiled ahead of time when running in the browser.
#
# In shinylive (webR) bslib's runtime Sass compile adds over 20 seconds to
# startup. The CSS is compiled natively by scripts/precompile_shiny_css.R and
# stored in precompiled/; here bslib's compile functions are swapped for
# lookups into that store. Anything not in the store falls back to the normal
# (slow) compile.

local({
  index_file <- file.path("precompiled", "index.rds")
  if (!identical(R.version$os, "emscripten") || !file.exists(index_file)) return()

  store_dir <- normalizePath("precompiled")
  rec <- readRDS(index_file)

  restore <- function(x) {
    if (inherits(x, "html_dependency")) {
      if (!is.null(x$src$file)) x$src$file <- file.path(store_dir, x$src$file)
      x
    } else {
      lapply(x, restore)
    }
  }

  ns <- asNamespace("bslib")
  orig_dependency <- get("bs_dependency", ns)
  orig_theme_deps <- get("bs_theme_dependencies", ns)
  orig_get_vars   <- get("bs_get_variables", ns)

  utils::assignInNamespace("bs_dependency", function(input = list(), theme, name, version, ...) {
    if (!is.null(rec$deps[[name]])) return(restore(rec$deps[[name]]))
    orig_dependency(input = input, theme = theme, name = name, version = version, ...)
  }, "bslib")

  utils::assignInNamespace("bs_theme_dependencies", function(theme, ...) {
    if (!is.null(rec$theme)) return(restore(rec$theme))
    orig_theme_deps(theme, ...)
  }, "bslib")

  utils::assignInNamespace("bs_get_variables", function(theme, varnames) {
    hit <- rec$vars[[paste(varnames, collapse = ",")]]
    if (!is.null(hit)) return(hit)
    orig_get_vars(theme, varnames)
  }, "bslib")
})
