"""The LLM is an editor that marks [sic]; it never rewrites. One call per segment, tool-shaped answer.
Only the Anthropic Messages API is wired in; add a provider by implementing `ask(prompt) -> dict`."""
import json
import os
import re
import urllib.request

SCHEMA = {
    "type": "object",
    "required": ["suspect", "confidence"],
    "properties": {
        "suspect": {"type": "boolean", "description": "true if the primary transcript likely contains a mishearing"},
        "kind": {"type": "string", "enum": ["term", "nonsense", "disagree", "other"]},
        "wrong": {"type": "string", "description": "exact substring of the primary transcript that is wrong"},
        "fix": {"type": "string", "description": "what was most likely said instead of `wrong`"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "why": {"type": "string"},
    },
}

PROMPT = """You review automatic speech recognition output. Do NOT rewrite or clean up the text:
fillers, repetitions and informal speech are correct and must stay.
Your only job is to point at a span that was probably MISHEARD (a word that sounds like what was
said but makes no sense here, e.g. a domain term or loanword turned into a common word).

{context}Primary transcript: {primary}
{others}
If nothing looks misheard, answer suspect=false. Otherwise give `wrong` as an exact substring of the
primary transcript and `fix` as the replacement. Answer by calling the tool `report`."""


def build_prompt(primary: str, others: dict, context: str = "") -> str:
    o = "".join(f"Other system ({k}): {v}\n" for k, v in others.items())
    return PROMPT.format(context=f"Context: {context}\n" if context else "", primary=primary, others=o)


class Anthropic:
    def __init__(self, model: str = "claude-sonnet-5-5", key: str = None):
        self.model = model
        self.key = key or os.environ["ANTHROPIC_API_KEY"]

    def ask(self, prompt: str) -> dict:
        body = {"model": self.model, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}],
                "tools": [{"name": "report", "description": "Report the review result", "input_schema": SCHEMA}],
                "tool_choice": {"type": "auto"}}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
                                     {"x-api-key": self.key, "anthropic-version": "2023-06-01",
                                      "content-type": "application/json"})
        content = json.load(urllib.request.urlopen(req, timeout=120))["content"]
        for b in content:
            if b.get("type") == "tool_use":
                return b["input"]
        text = "".join(b.get("text", "") for b in content)          # model answered in prose: salvage JSON
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0)) if m else {"suspect": False, "confidence": 0}
