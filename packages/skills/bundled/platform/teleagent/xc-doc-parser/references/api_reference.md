# Xingchen Document Parse Cloud API Reference

## Endpoint

Default base URL used by the CLI:

```text
https://openapi.teleagi.cn
```

Submit endpoint:

```text
POST /aipaas/ocr/v1/xingchenOcr/multimodal
```

Pull query endpoint:

```text
GET /aipaas/lm/v1/asyncResult/query?requestId=<requestId>
```

The API is asynchronous. This CLI uses Pull mode by default.

## Authentication

The cloud API requires these headers:

| Header | Source |
|---|---|
| `Content-Type` | `application/json` on submit |
| `X-APP-ID` | App id from CLI arg, environment, encrypted config, or plain config fallback |
| `Authorization` | Provided directly or generated from app key |

Credential precedence:

```text
CLI arguments > environment variables > encrypted config > plain config
```

External override examples:

```bash
# Generated HMAC Authorization
export TELEAI_X_APP_ID="..."       # or XINGCHEN_APP_ID
export XINGCHEN_API_KEY="..."      # or TELEAI_X_APP_KEY

# Precomputed Authorization
export TELEAI_X_APP_ID="..."
export TELEAI_AUTHORIZATION="teleai-cloud-auth-v1/..."
```

Generated Authorization uses the implementation from the original adapter:

```text
auth_prefix = teleai-cloud-auth-v1/{appid}/{region}/{timestamp}/{expiration}
signing_key = HMAC_SHA256_HEX(app_key, auth_prefix)
canonical_request = METHOD + "\n" + PATH + "\n" + canonical_query + "\n" + "x-app-id:{appid}"
signature = HMAC_SHA256_HEX(signing_key, canonical_request)
Authorization = {auth_prefix}/x-app-id/{signature}
```

Defaults:

| Setting | Default |
|---|---|
| `base_url` | `https://openapi.teleagi.cn` |
| `region` | `QG` |
| `auth_expiration` | `43200` seconds |

## Submit Request

Request body is JSON.

Local file mode:

```json
{
  "image": "<base64 pdf/image>",
  "seqid": "REQ_...",
  "return_mode": 1,
  "image_type": 1,
  "callback_url": "http://127.0.0.1/unused",
  "html_escape": false
}
```

Public URL mode:

```json
{
  "image": "https://example.com/report.pdf",
  "seqid": "REQ_...",
  "return_mode": 1,
  "image_type": 0,
  "callback_url": "http://127.0.0.1/unused",
  "html_escape": false
}
```

Field notes:

| Field | CLI behavior |
|---|---|
| `seqid` | Auto-generated as `REQ_<millis>_<uuid8>` unless `--seqid` is provided |
| `image_type=0` | Used for public URL input |
| `image_type=1` | Used for local file input, sent as base64 |
| `return_mode=1` | Pull mode; the CLI polls the query endpoint |
| `callback_url` | Included because the API document marks it required; defaults to `http://127.0.0.1/unused` |
| `html_escape` | Defaults to `false` in this CLI for more readable Markdown/HTML |
| `page_range` | Added only when `--page-range` is passed |
| `password` | Added only when `--password` is passed |

Success response:

```json
{
  "msg": "调用成功",
  "code": "10000",
  "requestId": "REQ_17763255011823",
  "resultUrl": "https://openapi.teleagi.cn/aipaas/lm/v1/asyncResult/query"
}
```

For submit requests, any non-`10000` code is treated as submit failure. For query requests, `990003` is treated as "task still processing" and the CLI keeps polling until timeout.

## Query Response

The query endpoint is called with:

```text
/aipaas/lm/v1/asyncResult/query?requestId=<requestId>
```

Processing response shape:

```json
{
  "code": "990003",
  "message": "任务处理中"
}
```

The CLI treats query `code=990003` as a pending state, not as an error.

Completed response shape:

```json
{
  "code": "10000",
  "flag": 1,
  "data": {
    "words_result": [
      {
        "pages": [],
        "total_page_number": 1,
        "markdown": "..."
      }
    ],
    "timeSecond": 3.78
  }
}
```

The CLI extracts Markdown in this order:

1. `markdown` or `md` field anywhere in the completed result
2. `plain_text` or `full_text`
3. nested `text`, `content`, `value`, or `html` blocks
4. fallback Markdown explaining that raw JSON is preserved in `result.json`

## Wrapper features

- Pull mode query polling
- Batch manifest workflow
- Optional image/table asset download via `--download-images`
- Optional `--page-range` and `--password` passthrough
- Embedded obfuscated credentials with env/CLI override
- Static `Authorization` or generated HMAC `Authorization`


## Query pending behavior

For Pull mode, `code=990003` means the async task is still processing. The CLI does not treat this as a failure; it continues polling until `--timeout`.

Some gateway deployments may nest the completed result differently. The CLI therefore detects completed results recursively by looking for `words_result`, `pages`, `markdown`, `md`, `plain_text`, or `full_text`.
