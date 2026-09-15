---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '1673229b-6528-4b2e-bb5f-54b19bcdb0ac'
  PropagateID: '1673229b-6528-4b2e-bb5f-54b19bcdb0ac'
  ReservedCode1: '5ef4e375-f570-42c3-be57-bda84842f562'
  ReservedCode2: '5ef4e375-f570-42c3-be57-bda84842f562'
---

# Xingchen Document Parse CLI Guidance

## Credential behavior

Normal private use does not require users to provide AppID/AppKey. This build contains an encrypted config fallback.

Credential lookup order:

```text
CLI arguments > environment variables > encrypted config > plain config
```

Override only for development, rotation, or emergency testing:

```bash
export TELEAI_X_APP_ID="..."
export XINGCHEN_API_KEY="..."
```

To test missing credentials, temporarily move the config file and clear credential environment variables:

```bash
python tele_xingchen/scripts/xingchen_docparse.py --doctor
```

`callback_url` defaults to `http://127.0.0.1/unused` because this wrapper uses Pull mode. Override it when needed:

```bash
export TELEAI_CALLBACK_URL="https://your-callback.example.com/callback"
```


## Pull query diagnostics

If a task stays pending for a long time, use a longer timeout once to distinguish slow backend processing from a script issue:

```bash
python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output ./output --timeout 900 --poll-interval 5
```

Each poll line prints the request id, poll count, elapsed seconds, API code, and message. `code=990003` means the backend is still processing.

To inspect a known request id without resubmitting the file:

```bash
python tele_xingchen/scripts/xingchen_docparse.py query --request-id REQ_xxx
```

When the parse times out, inspect `timeout_status.json` in the document output directory. It contains the last query response returned by the service.

## Command shape

Single local document:

```bash
python tele_xingchen/scripts/xingchen_docparse.py report.pdf
```

Single public URL:

```bash
python tele_xingchen/scripts/xingchen_docparse.py https://example.com/report.pdf
```

Batch:

```bash
python tele_xingchen/scripts/xingchen_docparse.py ./docs --recursive --resume --output ./output
```

Batch readback:

```bash
python tele_xingchen/scripts/xingchen_docparse.py read --batch ./output/batch_xxx/manifest.json --group 1 --group-size 10
```

## Output views

**Important**: By default, the script prints a **JSON status summary** (not raw Markdown) to stdout. This avoids Chinese garbling on Windows terminals (GBK/CP936). The JSON contains `markdown_path` — use the `Read` tool to open the `.md` file and get the full OCR content.

| Goal | Command |
|---|---|
| Default: JSON status summary (recommended) | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf` |
| Markdown content via stdout (may garble on Windows) | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --view markdown` |
| Raw result JSON | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --view json` |
| Custom output dir | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output ./result` |
| Markdown file (specify .md output) | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output result.md` |
| Raw JSON file | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --view json --output result.json` |
| URL input | `python tele_xingchen/scripts/xingchen_docparse.py https://example.com/report.pdf` |
| Force base64 mode | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --input-mode base64` |
| Download returned image assets | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --download-images` |
| Page range passthrough | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --page-range 1-5` |
| Encrypted PDF password passthrough | `python tele_xingchen/scripts/xingchen_docparse.py report.pdf --password "..."` |
| Endpoint/config check | `python tele_xingchen/scripts/xingchen_docparse.py --doctor` |
| Version | `python tele_xingchen/scripts/xingchen_docparse.py --version` |

**Recommended workflow**: Run the default command → read the JSON status summary → find `markdown_path` → use the `Read` tool to read the `.md` file. This avoids all terminal encoding issues.

Compatibility aliases:

- `--stdout` is equivalent to `--view markdown` for one input.
- `--json` is equivalent to `--view json`.
- `--input-mode file` is kept as an alias for local base64 upload.
- `--appid` is accepted as an alias for `--app-id`.

## Artifacts

Single document:

```text
output/
  document-name/
    document-name.md
    result.json
```

Batch:

```text
output/
  batch_YYYYMMDD_HHMMSS/
    manifest.json
    001_document-name/
      document-name.md
      result.json
```

When `--download-images` is used, downloaded assets are saved under each document directory:

```text
output/document-name/images/image_001.jpg
```

Read Markdown first. Inspect `result.json` when the task needs page layout, structured blocks, table HTML, image regions, confidence, coordinates, or debug details.

## Batch workflow

1. Run batch parse.
2. Read stdout batch summary and find `manifest_path`.
3. Use `read --list` to inspect documents if needed.
4. Use `read --group N --group-size 10` for broad summaries.
5. Use `read --index ...` for specific documents.

Do not feed all Markdown from a large batch into the model at once.

## Security note

The encrypted config fallback hides plaintext credentials from casual source inspection and logs. It is not a hard security boundary. If the package is distributed to untrusted users with source access, use a server-side proxy instead.

> AI生成