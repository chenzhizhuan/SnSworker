# Xingchen Document Parse Output Schema

## Single document status JSON

When a single parse fails with `--view json`, stdout uses this shape:

```json
{
  "index": 1,
  "name": "paper",
  "filename": "paper.pdf",
  "source": "paper.pdf",
  "state": "failed",
  "request_id": null,
  "markdown_path": null,
  "json_path": null,
  "total_page_number": null,
  "time_second": null,
  "error": "Missing X-APP-ID. Set TELEAI_X_APP_ID / XINGCHEN_APP_ID or pass --app-id."
}
```

On single-document success with `--view json`, stdout is the raw TeleAI query response.

## Single artifact layout

```text
output/
  document-name/
    document-name.md
    result.json
```

- `{document-name}.md` contains extracted Markdown or fallback Markdown.
- `result.json` contains the raw TeleAI query response.
- If `--output` points to a file, the requested primary view is written to that exact path and the companion format is written beside it.
- If `--download-images` is used, image assets are saved under `images/` in the document directory and Markdown links are rewritten when possible.
- If polling times out, `timeout_status.json` is saved in the document directory with `request_id`, elapsed time, timeout setting, and the last query response.

## Batch artifact layout

```text
output/
  batch_YYYYMMDD_HHMMSS/
    manifest.json
    001_document-name/
      document-name.md
      result.json
```

Batch stdout is a summary JSON:

```json
{
  "state": "completed",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "manifest_path": "output/batch_20260617_120000/manifest.json",
  "documents": []
}
```

## Manifest

`manifest.json` is the stable handoff file for agents:

```json
{
  "batch_id": "batch_20260617_120000",
  "total": 2,
  "completed": 2,
  "failed": 0,
  "documents": [
    {
      "index": 1,
      "name": "paper",
      "filename": "paper.pdf",
      "source": "paper.pdf",
      "state": "done",
      "request_id": "REQ_abc123",
      "markdown_path": "output/batch/001_paper/paper.md",
      "json_path": "output/batch/001_paper/result.json",
      "total_page_number": 5,
      "time_second": 2.3,
      "error": null
    }
  ]
}
```

`documents` is always sorted by `index`, not by async completion time.

## Read output

`read --list` prints a compact JSON list. `read --index` and `read --group` print Markdown sections:

```markdown
## Document 1: paper.pdf

requestId: REQ_abc123

source: paper.pdf

markdown_path: output/batch/001_paper/paper.md

...document markdown...
```
