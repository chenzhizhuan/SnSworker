
# Root Cause Tracing

## Overview

Errors that surface at the end of a call chain are symptoms, not causes. The discipline of root cause tracing is to walk backward through callers and data flow until you find the original trigger — the first place where something went wrong — and fix it there. This reference complements Phase 3.5 (Error Resolution & Systematic Debugging) in the main SKILL.md, upgrading ad-hoc debugging into a systematic, reproducible process.

## When to Use

- Error manifests deep in the call stack, not at the entry point
- Stack trace shows a long call chain across multiple modules
- Unclear where an invalid or empty value originated
- Same error (e.g., `KeyError`, `TypeError`, `NoneType`) appears in multiple locations
- A "quick fix" suppresses the error but it reappears elsewhere

## The Tracing Process

### Step 1: Observe the Symptom

Read the error message completely. Note the exact `file:line` where it was raised.

```
Traceback (most recent call last):
  File "pipeline/indicators.py", line 42, in compute_ma
    ma = sum(values) / len(values)
TypeError: unsupported operand type(s) for /: 'int' and 'NoneType'
```

Observed: `len(values)` returns `None` — wait, `len()` never returns `None`. The actual problem is `values` is not a list. Trace it.

### Step 2: Find Immediate Cause

What code directly caused this? What is `values` at line 42?

```python
def compute_ma(values, period):
    window = values[-period:]          # line 41
    ma = sum(window) / len(window)     # line 42 — TypeError here
    return ma
```

`window` is `values[-period:]`. If `values` is an int (not a list), slicing returns `None` or throws. Where did `values` come from?

### Step 3: Ask "What Called This?"

Trace up the call chain. Find every caller of `compute_ma`.

```python
# pipeline/indicators.py — caller
def build_indicators(stock_data):
    closes = stock_data.get("close")   # could be None if data missing
    ma5 = compute_ma(closes, 5)        # passes None or non-list downstream
    return {"ma5": ma5}
```

Found it: `stock_data.get("close")` returns `None` when the key is missing or the value is `None`. But why is `close` missing?

### Step 4: Keep Tracing Up

Who called `build_indicators`? Where did `stock_data` come from?

```python
# pipeline/data_loader.py
def load_stock(code, date):
    raw = fetch_from_api(code, date)
    if raw is None:
        return {}                      # empty dict — no keys at all
    return parse_ohlcv(raw)

# pipeline/runner.py
def run_pipeline(code, date):
    stock_data = load_stock(code, date)     # returns {} when API fails
    indicators = build_indicators(stock_data)  # close is None → TypeError
```

### Step 5: Find Original Trigger

The original trigger is in `load_stock`: when the API returns `None`, it silently returns `{}` instead of signaling failure. This empty dict propagates through every downstream function, each of which assumes valid data exists.

**Bad fix (symptom-level):** Add `if values is None: return 0` inside `compute_ma`.
This hides the problem; the pipeline produces garbage (MA = 0) instead of failing loudly.

**Good fix (root-cause-level):** Make `load_stock` fail explicitly and let callers handle it.

```python
def load_stock(code, date):
    raw = fetch_from_api(code, date)
    if raw is None:
        raise DataUnavailableError(f"No data for {code} on {date}")
    return parse_ohlcv(raw)

def run_pipeline(code, date):
    try:
        stock_data = load_stock(code, date)
    except DataUnavailableError:
        return {"status": "skipped", "reason": "no_data"}
    indicators = build_indicators(stock_data)
    return indicators
```

Now the error is impossible to miss, and the caller decides how to handle missing data (skip, retry, alert). No silent corruption flows downstream.

## Integration with CE Phase 1.5 Impact Map

When a root cause is found, consult the Impact Map produced in Phase 1.5 (Context Discovery). The Impact Map lists all call sites and dependents of the function you are about to change. Verify that every affected caller is covered by your fix — either it handles the new error/return type, or you update it to do so. If the Impact Map shows callers outside the current file or module, check each one before declaring the fix complete.

## Adding Stack Traces for Investigation

When manual tracing through the code isn't enough — for example, the error only occurs in production or depends on runtime state — add instrumentation logging right before the problematic operation. Capture the directory, working directory, environment variables, and a full stack trace so you can reconstruct the call chain from logs.

```python
import traceback, os

def compute_ma(values, period):
    if not isinstance(values, (list, tuple)):
        print(f"[DEBUG] compute_ma received bad type: {type(values)}")
        print(f"[DEBUG] cwd: {os.getcwd()}")
        print(f"[DEBUG] DATA_DIR env: {os.environ.get('DATA_DIR', '<unset>')}")
        print(f"[DEBUG] stack trace:\n{''.join(traceback.format_stack())}")
        raise TypeError(f"expected list, got {type(values).__name__}")
    window = values[-period:]
    return sum(window) / len(window)
```

Deploy, reproduce the error once, read the stack trace from the log to find the original caller, then remove the instrumentation and apply the permanent fix at the root cause.

## Key Principle

**NEVER fix just where the error appears. Trace back to find the original trigger, fix at source.**

Symptom-level fixes (try/except swallows, `if x is None` guards at the crash site) hide bugs and cause silent data corruption. They also make future debugging harder because the real failure point is masked. Always walk the chain to the origin.

## Defense-in-Depth After Fix

After fixing the root cause, add validation at each layer the data passes through — see `defense-in-depth.md`. The goal is not redundancy but structural impossibility: if the same class of bad data ever enters the pipeline again, each layer should catch it early with a clear, actionable error rather than letting it propagate and crash in an unrelated function. For the stock pipeline example: `load_stock` raises `DataUnavailableError` (source fix), `build_indicators` validates input shape at entry (layer 1), and `compute_ma` asserts `isinstance(values, list)` in debug mode (layer 2). A bug that is structurally impossible to recur is a bug that stays fixed.