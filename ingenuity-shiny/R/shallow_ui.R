# R/shallow_ui.R — render the page without deep recursion.
#
# Why: in shinylive, R runs in the browser on a small call stack. htmltools
# renders a page by recursing through the whole tag tree, and in Safari that
# overflowed the stack: the page request never answered and Safari showed
# GitHub's 404.
#
# shallow_ui() walks the tag tree with loops instead of recursion, then renders
# it bottom-up: each tag is rendered once its children are already finished
# HTML, so every htmltools call only sees one level of tags. R's stack depth no
# longer grows with the page's nesting. The result is the same page. Render
# hooks and tag functions (such as bslib's theme setup) run in document order,
# as they do in htmltools::tagify().

shallow_ui <- function(ui) {
  keep_tags <- c("html", "head", "body")   # structural tags renderPage looks for

  is_done <- function(x) {
    is.null(x) || is.character(x) || inherits(x, "html_dependency") ||
      htmltools:::isTagList(x) ||
      (inherits(x, "shiny.tag") && length(x$.renderHooks) == 0)
  }
  children_of <- function(x) {
    if (inherits(x, "shiny.tag")) x$children
    else if (htmltools:::isTagList(x)) x
    else NULL
  }

  # 1. Expand, top-down in document order: resolve render hooks and tag
  #    functions, and record every node with its parent and position.
  nodes <- list(); parent <- integer(); slot <- integer()
  todo <- list(list(x = ui, parent = 0L, slot = 0L))   # a stack
  while (length(todo)) {
    item <- todo[[length(todo)]]; todo[[length(todo)]] <- NULL
    x <- item$x
    while (!is_done(x)) x <- htmltools::as.tags(x)
    i <- length(nodes) + 1L
    nodes[i] <- list(x); parent[i] <- item$parent; slot[i] <- item$slot
    kids <- children_of(x)
    for (k in rev(seq_along(kids))) {
      todo[[length(todo) + 1L]] <- list(x = kids[[k]], parent = i, slot = k)
    }
  }

  # 2. Collapse, bottom-up (children always come after their parent above):
  #    render each tag to HTML and put it back into its parent.
  singletons <- character(0)
  for (i in rev(seq_along(nodes))) {
    x <- nodes[[i]]
    if (i > 1L && inherits(x, "shiny.tag") && !x$name %in% keep_tags) {
      rt <- htmltools::renderTags(x, singletons = singletons, indent = FALSE)
      singletons <- rt$singletons
      x <- htmltools::attachDependencies(htmltools::HTML(rt$html), rt$dependencies)
      if (nzchar(rt$head)) x <- htmltools::tagList(tags$head(htmltools::HTML(rt$head)), x)
    }
    if (i == 1L) return(x)
    p <- parent[i]
    if (inherits(nodes[[p]], "shiny.tag")) nodes[[p]]$children[slot[i]] <- list(x)
    else nodes[[p]][slot[i]] <- list(x)
  }
}
