# TeleAI Xingchen Document Parse Skill

This package is organized by responsibility instead of placing all files at the package root.

```text
tele_xingchen/
  SKILL.md                          # Skill entry file
  scripts/                           # executable implementation
    xingchen_docparse.py
  references/                        # supporting documentation
    api_reference.md
    cli-guidance.md
    error-handling.md
    output_schema.md
    README_PATCH.md
```

Run from the directory that contains `tele_xingchen/`:

```bash
python tele_xingchen/scripts/xingchen_docparse.py --doctor
python tele_xingchen/scripts/xingchen_docparse.py report.pdf --output ./output
```


Diagnostics for an existing async request:

```bash
python tele_xingchen/scripts/xingchen_docparse.py query --request-id REQ_xxx
```
