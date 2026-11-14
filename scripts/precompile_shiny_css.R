# scripts/precompile_shiny_css.R — compile the Shiny app's Sass ahead of time.
#
# Why: bslib and shiny compile Bootstrap's Sass when the page is first served.
# Natively that takes under a second, but in the browser (shinylive / webR) it
# added over 20 seconds to the app's startup.
#
# This script renders the app's page once in regular R, records every Sass
# result (theme CSS, bslib component CSS, shiny's own CSS, theme variables),
# and writes them to ingenuity-shiny/precompiled/. ingenuity-shiny/R/
# precompiled_css.R replays them when the app runs under webR.
#
# Run from the project root after changing the theme or upgrading packages:
#   Rscript scripts/precompile_shiny_css.R

suppressPackageStartupMessages(library(shiny))

app_dir <- "ingenuity-shiny"
out_dir <- file.path(app_dir, "precompiled")
unlink(out_dir, recursive = TRUE)
dir.create(out_dir)
out_abs <- normalizePath(out_dir)

recorded <- list(deps = list(), theme = NULL, vars = list())

# Copy a dependency's files under precompiled/ and store a relative path.
# bslib copies the same Google Fonts (font.css + fonts/, ~3 MB) into every
# compiled dependency, but only the Bootstrap CSS @imports them. Drop the
# copies that nothing in the dependency references.
store_dep <- function(dep) {
  if (is.null(dep$src$file)) return(dep)            # remote (href) dependency
  dep <- htmltools::copyDependencyToDir(dep, out_abs, mustWork = TRUE)
  dir <- normalizePath(dep$src$file)
  font_css <- file.path(dir, "font.css")
  if (file.exists(font_css) && !"font.css" %in% dep$stylesheet) {
    css <- setdiff(list.files(dir, "\\.css$", full.names = TRUE), font_css)
    imports_fonts <- any(vapply(css, function(f)
      any(grepl("font.css", readLines(f, warn = FALSE), fixed = TRUE)), logical(1)))
    if (!imports_fonts) unlink(c(font_css, file.path(dir, "fonts")), recursive = TRUE)
  }
  dep$src$file <- sub(paste0("^", out_abs, "/?"), "", dir)
  dep
}
store <- function(x) {
  if (inherits(x, "html_dependency")) store_dep(x) else lapply(x, store)
}

ns <- asNamespace("bslib")
orig_dependency <- get("bs_dependency", ns)
orig_theme_deps <- get("bs_theme_dependencies", ns)
orig_get_vars   <- get("bs_get_variables", ns)

assignInNamespace("bs_dependency", function(input = list(), theme, name, version, ...) {
  res <- orig_dependency(input = input, theme = theme, name = name, version = version, ...)
  recorded$deps[[name]] <<- store(res)
  res
}, "bslib")
assignInNamespace("bs_theme_dependencies", function(theme, ...) {
  res <- orig_theme_deps(theme, ...)
  recorded$theme <<- store(res)
  res
}, "bslib")
assignInNamespace("bs_get_variables", function(theme, varnames) {
  res <- orig_get_vars(theme, varnames)
  recorded$vars[[paste(varnames, collapse = ",")]] <<- res
  res
}, "bslib")

# Render the page the way shinylive does.
app <- shiny::as.shiny.appobj(app_dir)
app$onStart()
shiny:::workerId("")
shiny:::clearCurrentAppState()
shiny:::initCurrentAppState(app)
handlers <- shiny:::createAppHandlers(app$httpHandler, app$serverFuncSource)
req <- new.env()
req$PATH_INFO <- "/"; req$REQUEST_METHOD <- "GET"; req$QUERY_STRING <- ""
resp <- handlers$http(req)
stopifnot(resp$status == 200, !is.null(recorded$theme))

# Inputs that the server renders later (renderUI) aren't in the page; resolve
# their theme-dependent CSS too, against the theme the page just set.
stopifnot(!is.null(shiny::getCurrentTheme()))
invisible(htmltools::resolveDependencies(htmltools::findDependencies(tagList(
  selectInput("x_select", "x", "a"),
  sliderInput("x_slider", "x", 0, 1, 0),
  checkboxInput("x_check", "x"),
  checkboxGroupInput("x_group", "x", "a")
))))

recorded$built_with <- vapply(c("shiny", "bslib", "sass"),
                              function(p) as.character(packageVersion(p)), "")
saveRDS(recorded, file.path(out_abs, "index.rds"), version = 2)  # shiny may have changed the wd

message("Precompiled: theme + ", paste(names(recorded$deps), collapse = ", "),
        " + ", length(recorded$vars), " variable lookup(s) -> ", out_dir)
