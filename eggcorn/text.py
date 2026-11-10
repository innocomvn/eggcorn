"""Text normalisation and word alignment shared by every eggcorn command."""
import unicodedata


def normalize(text: str) -> str:
    """NFC, lowercase, punctuation -> space, collapse whitespace. Keeps letters, marks and digits
    of any script, so Vietnamese tones and code-switched English survive."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text).lower()
    t = "".join(ch if unicodedata.category(ch)[0] in "LMN" else " " for ch in t)
    return " ".join(t.split())


def words(text: str) -> list:
    return normalize(text).split()


def align(ref: list, hyp: list) -> list:
    """Levenshtein alignment. Returns [(op, ref_word|None, hyp_word|None)], op in C/S/D/I."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]), d[i - 1][j] + 1, d[i][j - 1] + 1)
    ops, i, j = [], n, m
    while i or j:
        if i and j and d[i][j] == d[i - 1][j - 1] + (ref[i - 1] != hyp[j - 1]):
            ops.append(("C" if ref[i - 1] == hyp[j - 1] else "S", ref[i - 1], hyp[j - 1])); i -= 1; j -= 1
        elif i and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", ref[i - 1], None)); i -= 1
        else:
            ops.append(("I", None, hyp[j - 1])); j -= 1
    return ops[::-1]


def wer_counts(ref: str, hyp: str) -> tuple:
    """(errors, reference word count)."""
    r, h = words(ref), words(hyp)
    return sum(op != "C" for op, *_ in align(r, h)), len(r)


def distance(a: str, b: str) -> float:
    """Word error rate of b against a; 0 when both are empty."""
    e, n = wer_counts(a, b)
    return 0.0 if n == 0 and e == 0 else e / max(n, 1)


def contains(text: str, phrase: str) -> bool:
    """Whole-word containment after normalisation."""
    p = normalize(phrase)
    return bool(p) and f" {p} " in f" {normalize(text)} "
