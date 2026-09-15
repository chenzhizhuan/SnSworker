
# Windows/PowerShell-Specific Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves .bat/.cmd/.json file writing or PowerShell command construction on Windows (T1: always | T2: always). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Windows/PowerShell-Specific
- [ ] .bat files: CRLF line endings + GBK/ASCII encoding only (LF breaks cmd.exe)
- [ ] .json files: UTF-8 without BOM (`New-Object System.Text.UTF8Encoding($false)`)
- [ ] No `&&` chaining (PS 5.1 unsupported); use `;` or separate commands
- [ ] Never write to reserved device names: NUL, CON, PRN, AUX, COM1-9, LPT1-9
- [ ] Python脚本中文输出乱码：Windows代码页936(GBK)与Python UTF-8不匹配，需在`import sys`后加修复块：
  ```python
  # Windows 936代码页下stdout/stderr默认GBK，中文输出乱码，强制utf-8
  if sys.platform == "win32":
      for _stream in (sys.stdout, sys.stderr):
          if hasattr(_stream, "reconfigure"):
              _stream.reconfigure(encoding="utf-8")
  ```
  临时方案：`$env:PYTHONIOENCODING="utf-8"; python script.py`