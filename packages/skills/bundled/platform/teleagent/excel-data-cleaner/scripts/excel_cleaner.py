#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Excel Data Cleaner - 去重、空值处理、合并表格

Usage:
    python excel_cleaner.py dedup <input> <output> [--columns col1,col2] [--keep first|last]
    python excel_cleaner.py fillna <input> <output> [--method drop|value|mean|median|ffill|bfill|auto] [--fill-value VALUE] [--columns col1,col2]
    python excel_cleaner.py merge <input1> <input2> <output> [--mode join|vstack|hstack] [--on col1,col2] [--how left|right|inner|outer] [--sheet1 NAME] [--sheet2 NAME]
    python excel_cleaner.py merge-multi <output> [--inputs f1.xlsx,f2.xlsx,...] [--mode vstack|hstack] [--sheet NAME] [--all-sheets]
    python excel_cleaner.py merge-sheets <input> <output> [--sheet-names s1,s2] [--all]
"""

import argparse
import sys
import os
import json
import glob

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is required. Install with: pip install pandas openpyxl")
    sys.exit(1)


def read_file(path, sheet_name=None):
    """Read Excel or CSV file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        return pd.read_csv(path, encoding='utf-8-sig')
    elif ext in ('.xlsx', '.xlsm', '.xls'):
        kwargs = {'engine': 'openpyxl'} if ext != '.xls' else {}
        if sheet_name:
            kwargs['sheet_name'] = sheet_name
        return pd.read_excel(path, **kwargs)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def write_file(df, path):
    """Write DataFrame to Excel or CSV."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        df.to_csv(path, index=False, encoding='utf-8-sig')
    else:
        df.to_excel(path, index=False, engine='openpyxl')


def cmd_dedup(args):
    """Remove duplicate rows."""
    df = read_file(args.input)
    subset = args.columns.split(',') if args.columns else None
    keep = args.keep or 'first'
    before = len(df)
    result = df.drop_duplicates(subset=subset, keep=keep)
    after = len(result)
    write_file(result, args.output)
    print(json.dumps({
        "action": "dedup",
        "rows_before": before,
        "rows_after": after,
        "rows_removed": before - after,
        "keep": keep,
        "subset": subset,
        "output": args.output
    }, ensure_ascii=False))


def _fill_auto(series):
    """Auto-detect best fill strategy for a column."""
    dtype = series.dtype
    null_count = series.isnull().sum()
    if null_count == 0:
        return series
    if pd.api.types.is_numeric_dtype(dtype):
        skew = series.skew()
        if abs(skew) > 1.5:
            return series.fillna(series.median())
        else:
            return series.fillna(series.mean())
    else:
        mode = series.mode()
        if len(mode) > 0:
            return series.fillna(mode.iloc[0])
        return series.fillna(method='ffill')


def cmd_fillna(args):
    """Handle missing values."""
    df = read_file(args.input)
    method = args.method or 'auto'
    cols = args.columns.split(',') if args.columns else None
    fill_value = args.fill_value
    before = int(df.isnull().sum().sum())

    if cols:
        target_cols = [c.strip() for c in cols]
    else:
        target_cols = df.columns.tolist()

    if method == 'drop':
        result = df.dropna(subset=target_cols if cols else None)
    elif method == 'value':
        if fill_value is None:
            print("ERROR: --fill-value is required when method=value", file=sys.stderr)
            sys.exit(1)
        result = df.copy()
        result[target_cols] = result[target_cols].fillna(fill_value)
    elif method == 'mean':
        result = df.copy()
        for c in target_cols:
            if pd.api.types.is_numeric_dtype(result[c]):
                result[c] = result[c].fillna(result[c].mean())
    elif method == 'median':
        result = df.copy()
        for c in target_cols:
            if pd.api.types.is_numeric_dtype(result[c]):
                result[c] = result[c].fillna(result[c].median())
    elif method == 'ffill':
        result = df.copy()
        result[target_cols] = result[target_cols].fillna(method='ffill')
    elif method == 'bfill':
        result = df.copy()
        result[target_cols] = result[target_cols].fillna(method='bfill')
    elif method == 'auto':
        result = df.copy()
        for c in target_cols:
            result[c] = _fill_auto(result[c])
    else:
        print(f"ERROR: Unknown method: {method}", file=sys.stderr)
        sys.exit(1)

    after = int(result.isnull().sum().sum())
    rows_before = len(df)
    rows_after = len(result)
    write_file(result, args.output)
    print(json.dumps({
        "action": "fillna",
        "method": method,
        "cells_filled": before - after,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_dropped": rows_before - rows_after,
        "output": args.output
    }, ensure_ascii=False))


def cmd_merge(args):
    """Merge two tables."""
    df1 = read_file(args.input1, sheet_name=args.sheet1)
    df2 = read_file(args.input2, sheet_name=args.sheet2)
    mode = args.mode or 'join'

    if mode == 'join':
        on = args.on.split(',') if args.on else None
        how = args.how or 'left'
        if not on:
            common = list(set(df1.columns) & set(df2.columns))
            if not common:
                print("ERROR: No common columns found. Use --on to specify merge keys.", file=sys.stderr)
                sys.exit(1)
            on = common
        result = pd.merge(df1, df2, on=on, how=how, suffixes=('', '_2'))
    elif mode == 'vstack':
        result = pd.concat([df1, df2], ignore_index=True)
    elif mode == 'hstack':
        if len(df1) != len(df2):
            print(f"WARNING: Row counts differ ({len(df1)} vs {len(df2)}). Padding shorter table.", file=sys.stderr)
        result = pd.concat([df1.reset_index(drop=True), df2.reset_index(drop=True)], axis=1)
    else:
        print(f"ERROR: Unknown merge mode: {mode}", file=sys.stderr)
        sys.exit(1)

    write_file(result, args.output)
    print(json.dumps({
        "action": "merge",
        "mode": mode,
        "rows_in": len(df1) + len(df2),
        "rows_out": len(result),
        "cols_out": len(result.columns),
        "output": args.output
    }, ensure_ascii=False))


def cmd_merge_multi(args):
    """Merge multiple Excel/CSV files into one."""
    file_list = [f.strip() for f in args.inputs.split(',') if f.strip()]
    if not file_list:
        print("ERROR: No input files specified.", file=sys.stderr)
        sys.exit(1)

    mode = args.mode or 'vstack'
    dfs = []
    file_info = []

    for fpath in file_list:
        try:
            if args.all_sheets:
                ext = os.path.splitext(fpath)[1].lower()
                if ext == '.csv':
                    df = pd.read_csv(fpath, encoding='utf-8-sig')
                    dfs.append(df)
                    file_info.append({"file": fpath, "sheet": "csv", "rows": len(df)})
                else:
                    xl = pd.ExcelFile(fpath, engine='openpyxl')
                    for sname in xl.sheet_names:
                        df = pd.read_excel(fpath, sheet_name=sname, engine='openpyxl')
                        dfs.append(df)
                        file_info.append({"file": fpath, "sheet": sname, "rows": len(df)})
            else:
                df = read_file(fpath, sheet_name=args.sheet)
                dfs.append(df)
                file_info.append({"file": fpath, "rows": len(df)})
        except Exception as e:
            print(f"WARNING: Failed to read {fpath}: {e}", file=sys.stderr)

    if not dfs:
        print("ERROR: No valid data read from input files.", file=sys.stderr)
        sys.exit(1)

    if mode == 'vstack':
        result = pd.concat(dfs, ignore_index=True)
    elif mode == 'hstack':
        # Align all to the max row count
        max_rows = max(len(df) for df in dfs)
        aligned = []
        for df in dfs:
            if len(df) < max_rows:
                padded = df.reindex(range(max_rows))
                aligned.append(padded)
            else:
                aligned.append(df)
        result = pd.concat(aligned, axis=1)
    else:
        print(f"ERROR: merge-multi only supports vstack and hstack modes, got {mode}", file=sys.stderr)
        sys.exit(1)

    write_file(result, args.output)
    print(json.dumps({
        "action": "merge-multi",
        "mode": mode,
        "files_processed": len(file_info),
        "file_details": file_info,
        "total_rows_in": sum(d["rows"] for d in file_info),
        "rows_out": len(result),
        "cols_out": len(result.columns),
        "output": args.output
    }, ensure_ascii=False))


def cmd_merge_sheets(args):
    """Merge multiple sheets from a single Excel file into one."""
    ext = os.path.splitext(args.input)[1].lower()
    if ext == '.csv':
        print("ERROR: CSV files have no sheets. Use dedup or fillna instead.", file=sys.stderr)
        sys.exit(1)

    xl = pd.ExcelFile(args.input, engine='openpyxl')

    if args.all_sheets:
        sheet_names = xl.sheet_names
    elif args.sheet_names:
        sheet_names = [s.strip() for s in args.sheet_names.split(',')]
    else:
        sheet_names = xl.sheet_names

    dfs = []
    sheet_info = []
    for sname in sheet_names:
        df = pd.read_excel(args.input, sheet_name=sname, engine='openpyxl')
        dfs.append(df)
        sheet_info.append({"sheet": sname, "rows": len(df), "cols": len(df.columns)})

    if not dfs:
        print("ERROR: No sheets to merge.", file=sys.stderr)
        sys.exit(1)

    result = pd.concat(dfs, ignore_index=True)
    write_file(result, args.output)
    print(json.dumps({
        "action": "merge-sheets",
        "sheets_merged": len(sheet_info),
        "sheet_details": sheet_info,
        "total_rows_in": sum(d["rows"] for d in sheet_info),
        "rows_out": len(result),
        "cols_out": len(result.columns),
        "output": args.output
    }, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Excel Data Cleaner')
    sub = parser.add_subparsers(dest='command')

    # dedup
    p_dedup = sub.add_parser('dedup', help='Remove duplicates')
    p_dedup.add_argument('input', help='Input file path')
    p_dedup.add_argument('output', help='Output file path')
    p_dedup.add_argument('--columns', help='Comma-separated columns to check (default: all)')
    p_dedup.add_argument('--keep', choices=['first', 'last'], default='first')

    # fillna
    p_fill = sub.add_parser('fillna', help='Handle missing values')
    p_fill.add_argument('input', help='Input file path')
    p_fill.add_argument('output', help='Output file path')
    p_fill.add_argument('--method', choices=['drop', 'value', 'mean', 'median', 'ffill', 'bfill', 'auto'], default='auto')
    p_fill.add_argument('--fill-value', help='Value to fill when method=value')
    p_fill.add_argument('--columns', help='Comma-separated columns to process (default: all)')

    # merge (two files)
    p_merge = sub.add_parser('merge', help='Merge two tables')
    p_merge.add_argument('input1', help='First input file')
    p_merge.add_argument('input2', help='Second input file')
    p_merge.add_argument('output', help='Output file path')
    p_merge.add_argument('--mode', choices=['join', 'vstack', 'hstack'], default='join')
    p_merge.add_argument('--on', help='Comma-separated merge key columns')
    p_merge.add_argument('--how', choices=['left', 'right', 'inner', 'outer'], default='left')
    p_merge.add_argument('--sheet1', help='Sheet name in first file (if Excel)')
    p_merge.add_argument('--sheet2', help='Sheet name in second file (if Excel)')

    # merge-multi (multiple files)
    p_mmulti = sub.add_parser('merge-multi', help='Merge multiple files into one')
    p_mmulti.add_argument('output', help='Output file path')
    p_mmulti.add_argument('--inputs', required=True, help='Comma-separated input file paths')
    p_mmulti.add_argument('--mode', choices=['vstack', 'hstack'], default='vstack')
    p_mmulti.add_argument('--sheet', help='Sheet name to read from each file (if Excel)')
    p_mmulti.add_argument('--all-sheets', action='store_true', help='Read all sheets from each Excel file')

    # merge-sheets (multiple sheets from one file)
    p_msheets = sub.add_parser('merge-sheets', help='Merge sheets from one Excel file')
    p_msheets.add_argument('input', help='Input Excel file')
    p_msheets.add_argument('output', help='Output file path')
    p_msheets.add_argument('--sheet-names', help='Comma-separated sheet names to merge (default: all)')
    p_msheets.add_argument('--all', dest='all_sheets', action='store_true', help='Merge all sheets (default behavior)')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        'dedup': cmd_dedup,
        'fillna': cmd_fillna,
        'merge': cmd_merge,
        'merge-multi': cmd_merge_multi,
        'merge-sheets': cmd_merge_sheets,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
