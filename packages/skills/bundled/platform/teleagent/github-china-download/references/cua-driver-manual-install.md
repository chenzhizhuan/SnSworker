# Manual cua-driver Install (Windows, GitHub blocked)

When `hermes computer-use install` fails because GitHub times out.

## Steps

```bash
# 1. Check current version from install script output
#    Look for: "using baked release: cua-driver-rs-v0.9.0"

# 2. Download via proxy
VER="0.9.0"  # adjust to current
URL="https://github.com/trycua/cua/releases/download/cua-driver-rs-v${VER}/cua-driver-rs-${VER}-windows-x86_64.zip"
curl -sL -o "$USERPROFILE/cua-driver.zip" "https://ghfast.top/$URL" \
  --connect-timeout 10 -m 120

# 3. Verify (should be ~12MB)
ls -la "$USERPROFILE/cua-driver.zip"

# 4. Extract
OUTDIR="$HOME/AppData/Local/Programs/Cua/cua-driver/bin"
mkdir -p "$OUTDIR"
cd "$OUTDIR" && unzip -o "$USERPROFILE/cua-driver.zip"

# 5. Flatten subdirectory
mv "$OUTDIR"/cua-driver-rs-*/*.exe "$OUTDIR/"
rmdir "$OUTDIR"/cua-driver-rs-*/

# 6. Create package home (installer expects this)
mkdir -p "$HOME/.cua-driver"

# 7. Verify
"$OUTDIR/cua-driver.exe" --version
# Expected: cua-driver 0.9.0

# 8. Cleanup
rm -f "$USERPROFILE/cua-driver.zip"
```

## Starting the daemon

cua-driver requires a running daemon before `call` commands work.

```bash
# Start daemon (background — it's a long-lived server)
CUA="$HOME/AppData/Local/Programs/Cua/cua-driver/bin/cua-driver.exe"
"$CUA" serve &   # or use terminal background=true

# IMPORTANT: Do NOT pass --socket '\\.\pipe\cua-driver' from MSYS/bash.
# Backslash escaping breaks the pipe path → OS error 123.
# Bare `cua-driver serve` uses the correct default pipe automatically.
```

## Verifying it works

```bash
# Screen dimensions
"$CUA" call get_screen_size '{}'
# Expected: {"height": N, "scale_factor": 1.0, "width": N}

# Visible windows
"$CUA" call list_windows '{}'

# Full diagnostics
"$CUA" doctor
```

## Key capabilities (tool list)

| Tool | Purpose |
|------|---------|
| get_desktop_state | Full-screen screenshot |
| get_window_state | UIA element tree for a pid |
| click / double_click / right_click | Mouse actions on a pid |
| drag | Drag from (x1,y1) to (x2,y2) |
| scroll | Scroll in a window |
| press_key / hotkey | Keyboard input |
| launch_app / kill_app / list_apps | App lifecycle |
| list_windows / bring_to_front | Window management |
| browser_navigate / browser_click / browser_type | Browser automation |
| get_screen_size / get_cursor_position | Screen info |

## Expected binaries

- `cua-driver.exe` (~22MB) — main driver
- `cua-driver-uia.exe` (~11MB) — Windows UIA backend

## Install locations

| Path | Purpose |
|------|---------|
| `%LOCALAPPDATA%\Programs\Cua\cua-driver\bin\` | Binaries |
| `%USERPROFILE%\.cua-driver\` | Package home / state |
