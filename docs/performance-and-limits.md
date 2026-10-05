# Performance and limits

## Measured example lint time

The measurements below are from `doc_lint.py --no-write` on the shipped
examples, using the repository’s uv-managed Python 3.14.8 interpreter. Each
example was run 25 times; times are wall-clock milliseconds for a complete
lint. These are local reference measurements, not CI latency guarantees.

| Example | Files in example tree | Runs | Median | Minimum | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| `desk-timer` | 7 | 25 | 43.800 ms | 42.781 ms | 65.726 ms |
| `desk-timer-launch` | 9 | 25 | 44.585 ms | 43.411 ms | 71.041 ms |

## Figure limits

- `doc_view_figure` accepts PNG, JPEG, GIF, and WebP, and limits an inline
  image to 5 MiB (5,242,880 bytes).
- The tool verifies the file signature and returns an error for an
  unsupported type, invalid signature, missing file, or oversized image.
- SVG is intentionally not returned inline. `doc_figures` can inventory
  Markdown image references and Mermaid blocks without rendering an image.
- A successful view appends an observation. A vision review must bind to the
  image hash or its event ID; changing the image invalidates hash-based
  evidence.

## Record and workspace limits

- VRP stage impressions and vision-review impressions need at least 400
  characters and three sentences. The Stop hook makes at most two denials
  before allowing completion with an explicit gap report.
- SLP v2 validates workspace-relative paths, rejects symlink traversal, and
  hashes request inputs and response artifacts. A `done` response requires a
  fresh passing full lint report for each claimed Markdown artifact.
- Full lint reports are hash-bound to the brief and target files. Any edit
  after lint means the report must be regenerated.
- The doc plugin has no tools image. Its hooks, MCP server, and lint/record
  scripts need host `python3`; those plugin scripts use only the Python
  standard library.
- Lint checks the structure and evidence contracts encoded in its rules. It
  cannot establish that a product is safe, that an external fact is true, or
  that a vision observation is an engineering approval.

For the exact hook and protocol boundaries, see
[records and vision](records-and-vision.md) and [contracts](contracts.md).
