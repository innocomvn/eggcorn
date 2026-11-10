"""Triage pseudo-labelled segments into sure / check / drop.

Signals (all optional except two hypotheses):
- disagreement between ASR systems,
- low decoder confidence of the primary system,
- an LLM flag ([sic]-style: a suspect span and a suggested fix, never a rewrite).

An LLM fix is accepted as a label only when another ASR system independently heard it."""
from dataclasses import dataclass, field

from .text import contains, distance, words

LOW_CONF = -0.8      # mean token log-prob of the primary system
DISAGREE = 0.3       # word distance between primary and another system; one swapped word in a long
                     # sentence stays below it on purpose (systems differ on fillers) - the LLM catches those
LLM_MIN = 0.5        # LLM confidence needed to count a flag
CONFIRM = 0.25       # max distance between the fixed text and the confirming system
AGREE = 0.05         # systems this close count as agreeing


@dataclass
class Result:
    cls: str                         # sure | check | drop
    label: str = None                # training label when cls == "sure"
    reasons: list = field(default_factory=list)
    suggestion: dict = None          # {"wrong", "fix", "why"} for reviewers


def triage(hyps: dict, primary: str, conf: dict = None, llm: dict = None, biased=(), strict_bias=False) -> Result:
    """`biased`: systems that were given the same glossary the LLM saw. Their agreement with an LLM fix is
    correlated, not independent; it is marked, and with strict_bias it is not enough on its own."""
    p = hyps[primary]
    others = {k: v for k, v in hyps.items() if k != primary}
    reasons = []
    if conf and conf.get(primary) is not None and conf[primary] < LOW_CONF:
        reasons.append("low_conf")
    if len(words(p)) >= 3 and any(distance(p, o) >= DISAGREE for o in others.values()):
        reasons.append("disagree")
    sug = None
    if llm and llm.get("suspect") and (llm.get("confidence") or 0) >= LLM_MIN:
        reasons.append(f"llm_{llm.get('kind') or 'other'}")
        if llm.get("wrong") and llm.get("fix") and llm["wrong"] in p:
            sug = {k: llm.get(k) for k in ("wrong", "fix", "why")}

    if not reasons:
        # a weak LLM doubt with nothing to back it: not worth a reviewer's time, not safe to train on
        if llm and llm.get("suspect") and (llm.get("confidence") or 0) >= 0.3:
            return Result("drop", None, ["llm_weak"])
        return Result("sure", p)
    if sug:
        fixed = p.replace(sug["wrong"], sug["fix"], 1)
        confirm = [n for n, o in others.items() if contains(o, sug["fix"]) and distance(fixed, o) <= CONFIRM]
        free = [n for n in confirm if n not in biased]
        if free or (confirm and not strict_bias):
            tag = [f"confirmed_by_{n}" for n in free] + [f"confirmed_by_{n}_biased" for n in confirm if n in biased]
            return Result("sure", fixed, reasons + tag, sug)
    elif all(distance(p, o) <= AGREE for o in others.values()):
        return Result("sure", p, reasons + ["systems_agree"])
    return Result("check", None, reasons, sug)


def is_noise(hyps: dict, primary: str, no_speech: float = None, conf: dict = None) -> bool:
    """Segments that are probably not speech: drop before anything else."""
    lp = (conf or {}).get(primary)
    return bool(no_speech and no_speech > 0.6 and lp is not None and lp < -1.0) or not words(hyps[primary])
