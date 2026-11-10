# eggcorn

**Find, measure and fix what your speech recognizer mishears.**

In 2003 Mark Liberman wrote on Language Log about a woman who spelled *acorn* as **"egg corn"**.
It was not a typo: she had heard the word, and *egg corn* made sense to her — an acorn is
egg-shaped, and it is a kind of seed. Geoffrey Pullum suggested naming the phenomenon after it:
an **eggcorn** is a mishearing that is replaced by something that sounds alike *and still makes sense*.

That is exactly the error that hurts domain ASR most. A model trained on general speech hears
your product name, your English loanwords inside Vietnamese (or Korean, or Hindi) sentences,
your team's jargon — and writes down a plausible eggcorn:

| said | heard |
|---|---|
| *up lên* ("upload it") | *hấp lên* ("steam it") |
| *ba bản ghi* ("three records") | *ba bản e* |
| *CRM, ERP* | *cip* |

Word error rate barely notices these (one token out of thirty), but they are the words a meeting
summary or a voice agent actually needs. `eggcorn` is a small toolkit for the loop that fixes them:

```
           ┌──────────── 1. flag ────────────┐
 audio ──► │ several ASR systems + an LLM     │ ──► sure ─────────► training set
           │ that FLAGS, never rewrites       │ ──► check ──► human review ─┐
           └──────────────────────────────────┘ ──► drop                    │
                                                                            ▼
           ┌──────────── 2. bench ───────────┐        ┌──────── 3. learn ────────┐
           │ term test set built from your    │ ◄───── │ confusion pairs mined     │
           │ own flags; term recall, not WER  │ ─────► │ from human corrections;   │
           └──────────────────────────────────┘ gate   │ kept only if bench agrees │
                                                       └───────────────────────────┘
                                                         ├─► context / hotword list for ASR
                                                         └─► post-correction rules
```

## Why another tool

Each piece exists in a paper; we did not find them joined into one usable loop, especially for
code-switched, lower-resource languages:

- **LLMs must flag, not rewrite.** Letting an LLM freely "clean up" pseudo-labels made our WER
  *worse*: it smooths away disfluencies and invents fluent text. `eggcorn flag` asks the LLM only
  *where* it suspects an error and *what* it would suggest — like an editor's **[sic]** — and
  accepts a suggestion only when an independent ASR system agrees.
- **WER hides eggcorns.** Two of our models differed by 2 WER points but by **8% vs 60%**
  on correctly hearing domain terms. `eggcorn bench` builds a term test set from your own data
  and reports term recall.
- **Corrections are data.** Every time a person fixes a transcript, the (heard → meant) pair is
  a free label. `eggcorn learn` mines these pairs and turns them into a context list for the
  recognizer and safe replacement rules — gated by the bench so a "fix" that hurts is dropped.

## Install

```bash
pip install -e .            # core: pure Python, no ML dependencies
export ANTHROPIC_API_KEY=…  # only for `flag --llm`
```

eggcorn does not run ASR itself. Bring transcripts from any systems (Whisper, Qwen3-ASR,
NeMo, sherpa-onnx, a cloud API) as JSONL.

## Usage

### 1. flag — triage pseudo-labels

Input: one segment per line with the hypotheses of two or more systems.

```jsonl
{"id": "m1_017", "audio": "clips/m1_017.wav", "hyps": {"whisper": "hôm nay em hấp lên file", "qwen": "hôm nay em up lên file"}, "conf": {"whisper": -0.31}}
```

```bash
eggcorn flag segments.jsonl -o flagged.jsonl --primary whisper [--llm --context "Glossary: CRM, ERP, upload…"]
```

Each segment gets `class` = `sure` | `check` | `drop`, the reasons, and — when the LLM and another
system agree — a suggested `label`. Use `sure` for training, send `check` to your review tool.

### 2. bench — term recall

```bash
eggcorn bench build flagged.jsonl -o termtest.jsonl      # segments whose flag names a term
eggcorn bench score termtest.jsonl hyps_modelA.jsonl hyps_modelB.jsonl
```

```
system    term_recall  still_wrong  WER(vs label)
modelA        24.0%        113          16.2
modelB        60.0%         14          22.8
```

### 3. learn — confusion memory

```bash
eggcorn learn pairs reviewed.jsonl -o confusions.jsonl   # (heard, meant) from human edits
eggcorn learn export confusions.jsonl --min-count 2 --context-out context.txt --rules-out rules.jsonl
```

`reviewed.jsonl` holds `{"hyp": …, "ref": …}` pairs. Rules are kept only when applying them does
not lower term recall or raise WER on a held-out bench (`--gate termtest.jsonl`).

## Status

Early. The workflow comes from adapting Vietnamese ASR to an internal domain (meetings and
phone calls mixing Vietnamese and English terms); this repository contains only the generic
tooling — no data, prompts or models from that work.

## License

Apache-2.0

## Roadmap

- `learn pairs --context 1`: keep one neighbouring word so `hấp → up` becomes `hấp lên → up lên`.
- Review UI export (Label Studio / plain HTML) for `check` segments, with the suggestion pre-filled.
- Adapters for common ASR outputs (faster-whisper segments, NeMo manifests, Qwen3-ASR).
- A small public demo on FLEURS + a synthetic code-switched glossary.
