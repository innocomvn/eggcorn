"""eggcorn flag | bench build | bench score | learn pairs | learn export"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from . import bench, flag, learn


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cmd_flag(a):
    segs = read(a.input)
    reviewer = None
    if a.llm:
        from .llm import Anthropic, build_prompt
        reviewer = Anthropic(model=a.model)

    def one(s):
        hyps, conf = s["hyps"], s.get("conf")
        if flag.is_noise(hyps, a.primary, s.get("no_speech"), conf):
            return {**s, "primary": a.primary, "class": "drop", "reasons": ["noise"]}
        llm = None
        if reviewer:
            others = {k: v for k, v in hyps.items() if k != a.primary}
            try:
                llm = reviewer.ask(build_prompt(hyps[a.primary], others, a.context))
            except Exception as e:  # noqa: BLE001 - one bad call must not stop a batch of thousands
                print(f"{s['id']}: llm failed: {e}", file=sys.stderr)
        r = flag.triage(hyps, a.primary, conf, llm)
        return {**s, "primary": a.primary, "class": r.cls, "label": r.label, "reasons": r.reasons,
                "suggestion": r.suggestion}

    with ThreadPoolExecutor(a.workers) as ex:
        out = list(ex.map(one, segs))
    write(a.output, out)
    n = {c: sum(o["class"] == c for o in out) for c in ("sure", "check", "drop")}
    print(json.dumps(n))


def cmd_bench_build(a):
    items = bench.build(read(a.input))
    write(a.output, items)
    print(f"{len(items)} term items")


def cmd_bench_score(a):
    items = read(a.termtest)
    print(f"{'system':24s} {'term_recall':>11s} {'still_wrong':>11s} {'WER':>7s}")
    for p in a.hyps:
        s = bench.score(items, {r["id"]: r["hyp"] for r in read(p)})
        print(f"{os.path.basename(p):24s} {s['term_recall']:11.1%} {s['still_wrong']:11d} {s['wer']:7.1%}")


def cmd_learn_pairs(a):
    c = learn.mine(read(a.input))
    write(a.output, [{"heard": h, "meant": m, "count": n} for (h, m), n in c.most_common()])
    print(f"{len(c)} distinct pairs")


def cmd_learn_export(a):
    rows = read(a.input)
    c = learn.Counter({(r["heard"], r["meant"]): r["count"] for r in rows})
    if a.context_out:
        terms = learn.context_terms(c, a.min_count)[: a.max_terms]
        open(a.context_out, "w", encoding="utf-8").write(", ".join(terms) + "\n")
        print(f"{len(terms)} context terms -> {a.context_out}")
    if a.rules_out:
        rules = [r for r in rows if r["count"] >= a.min_count]
        if a.gate:
            items = read(a.gate)
            hyps = {r["id"]: r["hyp"] for r in read(a.gate_hyps)}
            before = len(rules)
            rules = learn.gate(rules, items, hyps)
            print(f"gate kept {len(rules)}/{before} rules")
        write(a.rules_out, rules)


def main(argv=None):
    p = argparse.ArgumentParser(prog="eggcorn")
    sub = p.add_subparsers(required=True)

    f = sub.add_parser("flag", help="triage segments into sure / check / drop")
    f.add_argument("input"); f.add_argument("-o", "--output", required=True)
    f.add_argument("--primary", required=True, help="key in `hyps` whose text becomes the label")
    f.add_argument("--llm", action="store_true", help="ask an LLM to flag suspect spans")
    f.add_argument("--model", default="claude-sonnet-5-5"); f.add_argument("--context", default="")
    f.add_argument("--workers", type=int, default=4)
    f.set_defaults(fn=cmd_flag)

    b = sub.add_parser("bench", help="term test set").add_subparsers(required=True)
    bb = b.add_parser("build"); bb.add_argument("input"); bb.add_argument("-o", "--output", required=True)
    bb.set_defaults(fn=cmd_bench_build)
    bs = b.add_parser("score"); bs.add_argument("termtest"); bs.add_argument("hyps", nargs="+", help='JSONL {"id","hyp"}')
    bs.set_defaults(fn=cmd_bench_score)

    l = sub.add_parser("learn", help="confusion memory").add_subparsers(required=True)
    lp = l.add_parser("pairs"); lp.add_argument("input", help='JSONL {"hyp","ref"}'); lp.add_argument("-o", "--output", required=True)
    lp.set_defaults(fn=cmd_learn_pairs)
    le = l.add_parser("export"); le.add_argument("input")
    le.add_argument("--min-count", type=int, default=2); le.add_argument("--max-terms", type=int, default=60)
    le.add_argument("--context-out"); le.add_argument("--rules-out")
    le.add_argument("--gate", help="termtest.jsonl to validate rules on"); le.add_argument("--gate-hyps")
    le.set_defaults(fn=cmd_learn_export)

    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
