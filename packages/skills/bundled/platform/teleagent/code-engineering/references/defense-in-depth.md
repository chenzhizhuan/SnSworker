---
AIGC:
  ContentProducer: ''
  ContentPropagator: ''
  Label: '1'
---

# Defense-in-Depth Validation

## Overview

After resolving a bug at its root cause, validate at **every layer** the data passes through — not just where the defect surfaced. The goal shifts from "we fixed the bug" to "we made the bug structurally impossible." A single validation point applies only to its own code path; multiple independent layers extend coverage to other paths. This methodology turns a one-off patch into systemic resilience.

## Why Multiple Layers

**"We fixed the bug"** = one validation at the failure point. A different input, refactor, or caller can skip it.

**"We made the bug impossible"** = validation at 4 independent layers. Each catches a different class of problem:

| Layer | Catches |
|-------|---------|
| Entry Point | Malformed input before it enters the system |
| Business Logic | Semantically valid but operationally wrong data |
| Environment | Operations that are legal but dangerous in this context |
| Debug | Silent corruption — no error, wrong result, no trace |

## The Four Layers

### Layer 1: Entry Point Validation

Reject invalid input at the API boundary before it propagates.

```python
@app.post("/api/stock/query")
def query_stock(stock_code: str):
    if not isinstance(stock_code, str) or not stock_code.isdigit() or len(stock_code) != 6:
        raise ValidationError(f"stock_code must be a 6-digit string, got: {stock_code!r}")
```

### Layer 2: Business Logic Validation

Ensure data makes sense for this specific operation, not just structurally valid.

```python
if stock_code not in market_data.get_all_codes():
    raise BusinessError(f"stock_code {stock_code} not found in market data")
if portfolio.get_position(stock_code) is None and not allow_new_position:
    raise BusinessError(f"No existing position for {stock_code}, new positions disabled")
```

### Layer 3: Environment Guards

Prevent dangerous operations in specific contexts — production vs test, read vs write.

```python
def write_trade_record(record: TradeRecord):
    if settings.ENVIRONMENT == "test" and not target_path.is_relative_to(settings.TEST_DATA_DIR):
        raise EnvironmentError(f"Refusing to write outside test data dir in env=test: {target_path}")
    if settings.READONLY_MODE:
        raise EnvironmentError("System is in read-only mode, writes are blocked")
```

### Layer 4: Debug Instrumentation

Capture context before dangerous operations so failures are traceable; not a gate, but a safety net.

```python
logger.info("DELETE stock_code=%s user=%s path=%s", stock_code, user_id, target_path)
logger.debug("Pre-delete state: %s", json.dumps(portfolio.get_position(stock_code)))
try:
    portfolio.delete(stock_code)
except Exception:
    logger.error("DELETE failed for %s, rolling back", stock_code, exc_info=True)
    raise
```

## Applying the Pattern

1. **Trace the data flow** — Where does the bad value originate? Map every function call, API boundary, and storage point it passes through from source to sink.
2. **Map all checkpoints** — List every point where data enters a new context (API call, function boundary, DB write, file I/O). Each is a candidate for validation.
3. **Add validation at each layer** — Entry Point rejects malformed data; Business Logic rejects semantically wrong data; Environment Guards block dangerous contexts; Debug Instrumentation captures state for forensics.
4. **Test each layer** — Deliberately test Layer 1 with (valid format, wrong value) and verify Layer 2 catches it. Disable the environment guard in production config and verify the operation still fails safely at Layer 4 logging.

## Key Insight

**All four layers are necessary. During testing, each layer catches bugs the others missed. Layer 1 catches malformed input; Layer 2 catches valid-but-wrong input; Layer 3 catches right-operation-wrong-context; Layer 4 catches silent corruption. Stopping at a single validation point is a fix — not a guarantee. Defense-in-depth is the difference between "patched" and "impossible."**

---

## Pattern: Thread-Level Timeout for Subprocess Calls

When calling external subprocesses (MCP servers, CLI tools, shell commands) from within a `ThreadPoolExecutor`, the subprocess's internal timeout mechanisms can fail in race conditions (e.g., subprocess restart during a blocked `readline()`). An outer thread-level timeout is the last line of defense.

**Symptom**: Process appears running (threads in Wait state, CPU frozen), but logs stop updating for 30+ minutes. The `ThreadPoolExecutor` future never completes because one worker thread is permanently blocked.

