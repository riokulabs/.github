#!/usr/bin/env python3
"""Render the shared GitHub structure from templates/ and copy it into a target repo.

    tools/sync-github-structure.py datacenter            # dry run: show the diff, write nothing
    tools/sync-github-structure.py datacenter --apply    # write the files
    tools/sync-github-structure.py --all [--apply]       # every repo in repos/ (not _defaults)
    tools/sync-github-structure.py --all --check         # exit 1 if any repo is out of date

How it works
  * templates/common/ is the base. templates/<kind>/ (kind = mod, tool, website, ...) replaces files with the same
    relative path. A file in the target is therefore either the common one or the kind one, never a mix.
  * repos/_defaults.toml, then repos/<name>.toml, give the variables. @@var@@ is replaced; @@var|filter@@ too
    (filters: raw, checklist, bullets, list, tomllist). A placeholder on a line of its own takes that line's indentation on
    every line it expands to. A missing variable is an error, not an empty string.
  * repos/<name>.toml may set  keep = [glob, ...]  (files the repo owns; never touched)  and
    exclude = [glob, ...]  (files this repo should not get at all).
  * Managed files start with a "managed by riokulabs/.github" comment where the format allows. A file that already
    exists in the target WITHOUT that comment is a conflict and is skipped, unless you pass --adopt.
  * Idempotent: a file is rewritten only when its rendered content differs.
  * Files that carry the marker but are no longer produced by the templates are listed as orphans. Nothing is deleted.
"""
import argparse
import difflib
import fnmatch
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "managed by riokulabs/.github"
HEADER_TEXT = MARKER + " - edit there (templates/), not here"
PLACEHOLDER = re.compile(r"@@\s*([A-Za-z0-9_]+)\s*(?:\|\s*([a-z]+))?\s*@@")
HASH_COMMENT = {".yml", ".yaml", ".toml", ".sh", ".py"}
HASH_NAMES = {"CODEOWNERS", ".editorconfig", ".gitattributes", "commit-msg", "pre-commit"}


def load_vars(name):
    defaults = tomllib.loads((ROOT / "repos" / "_defaults.toml").read_text())
    repo = tomllib.loads((ROOT / "repos" / f"{name}.toml").read_text())
    return {**defaults, **repo}


def collect(kind):
    files = {}
    for layer in ("common", kind):
        base = ROOT / "templates" / layer
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                files[p.relative_to(base).as_posix()] = p
    return files


def fmt(value, filt):
    items = value if isinstance(value, list) else None
    if items == [] and filt in ("checklist", "bullets", "list"):
        return ""
    if filt == "checklist":
        return "\n".join(f"- [ ] {i}" for i in (items or [value]))
    if filt == "bullets":
        return "\n".join(f"- {i}" for i in (items or [value]))
    if filt == "tomllist":
        return ", ".join(json.dumps(i) for i in (items or []))
    if filt == "list":  # YAML list items, for dropdown options
        return "\n".join(f"- {i}" for i in (items or [value]))
    if filt in (None, "raw"):
        if items is not None:
            raise ValueError("list variable needs a filter (checklist, bullets, list)")
        return str(value).rstrip("\n")
    raise ValueError(f"unknown filter {filt}")


def render(text, variables, relpath):
    out = []
    for line in text.split("\n"):
        m = PLACEHOLDER.fullmatch(line.strip()) if line.strip() else None
        if m:
            indent = line[: len(line) - len(line.lstrip())]
            val = lookup(variables, m.group(1), relpath)
            body = fmt(val, m.group(2))
            out.extend((indent + l) if l else l for l in body.split("\n"))
            continue
        out.append(PLACEHOLDER.sub(lambda mm: fmt(lookup(variables, mm.group(1), relpath), mm.group(2)), line))
    return "\n".join(out)


def lookup(variables, key, relpath):
    if key not in variables:
        raise KeyError(f"{relpath}: variable '{key}' is not defined for this repo")
    return variables[key]


def with_header(relpath, text):
    name = Path(relpath).name
    suffix = Path(relpath).suffix
    if suffix == ".md":
        comment = f"<!-- {HEADER_TEXT} -->"
    elif suffix in HASH_COMMENT or name in HASH_NAMES:
        comment = f"# {HEADER_TEXT}"
    else:
        return text
    lines = text.split("\n")
    at = 0
    if lines and lines[0].startswith("#!"):          # keep the shebang first
        at = 1
    elif suffix == ".md" and lines and lines[0] == "---":   # keep YAML front matter first (skills)
        at = lines.index("---", 1) + 1
    lines.insert(at, comment)
    return "\n".join(lines)


def has_marker(text):
    return MARKER in "\n".join(text.splitlines()[:12])


def matches(path, patterns):
    return any(fnmatch.fnmatch(path, p) or path == p.rstrip("/") for p in patterns)


def sync_one(name, apply, adopt):
    variables = load_vars(name)
    kind = variables["kind"]
    target = (ROOT / variables["target"]).resolve()
    keep, exclude = variables.get("keep", []), variables.get("exclude", [])
    if not (target / ".git").exists():
        print(f"{name}: target {target} is not a git repo, skipping", file=sys.stderr)
        return 0, 1
    print(f"== {name} ({kind}) -> {target}")
    pending = problems = 0
    produced = set()
    for rel, src in collect(kind).items():
        if matches(rel, exclude):
            continue
        produced.add(rel)
        if matches(rel, keep):
            print(f"  keep       {rel}")
            continue
        new = with_header(rel, render(src.read_text(), variables, f"{kind}/{rel}"))
        if not new.endswith("\n"):
            new += "\n"
        dest = target / rel
        if dest.exists():
            old = dest.read_text()
            if old == new:
                print(f"  unchanged  {rel}")
                continue
            if not has_marker(old) and not adopt:
                print(f"  CONFLICT   {rel} exists and is not managed; add it to keep or pass --adopt")
                problems += 1
                continue
            print(f"  update     {rel}")
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}"))
        else:
            print(f"  new        {rel} ({len(new.splitlines())} lines)")
        pending += 1
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new)
            if src.stat().st_mode & 0o111:
                dest.chmod(dest.stat().st_mode | 0o755)
    # orphans: managed files the templates no longer produce
    scan = [p for p in target.iterdir() if p.is_file()] + list((target / ".github").rglob("*"))
    for p in scan:
        if p.is_file() and p.stat().st_size < 200_000:
            rel = p.relative_to(target).as_posix()
            if rel not in produced and not matches(rel, keep):
                try:
                    if has_marker(p.read_text()):
                        print(f"  orphan     {rel} (managed marker, no template; remove by hand)")
                except UnicodeDecodeError:
                    pass
    return pending, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repos", nargs="*", help="names of repos/<name>.toml")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true", help="write files (default is a dry run)")
    ap.add_argument("--adopt", action="store_true", help="overwrite existing unmanaged files")
    ap.add_argument("--check", action="store_true", help="exit 1 if anything would change")
    a = ap.parse_args()
    names = a.repos
    if a.all:
        names = sorted(p.stem for p in (ROOT / "repos").glob("*.toml") if not p.stem.startswith("_"))
    if not names:
        ap.error("name a repo or use --all")
    total = bad = 0
    for n in names:
        p, b = sync_one(n, a.apply, a.adopt)
        total += p
        bad += b
    print(("applied" if a.apply else "dry run, nothing written") + f": {total} file(s) differ, {bad} problem(s)")
    if bad or (a.check and total):
        sys.exit(1)


if __name__ == "__main__":
    main()
