"""Community lexicon of mishearings (data/<lang>/*.csv): loading, validation, and use as hints.

An entry is a pair someone actually heard (or an ASR system wrote) and what was meant. Entries are
hints, never blind replacement rules: `tết -> test` is right in a software meeting and wrong at New Year.
Use them as LLM context for `flag`, as candidates for `learn gate`, or to seed a term test set."""
import csv
import glob
import os
import re

from .text import normalize

FIELDS = ["heard", "meant", "kind", "cause", "region", "example", "source", "verified"]
KINDS = {"loanword", "asr", "spelling", "phrase", "meaning"}
REGIONS = {"vi": {"", "bac", "trung", "nam"}, "en": {"", "us", "uk", "au", "in"}}
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# personal data must never enter a public lexicon
PII = [(re.compile(r"\d[\d .-]{7,}\d"), "phone/ID-like number"), (re.compile(r"\S+@\S+\.\w+"), "email address"),
       (re.compile(r"https?://|www\."), "URL")]


def load(lang: str = "vi", root: str = DATA) -> list:
    rows = []
    for p in sorted(glob.glob(os.path.join(root, lang, "*.csv"))):
        with open(p, encoding="utf-8", newline="") as f:
            for i, r in enumerate(csv.DictReader(f), start=2):
                rows.append({**r, "_file": os.path.relpath(p, root), "_line": i})
    return rows


def validate(rows: list) -> list:
    """Problems as strings; empty list = valid."""
    errs, seen = [], {}
    for r in rows:
        at = f"{r['_file']}:{r['_line']}"
        missing = [k for k in FIELDS if k not in r]
        if missing:
            errs.append(f"{at}: missing columns {missing}"); continue
        h, m = r["heard"].strip(), r["meant"].strip()
        if not h or not m:
            errs.append(f"{at}: heard and meant are required")
        elif normalize(h) == normalize(m):
            errs.append(f"{at}: heard and meant are the same")
        if r["kind"] not in KINDS:
            errs.append(f"{at}: kind must be one of {sorted(KINDS)}")
        allowed = REGIONS.get(r["_file"].split(os.sep)[0], {""} | {x for v in REGIONS.values() for x in v})
        if r["region"] not in allowed:
            errs.append(f"{at}: region must be empty or one of {sorted(allowed - {''})}")
        if r["verified"] not in ("yes", "no"):
            errs.append(f"{at}: verified must be yes or no")
        for k in ("heard", "meant", "example"):
            if len(r[k]) > 200:
                errs.append(f"{at}: {k} longer than 200 characters")
            for rx, what in PII:
                if rx.search(r[k]):
                    errs.append(f"{at}: {k} looks like it contains a {what}")
        key = (normalize(h), normalize(m))
        if key in seen:
            errs.append(f"{at}: duplicate of {seen[key]}")
        seen.setdefault(key, at)
    return errs


def hints(rows: list, kinds=("loanword", "asr"), verified_only: bool = False) -> list:
    """`heard -> meant` lines for an LLM prompt (context), most specific kinds only."""
    return [f"{r['heard']} -> {r['meant']}" for r in rows
            if r["kind"] in kinds and (r["verified"] == "yes" or not verified_only)]
