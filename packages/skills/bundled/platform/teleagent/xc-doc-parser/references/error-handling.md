# Xingchen Document Parse Error Handling

## Agent decision rules

- Do not ask normal private users for AppID/AppKey. This build loads them from encrypted config by default.
- Prefer external environment credentials only for operator-controlled deployments, key rotation, or local testing.
- `callback_url` is marked required by the API document. In Pull mode this wrapper defaults it to `http://127.0.0.1/unused`; use a real callback URL only if the service enforces one in the deployment environment.
- Local file not found or unsupported suffix: stop and ask for a valid PDF/image.
- Submit non-`10000` code: report the exact code and message, but never print credential values or Authorization headers.
- Query `code=990003`: treat as task still processing and continue polling until timeout.
- Query non-`10000`/non-`990003` code: report the exact code and message.
- Successful query with no usable result is treated as still processing until timeout. The detector searches recursively for `words_result`, `pages`, `markdown`, `md`, `plain_text`, or `full_text`.
- Timeout: report the request ID, save the last query response to `timeout_status.json`, and ask whether to retry or increase `--timeout`.
- Batch parse failure: keep successful document statuses in `manifest.json`; do not silently drop failed items.
- Resume skip: treat as success if both Markdown and JSON artifacts already exist.

## Retryable transport conditions

The CLI retries transient transport failures:

```text
HTTP 408
HTTP 429
HTTP 500
HTTP 502
HTTP 503
HTTP 504
Network error
```

## Non-retryable conditions

Do not retry automatically when:

- The input file is missing or not a file.
- The file suffix is unsupported.
- `X-APP-ID` is missing after config and external overrides are checked.
- Neither static `Authorization`, app key, nor config fallback is available.
- The submit API returns a business error code other than `10000`.
- The query API returns a business error code other than `10000` or pending code `990003`.
- The user must provide a different file, URL, or callback URL.

## Output contract

- stdout: Markdown, raw JSON, batch summary JSON, or `read` output only.
- stderr: progress and error messages only.
- exit code `0`: all requested documents succeeded or were skipped.
- exit code `1`: at least one requested document failed, or the command arguments are invalid.
- Diagnostics may show credential source and fingerprint, but must not show plaintext AppID, AppKey, or Authorization values.
