#!/usr/bin/env python3
"""Validate GitHub issue forms and workflow/config YAML against the documented issue-form schema.

    tools/check-issue-forms.py PATH [PATH ...]     files or directories (searched for *.yml / *.yaml)

Checks: YAML parses; issue forms (anything under ISSUE_TEMPLATE except config.yml) have name, description, body;
each body element has a valid type with its required attributes; ids are unique and match [A-Za-z0-9_-];
dropdown options are non-empty strings; checkbox options have labels; config.yml has only known keys.
Needs PyYAML.
"""
import re
import sys
from pathlib import Path

import yaml

TYPES = {"markdown", "textarea", "input", "dropdown", "checkboxes"}
TOP_OPTIONAL = {"title", "labels", "assignees", "projects", "type"}
RENDER_OK = True


def check_form(path, doc, errs):
    for key in ("name", "description", "body"):
        if key not in doc:
            errs.append(f"{path}: missing top-level '{key}'")
    for key in doc:
        if key not in {"name", "description", "body"} | TOP_OPTIONAL:
            errs.append(f"{path}: unknown top-level key '{key}'")
    if not isinstance(doc.get("body"), list) or not doc.get("body"):
        errs.append(f"{path}: body must be a non-empty list")
        return
    ids, has_input = set(), False
    for i, el in enumerate(doc["body"]):
        where = f"{path}: body[{i}]"
        t = el.get("type")
        if t not in TYPES:
            errs.append(f"{where}: invalid type {t!r}")
            continue
        attrs = el.get("attributes") or {}
        if t == "markdown":
            if not attrs.get("value"):
                errs.append(f"{where}: markdown needs attributes.value")
            if "id" in el:
                errs.append(f"{where}: markdown cannot have an id")
            continue
        has_input = True
        if t != "checkboxes" and not attrs.get("label"):
            errs.append(f"{where}: needs attributes.label")
        if t == "checkboxes" and not attrs.get("label"):
            errs.append(f"{where}: checkboxes needs attributes.label")
        if "id" in el:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", str(el["id"])):
                errs.append(f"{where}: bad id {el['id']!r}")
            if el["id"] in ids:
                errs.append(f"{where}: duplicate id {el['id']!r}")
            ids.add(el["id"])
        if t == "dropdown":
            opts = attrs.get("options")
            if not isinstance(opts, list) or not opts or not all(isinstance(o, str) and o for o in opts):
                errs.append(f"{where}: dropdown options must be a non-empty list of strings")
            elif len(set(opts)) != len(opts):
                errs.append(f"{where}: duplicate dropdown options")
        if t == "checkboxes":
            opts = attrs.get("options")
            if not isinstance(opts, list) or not opts or not all(isinstance(o, dict) and o.get("label") for o in opts):
                errs.append(f"{where}: checkbox options need a label each")
        if t != "textarea" and "render" in attrs:
            errs.append(f"{where}: 'render' is only valid on textarea")
        if t == "textarea" and "render" in attrs and "placeholder" in attrs:
            errs.append(f"{where}: textarea with render cannot also have placeholder")
        for k in (el.get("validations") or {}):
            if k != "required":
                errs.append(f"{where}: unknown validations key {k!r}")
    if not has_input:
        errs.append(f"{path}: form needs at least one non-markdown element")


def check_config(path, doc, errs):
    for key in doc:
        if key not in {"blank_issues_enabled", "contact_links"}:
            errs.append(f"{path}: unknown key {key!r}")
    for i, link in enumerate(doc.get("contact_links") or []):
        for key in ("name", "url", "about"):
            if not link.get(key):
                errs.append(f"{path}: contact_links[{i}] missing {key}")


def main():
    errs, n = [], 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        files = [p] if p.is_file() else sorted(list(p.rglob("*.yml")) + list(p.rglob("*.yaml")))
        for f in files:
            if "node_modules" in f.parts:
                continue
            n += 1
            try:
                doc = yaml.safe_load(f.read_text())
            except yaml.YAMLError as e:
                errs.append(f"{f}: YAML error: {e}")
                continue
            if "ISSUE_TEMPLATE" in f.parts:
                (check_config if f.name == "config.yml" else check_form)(f, doc, errs)
    print("\n".join(errs) or f"ok: {n} file(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
