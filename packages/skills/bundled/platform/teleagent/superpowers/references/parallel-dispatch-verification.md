---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '97e0cbcd-c15d-48ed-a8dc-017ca585845c'
  PropagateID: '97e0cbcd-c15d-48ed-a8dc-017ca585845c'
  ReservedCode1: 'b3c0c91b-bb1c-4b0c-b2d0-f9bedb4f3831'
  ReservedCode2: 'b3c0c91b-bb1c-4b0c-b2d0-f9bedb4f3831'
---

# 并行派发与验证实战备忘

## 派发前准备：预提取子代理无法直接读取的资源

当子代理需要读取 PDF、二进制文件等非文本资源时，主代理应在派发前预提取内容并传递文件路径，而非期望子代理自行解析。

### PDF 文本提取

用 `pypdf` 提取全文并保存为 `.txt`，将文本文件路径传给子代理：

```python
import pypdf
reader = pypdf.PdfReader(pdf_path)
parts = []
for i, page in enumerate(reader.pages):
    parts.append(f"===== PAGE {i+1} =====")
    parts.append(page.extract_text() or "")
full = "\n".join(parts)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(full)
```

### 多 Python 环境注意

Windows 上可能存在多个 Python 安装（如 TeleAgent 运行时 Python 与系统 Python），`pip install` 安装的包可能不在 `python` 默认指向的环境中。

- 用 `where.exe python` 确认所有 Python 路径
- 用 `python -m pip show <package>` 确认包安装在哪个环境
- 必要时用完整路径调用正确的 Python 可执行文件（如 `& 'C:\...\Python312\python.exe' script.py`）

### 子代理指令要点

在子代理 prompt 中写明预提取文件的完整路径，并提示可交叉核对原始文件。

---

## 派发后验证：Windows 环境常见陷阱

### `node --test` 路径参数

在 Windows PowerShell 下，`node --test test/` 会报 `Cannot find module` 错误——Node 将 `test/` 当作模块路径而非测试运行器参数，导致看似测试失败但实际是命令写法问题。

**正确用法**：

```bash
# 自动发现 test 目录下的 .test.js 文件（推荐）
node --test

# 如需指定路径，用 glob 模式
node --test "test/*.test.js"
```

### Playwright / 浏览器自动化不可用

当 `playwright_browser_navigate` 报 `transport closed` 或类似连接错误时，浏览器自动化不可用。回退验证方案：

1. **构建验证**：确认 `dist/` 目录存在且包含 `index.html`
2. **JS 语法检查**：`node --check <file.js>` 逐文件确认无语法错误
3. **HTTP 冒烟测试**：启动 dev/preview server 后用 `curl` 确认 200 响应
4. **文件完整性检查**：用 PowerShell `Test-Path` 批量确认所有交付文件存在且大小合理

### 子代理交付物补漏

并行子代理可能遗漏交付要求中的部分文件（如 README.md）。主代理在汇总阶段应逐项核对原始任务要求，发现缺失时直接补写，而非要求子代理重跑。