"""Tests for scripts/duplicate_scan.py - tokenization, TF-IDF ranking."""

import json
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import duplicate_scan as ds  # noqa: E402


# --------------------------------------------------------------- tokenization


def test_tokenize_lowercases_and_drops_stopwords_and_short():
    got = ds.tokenize("The PDF Statement for Mobile is on par")
    assert "pdf" in got and "statement" in got and "mobile" in got
    assert "the" not in got and "for" not in got and "is" not in got
    assert "on" not in got  # len < 3


def test_tokenize_handles_non_latin_scripts_and_strips_urls_and_markup():
    got = ds.tokenize(
        "h3. Relev\u00e9 *PDF* du compte {code}x{code} https://design.example.com/file/abc "
        "\u0432\u044b\u043f\u0438\u0441\u043a\u0430"
    )
    assert "relev\u00e9" in got and "pdf" in got
    assert (
        "\u0432\u044b\u043f\u0438\u0441\u043a\u0430" in got
    )  # Cyrillic token survives
    assert not any("design" in t or "http" in t for t in got)


def test_doc_terms_weights_summary_over_description():
    counts = ds.doc_terms("statement parity", "statement details here")
    assert counts["statement"] == ds.SUMMARY_WEIGHT + 1
    assert counts["parity"] == ds.SUMMARY_WEIGHT
    assert counts["details"] == 1


# -------------------------------------------------------------------- ranking


CORPUS = {
    "PROJ-174": ds.doc_terms(
        "Mobile PDF statement parity with web version",
        "PDF statement download must match the web bank statement output",
    ),
    "PROJ-457": ds.doc_terms(
        "Savings account display types on home",
        "Show savings accounts with adapted quick actions",
    ),
    "PROJ-999": ds.doc_terms("Bottom navigation tab registry", "Data-driven tabs"),
}


def _rank(query_summary, query_desc="", **kw):
    _, vectorize = ds.build_index(CORPUS)
    return ds.rank(
        ds.doc_terms(query_summary, query_desc),
        CORPUS,
        vectorize,
        top=kw.get("top", 10),
        min_score=kw.get("min_score", 0.05),
        exclude=kw.get("exclude", ()),
    )


def test_duplicate_ranks_first_with_shared_terms():
    got = _rank("PDF statement in mobile app equals web statement")
    assert got[0]["key"] == "PROJ-174"
    assert "statement" in got[0]["shared_terms"]
    assert got[0]["score"] > 0.3


def test_unrelated_query_below_min_score():
    got = _rank("Push notification permissions dialog", min_score=0.12)
    assert got == []


def test_min_score_filters_and_top_caps():
    got = _rank("statement savings navigation", min_score=0.0, top=2)
    assert len(got) == 2


def test_exclude_drops_self_match():
    got = _rank("Mobile PDF statement parity with web version", exclude={"PROJ-174"})
    assert all(m["key"] != "PROJ-174" for m in got)


def test_empty_query_scores_nothing():
    got = _rank("the and for")  # all stopwords -> empty vector
    assert got == []


def test_build_index_unseen_term_does_not_crash():
    _, vectorize = ds.build_index(CORPUS)
    vec = vectorize(ds.doc_terms("completely unseen phrase", ""))
    assert vec  # normalized, non-empty


def test_cosine_symmetry():
    _, vectorize = ds.build_index(CORPUS)
    a = vectorize(CORPUS["PROJ-174"])
    b = vectorize(CORPUS["PROJ-457"])
    assert abs(ds.cosine(a, b) - ds.cosine(b, a)) < 1e-12


# ------------------------------------------------------------------- stage 2


def _corpus(n=25):
    return [
        {
            "key": f"PROJ-{i}",
            "fields": {
                "summary": "login screen bug on mobile",
                "status": {"name": "Backlog"},
                "issuetype": {"name": "Task"},
                "labels": [],
            },
        }
        for i in range(1, n + 1)
    ]


def _drive(monkeypatch, capsys, plugin, workers=8):
    monkeypatch.setattr(ds, "resolve_jira_api", lambda v: "jira_api.py")
    monkeypatch.setattr(ds, "search_all", lambda *a, **k: _corpus())
    monkeypatch.setattr(ds, "_run_plugin", plugin)
    # main() ends through fatal()/sys.exit in both directions
    try:
        code = ds.main(
            ["--text", "login screen bug on mobile", "--workers", str(workers)]
        )
    except SystemExit as exc:
        code = exc.code
    return code, capsys.readouterr()


def test_stage_two_is_deterministic_whatever_the_completion_order(monkeypatch, capsys):
    # rank() sorts on a rounded score and Python's sort is stable, so ties
    # settle by insertion order. Reassembling in completion order made the
    # top-N differ between identical runs - and /dup-check calls itself a
    # deterministic shortlist.
    import random
    import time

    def plugin(api, argv, timeout):
        time.sleep(random.uniform(0, 0.01))
        key = argv[1]
        return {
            "key": key,
            "fields": {
                "summary": "login screen bug on mobile",
                "description": "same words in every ticket",
            },
        }

    seen = set()
    for _ in range(5):
        code, out = _drive(monkeypatch, capsys, plugin)
        assert code == 0, out.err
        payload = json.loads(out.out)
        seen.add(tuple(m["key"] for m in payload["results"][0]["matches"]))
    assert len(seen) == 1, f"shortlist changed between identical runs: {seen}"


def test_a_dead_token_stops_the_fan_out_instead_of_firing_all_of_it(
    monkeypatch, capsys
):
    calls = []

    def plugin(api, argv, timeout):
        calls.append(argv[1])
        raise ds.AuthFailure("401 from Jira")

    # workers=1 makes this deterministic: with the break the run stops on the
    # first 401, without it every shortlist key is read against a dead token.
    code, out = _drive(monkeypatch, capsys, plugin, workers=1)
    assert code == 1 and "AUTH" in out.err
    assert len(calls) <= 2, f"issued {len(calls)} reads after the first 401"
