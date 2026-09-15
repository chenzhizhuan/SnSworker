# Adaptation Notes

This package adapts the old unauthenticated Open OCR wrapper to the authenticated TeleAI Xingchen Document Parse cloud API, while keeping the batch `manifest.json` and `read` workflow from the newer agent-oriented wrapper.

## Main code changes

1. Endpoint changed from:

```text
POST /api/v1/open/ocr/task
GET  /api/v1/open/ocr/result/{requestId}
```

to:

```text
POST /aipaas/ocr/v1/xingchenOcr/multimodal
GET  /aipaas/lm/v1/asyncResult/query?requestId=<requestId>
```

2. Request body changed from `multipart/form-data` to JSON.

3. Local files are sent as:

```json
{"image_type": 1, "image": "<base64>"}
```

4. Public URLs are sent as:

```json
{"image_type": 0, "image": "https://..."}
```

5. Authentication now supports three modes, in this precedence order:

```text
CLI arguments > environment variables > encrypted config > plain config
```

The production AppID/AppKey are not stored as plain strings. They are decoded at runtime and used only to generate the `Authorization` header. `--doctor` reports only the credential source and a short non-reversible fingerprint; it does not print the AppID, AppKey, or Authorization value.

This is obfuscation, not strong secret protection. Anyone who can read and execute the source can still reverse the values. For strong protection, place the credential in a server-side gateway or secret manager and let this CLI call that gateway instead.

6. Success code changed from `200` to `10000`; Pull-query pending code `990003` is treated as "task still processing" and does not fail the run.

7. The Pull-mode query loop now handles both pending forms: explicit `code=990003` and successful-but-empty responses. Completed results are read from `data.words_result[0].markdown`, with recursive fallback extraction retained.

8. `callback_url` is included because the API document marks it required. The CLI defaults to `http://127.0.0.1/unused` in Pull mode, matching the older adapter behavior, but you can override it with `--callback-url`.

9. The older adapter's optional features were brought back: generated TeleAI HMAC Authorization, `--page-range`, `--password`, `--download-images`, and expanded image suffix support.

## Quick run with encrypted config

```bash
python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output ./output
```

## Override credentials for development

```bash
export TELEAI_X_APP_ID="..."
export XINGCHEN_API_KEY="..."
python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output ./output
```

## Test missing credentials

```bash
python tele_xingchen/scripts/xingchen_docparse.py --doctor
```

## Check config

```bash
python tele_xingchen/scripts/xingchen_docparse.py --doctor
```


## v0.4.2 pending/timeout diagnostics

- Poll logs now include `count`, elapsed seconds, API `code`, and message so long-running Pull tasks can be distinguished from silent hangs.
- Query responses with nested `markdown`, `pages`, or `words_result` are detected recursively to avoid treating completed results as pending when the gateway nests the payload differently.
- On timeout, the last query response is saved as `timeout_status.json` beside the expected artifact directory.
- Added one-shot raw query helper:

```bash
python tele_xingchen/scripts/xingchen_docparse.py query --request-id REQ_xxx
```
