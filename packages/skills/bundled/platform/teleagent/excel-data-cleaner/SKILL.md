---
name: excel-data-cleaner
description: Clean and organize raw Excel/CSV data. Supports deduplication (full-row or by-column), missing value handling (drop, fill with value/mean/median/ffill/bfill/auto), and table merging (join by key columns like VLOOKUP, vertical stack, horizontal concatenation, multi-file batch merge, merge all sheets from one file). Use when user asks to clean data, remove duplicates, handle blanks/nulls, merge sheets or files, combine tables, consolidate multiple files/sheets, or any raw data preparation task on spreadsheets.
name_cn: Excel 数据整理
description_cn: 清洗和整理 Excel/CSV 原始数据，支持去重、空值处理、合并表格（含多文件合并与多工作表合并）
create_source: super-agent-skill-creator
---

# Excel Data Cleaner

Clean raw spreadsheet data with five core operations: dedup, fillna, merge, merge-multi, merge-sheets.

## Workflow

1. **Diagnose**: Read the file, check shape, dtypes, null counts, duplicate counts. Report findings to user.
2. **Plan**: Based on diagnosis and user intent, choose operation(s) and parameters.
3. **Execute**: Run `scripts/excel_cleaner.py` with chosen command.
4. **Report**: Parse the JSON output, summarize changes in plain language.

## Commands

All commands via `python <skill-dir>/scripts/excel_cleaner.py`. Output is JSON for machine parsing; always translate to plain language for the user.

### Dedup

```bash
python excel_cleaner.py dedup <input> <output> [--columns c1,c2] [--keep first|last]
```

- Default: full-row dedup, keep first occurrence
- Use `--columns` when duplicates should be checked on specific fields (e.g., phone + name)
- Use `--keep last` when newer records take priority

### Fillna

```bash
python excel_cleaner.py fillna <input> <output> [--method drop|value|mean|median|ffill|bfill|auto] [--fill-value VAL] [--columns c1,c2]
```

- **drop**: remove rows with nulls
- **value**: fill with `--fill-value` (e.g., 0, "unknown")
- **mean/median**: for numeric columns only
- **ffill/bfill**: for time-series or ordered data
- **auto**: smart detection — numeric: choose mean or median by skewness; text: use mode

When user doesn't specify a method, use **auto** by default. For detailed method guidance, read `references/workflow_guide.md`.

### Merge (two files)

```bash
python excel_cleaner.py merge <input1> <input2> <output> [--mode join|vstack|hstack] [--on key] [--how left|right|inner|outer] [--sheet1 NAME] [--sheet2 NAME]
```

- **join**: merge by key columns (like VLOOKUP). Use `--how` to control join type; default is `left`
- **vstack**: stack rows vertically (append data)
- **hstack**: concatenate columns horizontally

If `--on` is omitted in join mode, auto-detect common column names.

### Merge-Multi (multiple files)

```bash
python excel_cleaner.py merge-multi <output> --inputs f1.xlsx,f2.xlsx,f3.xlsx [--mode vstack|hstack] [--sheet NAME] [--all-sheets]
```

- Batch merge 3+ files at once, no need to call merge repeatedly
- **vstack**: stack all file rows vertically (most common for combining monthly/quarterly data)
- **hstack**: concatenate columns side by side
- Use `--sheet NAME` to read a specific sheet from each Excel file
- Use `--all-sheets` to read every sheet from each Excel file and merge them all

### Merge-Sheets (one file, multiple sheets)

```bash
python excel_cleaner.py merge-sheets <input> <output> [--sheet-names s1,s2] [--all]
```

- Consolidate all sheets (or selected sheets) from a single Excel file into one table
- Default merges all sheets; use `--sheet-names` to select specific ones
- Output is a single flat table with rows stacked vertically

## Multi-step Cleaning

Real tasks often chain operations. Example pipeline:

```bash
# 1. Merge multiple files
python excel_cleaner.py merge-multi .temp/merged.xlsx --inputs jan.xlsx,feb.xlsx,mar.xlsx

# 2. Dedup
python excel_cleaner.py dedup .temp/merged.xlsx .temp/deduped.xlsx --columns 订单号

# 3. Fillna
python excel_cleaner.py fillna .temp/deduped.xlsx .temp/filled.xlsx --method auto

# 4. Merge with reference
python excel_cleaner.py merge .temp/filled.xlsx ref.xlsx output.xlsx --mode join --on ID --how left
```

Use `.temp/` for intermediate files. Final output goes to the working directory.

## Tips

- Always run diagnosis first (read file, report nulls & dupes) before executing operations
- When user says "clean this data" without specifics, diagnose first then propose a plan
- For large files (>100k rows), warn about potential processing time
- CSV files are auto-detected by extension; no extra flags needed
- Preserve original file: never overwrite input, always write to a new output path
- When user wants to combine multiple Excel files into one, prefer `merge-multi` over calling `merge` repeatedly
- When user wants to merge sheets within a single file, use `merge-sheets`
