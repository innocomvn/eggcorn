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

#### Context helps — and has a trap

Optional per-segment fields: `group` (recording id: the LLM then sees the previous / next sentence,
`--neighbors 1`), `context` (glossary or topic for that recording, e.g. the customer's product names).
Short segments are often ambiguous on their own; one sentence on each side and a glossary make the
LLM's flags much sharper.

The trap: if the second ASR system was **given the same glossary** (Whisper `initial_prompt`,
Qwen3-ASR `context`, hotwords), its agreement with the LLM is no longer independent — both lean towards
the glossary. Declare such systems with `--biased qwen` (or `"biased": [...]` per segment):
their confirmations are tagged `confirmed_by_qwen_biased`, and `--strict-bias` sends them to review
instead of straight into training. `bench score --glossary` counts `false_terms` (glossary words
heard but not said) so you can see what biasing costs.

### 2. bench — term recall

```bash
eggcorn bench build flagged.jsonl -o termtest.jsonl      # segments whose flag names a term
eggcorn bench score termtest.jsonl hyps_modelA.jsonl hyps_modelB.jsonl
```

```
system    term_recall  still_wrong  false_terms  WER(vs label)
modelA        24.0%        113            -          16.2
modelB        60.0%         14            -          22.8
```

### 3. learn — confusion memory

```bash
eggcorn learn pairs reviewed.jsonl -o confusions.jsonl   # (heard, meant) from human edits
eggcorn learn export confusions.jsonl --min-count 2 --context-out context.txt --rules-out rules.jsonl
```

`reviewed.jsonl` holds `{"hyp": …, "ref": …}` pairs. Rules are kept only when applying them does
not lower term recall or raise WER on a held-out bench (`--gate termtest.jsonl`).

## Nghễnh Ngãng — an open lexicon of Vietnamese mishearings

*Nghễnh ngãng* is Vietnamese for "hard of hearing". `data/vi/nghenh-ngang.csv` (plus `data/vi/vietglish-office.csv`, office "Vietglish": *áp đết → update*, *bách láp → backlog*, *chê ra → Jira*) (and `data/en/eggcorns.csv` for English) collect pairs of
**what was heard → what was meant**: English loanwords spoken the Vietnamese way (*i meo → email*,
*bót → bot*), ASR eggcorns (*thích hợp → tích hợp*, *bỏ giá → báo giá*), regional sound mergers
(*s/x, tr/ch, l/n, r/d/gi, hỏi/ngã, -n/-ng, -c/-t*) and classic phrase errors (*vô hình chung → vô hình trung*).

```bash
eggcorn lexicon check            # validate (schema, duplicates, no personal data)
eggcorn lexicon hints > hints.txt   # "heard -> meant" lines to give the LLM in `flag --context`
```

Entries are **hints, not replacement rules**: *tết → test* is right in a software meeting and wrong
at New Year. Use them as LLM context, as candidates for `learn` (which gates every rule on the bench),
or to build term test sets.

An English lexicon lives in `data/en/eggcorns.csv`: classic eggcorns (*for all intensive purposes →
for all intents and purposes*, *escape goat → scapegoat*) and tech-meeting ASR errors (*Jason → JSON*,
*sequel → SQL*, *cooper netties → Kubernetes*, *cloud → Claude*). Use `--lang en` with `lexicon check / hints`.

**Contributions wanted — đóng góp nhé!** Anyone can add a pair through the
[issue form](../../issues/new?template=nghenh-ngang.yml) — no coding needed — or a pull request.
See [CONTRIBUTING.md](CONTRIBUTING.md) (tiếng Việt + English). The data is CC BY 4.0; other
languages are welcome under `data/<lang>/`.

Further reading (not copied; different licenses):
[The Eggcorn Database](https://eggcorns.lascribe.net/) (English) ·
[Từ dễ nhầm lẫn — Ngày ngày viết chữ](https://ngayngayvietchu.com/tu-de-nham-lan/) (Vietnamese).

## Privacy and safety

- **Nothing leaves your machine unless you pass `--llm`.** With `--llm`, each segment's transcripts
  (text only, never audio) are sent to the Anthropic API. Do not use it on data you are not allowed
  to share with a third party; plug in a local model through `llm.py` instead.
- The API key is read from `ANTHROPIC_API_KEY` and is never written to disk or logs.
- Transcripts are untrusted input to the LLM. A segment that contains instructions can at worst
  change its own flag: a suggested fix still needs an independent ASR system to agree before it
  becomes a training label, and everything else goes to human review.
- The core has no third-party dependencies and never executes or unpickles input files.

## Status

Early. The workflow comes from adapting Vietnamese ASR to an internal domain (meetings and
phone calls mixing Vietnamese and English terms); this repository contains only the generic
tooling — no data, prompts or models from that work.

## License

Code: Apache-2.0. Data in `data/`: CC BY 4.0 (`data/LICENSE`).

## Roadmap

- `learn pairs --context 1`: keep one neighbouring word so `hấp → up` becomes `hấp lên → up lên`.
- Review UI export (Label Studio / plain HTML) for `check` segments, with the suggestion pre-filled.
- Adapters for common ASR outputs (faster-whisper segments, NeMo manifests, Qwen3-ASR).
- A small public demo on FLEURS + a synthetic code-switched glossary.
