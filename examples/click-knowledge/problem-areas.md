# Recurring Problem Areas
[← back to index](index.md)

Framed as guidance for future work — these are where fixes clustered.

- **The pager is fragile.** Multiple independent fixes touched stream closing, incremental
  output, and test races. Treat any pager change with extra test scrutiny.
  See [Terminal Output](themes/terminal-output.md).
- **Shell completion breaks on formatting edges.** Quoting, line endings, and multiline help
  strings have all caused breakage. See [Shell Completion](themes/shell-completion.md).
- **Parameter source / eager callbacks.** `get_parameter_source()` needed correcting during
  type conversion and eager callbacks (`7d05a59`) — a subtle ordering area.