**Root Cause**: Internal subprocess timeouts (e.g., `reader.join(timeout=5)`) assume the subprocess is responsive. If the subprocess restarts mid-call or enters a deadlock, the internal timeout thread may never return, leaving the outer thread blocked forever.

**Fix Pattern** (Python):

```python
import threading

def call_with_timeout(func, args=(), timeout=20, fallback=None):
    """Wrap a potentially-blocking call in a thread with timeout protection.
    
    Use when: calling subprocess-based clients (MCP, CLI tools) from 
    ThreadPoolExecutor workers where a blocked call would hang the entire pool.
    """
    holder = [None]
    
    def _worker():
        holder[0] = func(*args)
    
    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout)
    
    if t.is_alive():
        return fallback
    
    return holder[0]
```

**Key Rules**:
- Always use `daemon=True` — if the thread is truly stuck, it won't prevent process exit
- Timeout should be generous (3-5x expected call time) to avoid false positives
- Always provide a `fallback` (alternative data source, cached data, or `None` with graceful degradation)
- Log timeout events for monitoring

## Pattern: PID Lock File Management

When launching long-running scripts that implement their own PID-based lock mechanism:

1. **Never pre-create the PID file** before launching the script — the script's own lock check will see the file and conclude "another instance is running," then skip the main flow entirely
2. **Always clean up stale PID files** before retrying — a killed process leaves its PID file behind, and the next launch will refuse to start
3. **PID files should contain PID + timestamp** — allows detecting stale locks (process no longer exists) vs. active locks

```python
# Correct PID lock pattern in the script itself
import os, psutil

def acquire_pid_lock(pid_file):
    if os.path.exists(pid_file):
        content = open(pid_file).read().strip()
        old_pid = int(content.split("|")[0])
        if psutil.pid_exists(old_pid):
            print(f"[LOCK] Another instance running (PID={old_pid}), exiting")
            return False
        else:
            print(f"[LOCK] Stale PID file (PID={old_pid} gone), removing")
            os.remove(pid_file)
    
    with open(pid_file, "w") as f:
        f.write(f"{os.getpid()}|{datetime.now().isoformat()}")
    return True
```

**Launcher-side rule**: Only start the process and let it manage its own PID file. Do NOT write the PID file on behalf of the script.

## Pattern: Long-Running Script — Background Launch + Poll

When a script's expected runtime exceeds the PowerShell tool timeout (typically 10–30 min), foreground execution will be killed mid-run. Use `Start-Process` to launch in the background, then poll log files and process status in separate short-timeout calls.

**Symptom**: Script runs for 20+ minutes; PowerShell tool kills it at 10 or 30 min timeout; stdout/stderr redirect files are 0 KB because Python buffered output was never flushed before the kill.

**Root Cause**: PowerShell tool has a hard timeout. Python's default output buffering means redirected stdout/stderr may not be flushed to disk until process exit — if the process is killed, all buffered output is lost.

**Fix Pattern** (PowerShell):

```powershell
# 1. Clean up stale PID files from previous killed runs
$pidPath = Join-Path $v "data\.daily_signal.pid"
if (Test-Path $pidPath) { Remove-Item $pidPath -Force }

# 2. Clear old logs
$logFile = Join-Path $v "logs\daily_signal_out.log"
$errFile = Join-Path $v "logs\daily_signal_err.log"
if (Test-Path $logFile) { Clear-Content $logFile -Force }
if (Test-Path $errFile) { Clear-Content $errFile -Force }

# 3. Launch with -u (unbuffered) so output flushes immediately
$proc = Start-Process -FilePath $python `
    -ArgumentList "-u", "script.py", "--force" `
    -WorkingDirectory $v `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -PassThru -NoNewWindow

# 4. Poll in separate tool calls (each with short timeout)
```

**Key Rules**:
- **Always use `-u` flag** (`python -u`) for unbuffered output
- **Do NOT combine `-NoNewWindow` with `-WindowStyle`** — PowerShell rejects this combination
- **Clean stale PID files before launch** — a killed process leaves its PID lock
- **Poll with short-timeout tool calls** — each poll should be < 30s
- **Completion detection**: search logs for domain-specific markers, or check output file timestamps
- **Failure detection**: search for "Traceback", "Error", "Killed" in the log

**When to use**: Script runtime > 10 minutes, produces output files, writes progress to stdout/stderr.
**When NOT to use**: Script runs < 5 minutes (run foreground), or no log/output to poll.

<!-- Updated: 2026-09-08, removed ChanLunPro-specific example details while keeping reusable patterns -->