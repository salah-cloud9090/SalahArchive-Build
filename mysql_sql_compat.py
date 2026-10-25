# -*- coding: utf-8 -*-
"""Conservative SQL compatibility helpers for the SQLite -> MySQL migration.

This module is intentionally NOT wired into main.py yet. It translates only
well-defined SQL fragments and rejects known unsafe/unsupported constructs.
"""
from __future__ import annotations
import re

class SQLCompatibilityError(ValueError):
    pass

def _rewrite_outside_literals(sql: str, transform):
    """Apply transform to SQL code only, preserving quotes and comments."""
    out=[]; i=0; n=len(sql); state="code"
    while i<n:
        ch=sql[i]
        nxt=sql[i+1] if i+1<n else ""
        if state=="code":
            if ch=="'" or ch=='"' or ch=="`":
                state={"'":"single", '"':"double", "`":"backtick"}[ch]
                out.append(ch); i+=1; continue
            if ch=="-" and nxt=="-":
                state="line_comment"; out.extend([ch,nxt]); i+=2; continue
            if ch=="#" :
                state="line_comment"; out.append(ch); i+=1; continue
            if ch=="/" and nxt=="*":
                state="block_comment"; out.extend([ch,nxt]); i+=2; continue
            replacement, consumed = transform(sql, i)
            if consumed:
                out.append(replacement); i+=consumed; continue
            out.append(ch); i+=1; continue
        if state in ("single","double","backtick"):
            quote={"single":"'","double":'"',"backtick":"`"}[state]
            out.append(ch); i+=1
            if ch=="\\" and state!="backtick" and i<n:
                out.append(sql[i]); i+=1; continue
            if ch==quote:
                if i<n and sql[i]==quote:
                    out.append(sql[i]); i+=1
                else:
                    state="code"
            continue
        if state=="line_comment":
            out.append(ch); i+=1
            if ch=="\n": state="code"
            continue
        if state=="block_comment":
            if ch=="*" and nxt=="/":
                out.extend([ch,nxt]); i+=2; state="code"
            else:
                out.append(ch); i+=1
            continue
    return "".join(out)

def _mask_literals_and_comments(sql: str) -> str:
    """Mask quoted text and comments so safety checks inspect SQL syntax only."""
    out = list(sql)
    i = 0
    n = len(sql)
    state = "code"
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch in ("'", '"', "`"):
                state = {"'": "single", '"': "double", "`": "backtick"}[ch]
                out[i] = " "
                i += 1
                continue
            if ch == "-" and nxt == "-":
                state = "line_comment"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if ch == "#":
                state = "line_comment"
                out[i] = " "
                i += 1
                continue
            if ch == "/" and nxt == "*":
                state = "block_comment"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            i += 1
            continue
        if state in ("single", "double", "backtick"):
            quote = {"single": "'", "double": '"', "backtick": "`"}[state]
            if ch != "\n":
                out[i] = " "
            i += 1
            if ch == "\\" and state != "backtick" and i < n:
                if sql[i] != "\n": out[i] = " "
                i += 1
                continue
            if ch == quote:
                if i < n and sql[i] == quote:
                    if sql[i] != "\n": out[i] = " "
                    i += 1
                else:
                    state = "code"
            continue
        if state == "line_comment":
            if ch != "\n": out[i] = " "
            i += 1
            if ch == "\n": state = "code"
            continue
        if state == "block_comment":
            if ch != "\n": out[i] = " "
            i += 1
            if ch == "*" and nxt == "/":
                if i < n and sql[i] != "\n": out[i] = " "
                i += 1
                state = "code"
            continue
    return "".join(out)

def translate_sql(sql: str) -> str:
    """Translate a limited SQLite SQL subset into MySQL syntax."""
    if not isinstance(sql,str) or not sql.strip():
        raise SQLCompatibilityError("SQL statement is empty")
    syntax_only = _mask_literals_and_comments(sql)
    stripped = syntax_only.lstrip()
    if re.match(r"(?is)^PRAGMA\b", stripped):
        raise SQLCompatibilityError("PRAGMA is SQLite-only; replace with explicit MySQL connection/session logic")
    if re.search(r"(?is)\bexecutescript\s*\(", syntax_only):
        raise SQLCompatibilityError("executescript requires a schema migration, not statement-level translation")
    # One source-specific REPLACE operation is fully understood: the basket grouping
    # code reassigns an inbox item to a group, and inbox_id is UNIQUE in both schemas.
    # MySQL's duplicate-key update preserves that intended reassignment without the
    # delete/reinsert side effects of SQLite REPLACE.
    replace_pattern = re.compile(
        r"(?is)^\s*INSERT\s+OR\s+REPLACE\s+INTO\s+`?scan_inbox_group_items`?\s*"
        r"\(\s*`?group_id`?\s*,\s*`?inbox_id`?\s*\)\s*"
        r"VALUES\s*\(\s*\?\s*,\s*\?\s*\)\s*;?\s*$"
    )
    if replace_pattern.match(sql):
        sql = replace_pattern.sub(
            "INSERT INTO scan_inbox_group_items(group_id,inbox_id) VALUES(?,?) "
            "ON DUPLICATE KEY UPDATE group_id=VALUES(group_id)", sql
        )
        syntax_only = _mask_literals_and_comments(sql)
    elif re.search(r"(?is)\bINSERT\s+OR\s+REPLACE\b", syntax_only):
        raise SQLCompatibilityError("INSERT OR REPLACE semantics differ; rewrite explicitly for MySQL")
    if re.search(r"(?is)\bAUTOINCREMENT\b", syntax_only):
        raise SQLCompatibilityError("AUTOINCREMENT is schema syntax and requires a reviewed MySQL DDL migration")
    def transform(s,i):
        if s[i]=="?":
            return "%s",1
        m=re.match(r"(?is)datetime\s*\(\s*'now'\s*\)",s[i:])
        if m: return "CURRENT_TIMESTAMP",len(m.group(0))
        m=re.match(r"(?is)INSERT\s+OR\s+IGNORE\b",s[i:])
        if m: return "INSERT IGNORE",len(m.group(0))
        return "",0
    return _rewrite_outside_literals(sql, transform)
