from eggcorn import bench, flag, learn
from eggcorn.text import contains, distance, normalize


def test_normalize_keeps_vietnamese_and_english():
    assert normalize("Hôm nay, em UP lên CRM!") == "hôm nay em up lên crm"


def test_contains_is_whole_word():
    assert contains("em up lên file", "up lên")
    assert not contains("em upload file", "up")


def test_all_agree_is_sure():
    r = flag.triage({"a": "hôm nay trời đẹp", "b": "hôm nay trời đẹp"}, "a")
    assert r.cls == "sure" and r.label == "hôm nay trời đẹp"


def test_llm_fix_confirmed_by_second_system():
    hyps = {"whisper": "hôm nay em hấp lên file nhé", "qwen": "hôm nay em up lên file nhé"}
    llm = {"suspect": True, "kind": "term", "wrong": "hấp lên", "fix": "up lên", "confidence": 0.9}
    r = flag.triage(hyps, "whisper", llm=llm)
    assert r.cls == "sure" and r.label == "hôm nay em up lên file nhé"
    assert "confirmed_by_qwen" in r.reasons


def test_llm_fix_without_confirmation_goes_to_review():
    hyps = {"whisper": "hôm nay em hấp lên file nhé", "qwen": "hôm nay em hấp lên file nhé"}
    llm = {"suspect": True, "kind": "term", "wrong": "hấp lên", "fix": "up lên", "confidence": 0.9}
    r = flag.triage(hyps, "whisper", llm=llm)
    assert r.cls == "check" and r.suggestion["fix"] == "up lên"


def test_weak_llm_doubt_is_dropped():
    r = flag.triage({"a": "ừ thế nhé", "b": "ừ thế nhé"}, "a", llm={"suspect": True, "confidence": 0.4})
    assert r.cls == "drop"


def test_disagreement_goes_to_review():
    r = flag.triage({"a": "đồng bộ cip rồi", "b": "đồng bộ crm rồi ạ"}, "a")
    assert r.cls == "check" and "disagree" in r.reasons


def test_one_word_eggcorn_needs_the_llm():
    # a single swapped word in a long sentence stays under DISAGREE: catching it is the LLM's job
    r = flag.triage({"a": "bên em có ba bản e rồi", "b": "bên em có ba bản ghi rồi ạ"}, "a")
    assert r.cls == "sure"


def test_bench_term_recall():
    items = [{"id": "1", "term": "up lên", "misheard": "hấp lên", "ref": "em up lên file"},
             {"id": "2", "term": "crm", "misheard": "cip", "ref": "đồng bộ crm"}]
    s = bench.score(items, {"1": "em up lên file", "2": "đồng bộ cip"})
    assert s["term_recall"] == 0.5 and s["still_wrong"] == 1


def test_mine_pairs_and_gate():
    rows = [{"hyp": "em hấp lên file", "ref": "em up lên file"}] * 2 + [{"hyp": "đồng bộ cip", "ref": "đồng bộ crm"}]
    c = learn.mine(rows)
    assert c[("hấp", "up")] == 2 and c[("cip", "crm")] == 1
    rules = [{"heard": "hấp", "meant": "up"}, {"heard": "em", "meant": "anh"}]
    items = [{"id": "1", "term": "up lên", "misheard": "hấp lên", "ref": "em up lên file"}]
    kept = learn.gate(rules, items, {"1": "em hấp lên file"})
    assert kept == [rules[0]]            # the harmful rule raises WER and is dropped


def test_distance_empty():
    assert distance("", "") == 0.0


def test_biased_confirmation_is_marked_and_strict_sends_to_review():
    hyps = {"whisper": "đồng bộ cip nhé anh", "qwen": "đồng bộ crm nhé anh"}
    llm = {"suspect": True, "kind": "term", "wrong": "cip", "fix": "crm", "confidence": 0.9}
    r = flag.triage(hyps, "whisper", llm=llm, biased={"qwen"})
    assert r.cls == "sure" and "confirmed_by_qwen_biased" in r.reasons
    r = flag.triage(hyps, "whisper", llm=llm, biased={"qwen"}, strict_bias=True)
    assert r.cls == "check"


def test_false_terms_counts_over_biasing():
    items = [{"id": "1", "term": "crm", "misheard": "cip", "ref": "đồng bộ crm rồi"}]
    s = bench.score(items, {"1": "đồng bộ crm erp rồi"}, glossary=["crm", "erp"])
    assert s["false_terms"] == 1 and s["term_recall"] == 1.0


def test_prompt_shows_neighbours_read_only():
    from eggcorn.llm import build_prompt
    p = build_prompt("đồng bộ cip", {"qwen": "đồng bộ crm"}, "CRM, ERP", ["anh mở phần mềm"], ["xong rồi"])
    assert "(previous) anh mở phần mềm" in p and "(next) xong rồi" in p and "hint only" in p
