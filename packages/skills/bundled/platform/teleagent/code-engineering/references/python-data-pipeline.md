
# Python Data Pipeline Template

Standard Python data processing module for TeleAI projects. Designed to be called from Node.js via `execFileSync`.

## Module Skeleton (`main.py`)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Data processing module.
Called by Node.js: python main.py <command> [args...]
Output: JSON to stdout (single line)
Logging: print(..., file=sys.stderr)
"""
import sys
import json
import os
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging (stderr only — never pollute stdout JSON output)
# ---------------------------------------------------------------------------
def log(msg, level='INFO'):
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"[{level}] {ts} {msg}", file=sys.stderr)

def log_error(msg):
    log(msg, 'ERROR')

# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------
def ok(data=None, message='success'):
    result = {'code': 0, 'message': message}
    if data is not None:
        result['data'] = data
    return json.dumps(result, ensure_ascii=False)

def fail(message, code=1):
    return json.dumps({'code': code, 'message': message}, ensure_ascii=False)

# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------
def retry(max_retries=3, delay=1.0, backoff=2.0):
    import functools
    import time
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    if attempt < max_retries - 1:
                        wait = delay * (backoff ** attempt)
                        log(f"Retry {attempt+1}/{max_retries} after error: {e}, wait {wait:.1f}s")
                        time.sleep(wait)
            raise last_err
        return wrapper
    return decorator

# ---------------------------------------------------------------------------
# Safe numeric operations
# ---------------------------------------------------------------------------
def safe_divide(a, b, default=0):
    """Divide with zero/None protection."""
    if b is None or b == 0 or a is None:
        return default
    return a / b

def safe_pct(a, b, decimals=2):
    """Calculate percentage with protection."""
    result = safe_divide(a, b, 0) * 100
    return round(result, decimals)

# ---------------------------------------------------------------------------
# Data validation helpers
# ---------------------------------------------------------------------------
def validate_required(data_dict, required_keys):
    """Validate required keys exist and are not None/empty."""
    missing = [k for k in required_keys if not data_dict.get(k)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

def clean_dataframe(df):
    """Standard DataFrame cleaning pipeline."""
    import pandas as pd
    # Strip whitespace from string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    # Forward-fill NaN, then backward-fill
    df = df.ffill().bfill()
    # Convert date-like columns
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            try:
                df[col] = pd.to_datetime(df[col]).apply(lambda x: str(x)[:10])
            except:
                pass
    return df

# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------
def load_json(filepath):
    """Load JSON with UTF-8 encoding."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filepath, data, indent=2):
    """Save JSON with UTF-8, no BOM."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)

def get_cache_path(cache_dir, key):
    """Get cache file path with subdirectory creation."""
    os.makedirs(cache_dir, exist_ok=True)
    safe_key = key.replace('/', '_').replace('\\', '_').replace(':', '_')
    return os.path.join(cache_dir, f"{safe_key}.json")

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
def cmd_process(param):
    """Example: Process a single item."""
    log(f"Processing: {param}")
    # ... business logic ...
    data = {'result': param, 'timestamp': datetime.now().isoformat()}
    return ok(data)

def cmd_batch(params_json):
    """Example: Process batch items."""
    params = json.loads(params_json)
    log(f"Batch processing {len(params)} items")
    results = []
    for i, p in enumerate(params):
        try:
            result = process_single(p)  # implement this
            results.append({'index': i, 'success': True, 'data': result})
        except Exception as e:
            log_error(f"Item {i} failed: {e}")
            results.append({'index': i, 'success': False, 'error': str(e)})
    return ok(results, f'Processed {len(results)} items')

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        if len(sys.argv) < 2:
            print(fail('Usage: python main.py <command> [args...]'), file=sys.stderr)
            sys.exit(1)

        command = sys.argv[1]

        if command == 'process':
            if len(sys.argv) < 3:
                print(fail('Missing parameter'), file=sys.stderr)
                sys.exit(1)
            print(cmd_process(sys.argv[2]))

        elif command == 'batch':
            if len(sys.argv) < 3:
                print(fail('Missing parameters JSON'), file=sys.stderr)
                sys.exit(1)
            print(cmd_batch(sys.argv[2]))

        else:
            print(fail(f'Unknown command: {command}'), file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        log_error(f"Fatal: {e}")
        print(fail(str(e)), file=sys.stderr)
        sys.exit(1)
```

## Key Points

| Concern | Solution |
|---------|----------|
| stdout vs stderr | All log output to stderr; only final JSON to stdout |
| JSON output | `ensure_ascii=False` for Chinese; single `json.dumps` call |
| Error handling | try/except in main; never let unhandled exceptions crash |
| Retry mechanism | Decorator with exponential backoff |
| Zero-division | `safe_divide()` and `safe_pct()` utility functions |
| DataFrame cleaning | `clean_dataframe()` handles common issues |
| File encoding | Explicit `encoding='utf-8'` everywhere |
| Command pattern | `cmd_<name>` functions dispatched by sys.argv[1] |
| Exit codes | 0 for success, 1 for error |

## Usage Checklist When Copying

- [ ] Rename `cmd_process` / `cmd_batch` to actual command names
- [ ] Implement actual business logic in handler functions
- [ ] Add project-specific imports (pandas, akshare, etc.) at the top
- [ ] Adjust retry parameters based on API rate limits
- [ ] Add input validation specific to the domain
- [ ] Test with: `python main.py <command> <param>` from PowerShell
<!-- Updated: 2026-04-26, initial creation -->