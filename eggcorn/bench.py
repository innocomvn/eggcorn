"""Term test set built from your own flags, scored by term recall instead of WER alone.

A test item is a segment where a reviewer (or a confirmed LLM flag) says term `fix` was said
and the primary system wrote `wrong`. A system hears the term if `fix` appears in its output."""
from .text import contains, wer_counts


def build(flagged: list) -> list:
    """Items from flagged segments that carry a term suggestion; `label` (if any) becomes the reference."""
    out = []
    for s in flagged:
        sug = s.get("suggestion") or {}
        if not (sug.get("fix") and sug.get("wrong")):
            continue
        primary = s["hyps"][s["primary"]]
        ref = s.get("label") or primary.replace(sug["wrong"], sug["fix"], 1)
        out.append({"id": s["id"], "audio": s.get("audio"), "term": sug["fix"], "misheard": sug["wrong"], "ref": ref})
    return out


def score(items: list, hyps: dict) -> dict:
    """hyps: id -> text for one system."""
    hit = wrong = errs = n = scored = 0
    for it in items:
        h = hyps.get(it["id"])
        if h is None:
            continue
        scored += 1
        hit += contains(h, it["term"])
        wrong += contains(h, it["misheard"]) and not contains(it["term"], it["misheard"])
        e, k = wer_counts(it["ref"], h)
        errs += e; n += k
    return {"items": scored, "term_recall": hit / max(scored, 1), "still_wrong": wrong, "wer": errs / max(n, 1)}
