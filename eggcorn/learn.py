"""Confusion memory: mine (heard -> meant) pairs from human corrections, export them as a context list
for the recognizer and as replacement rules, and keep a rule only if it does not hurt the bench."""
from collections import Counter

from .bench import score
from .text import align, contains, normalize, words


def pairs(hyp: str, ref: str, max_len: int = 4) -> list:
    """Contiguous error spans between hypothesis and corrected reference, as (heard, meant)."""
    out, h, r = [], [], []
    for op, rw, hw in align(words(ref), words(hyp)) + [("C", None, None)]:
        if op == "C":
            if (h or r) and len(h) <= max_len and len(r) <= max_len:
                out.append((" ".join(h), " ".join(r)))
            h, r = [], []
        else:
            if hw: h.append(hw)
            if rw: r.append(rw)
    return [p for p in out if p[0] and p[1]]


def mine(rows: list) -> Counter:
    c = Counter()
    for x in rows:
        c.update(pairs(x["hyp"], x["ref"]))
    return c


def apply_rules(text: str, rules: list) -> str:
    t = f" {normalize(text)} "
    for r in rules:
        t = t.replace(f" {r['heard']} ", f" {r['meant']} ")
    return " ".join(t.split())


def gate(rules: list, items: list, hyps: dict, max_wer_rise: float = 0.0) -> list:
    """Greedy: keep each rule only if term recall does not drop and WER does not rise on the bench."""
    kept = []
    base = score(items, hyps)
    for r in rules:
        trial = kept + [r]
        s = score(items, {k: apply_rules(v, trial) for k, v in hyps.items()})
        if s["term_recall"] >= base["term_recall"] and s["wer"] <= base["wer"] + max_wer_rise:
            kept, base = trial, s
    return kept


def context_terms(counter: Counter, min_count: int = 2) -> list:
    """Distinct `meant` phrases, most frequent first: feed to Whisper initial_prompt / Qwen3-ASR context / hotwords.
    Keep it short: long prompts make some decoders drop the first words of a segment."""
    agg = Counter()
    for (heard, meant), n in counter.items():
        if not contains(meant, heard):
            agg[meant] += n
    return [t for t, n in agg.most_common() if n >= min_count]
