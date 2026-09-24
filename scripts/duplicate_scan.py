#!/usr/bin/env python3
"""Shortlist likely duplicates / overlapping scope for a ticket or free text.

Deterministic engine for triage judgment (/dup-check, or a triage skill's
"is this a duplicate?" step). Scores a query - a Jira ticket's
summary+description or free text - against a corpus (default: EVERY issue of
the configured project, closed included: duplicates usually hide in
already-done scope) using plain TF-IDF cosine over Unicode word tokens.
Two-stage, because a JQL search never returns descriptions: a
summary-vs-summary shortlist over the whole corpus, then a re-rank of the
top 3 x --top candidates with their descriptions fetched per key. No
embeddings, no external deps - this produces a SHORTLIST with evidence
terms; deciding "duplicate / overlaps / distinct" stays with the judgment
layer.

READ-ONLY: never writes to Jira.

Usage:
    python scripts/duplicate_scan.py --query EXT-15021 [--query PROJ-457 ...]
        [--text "free text to check"] [--corpus-jql "project = PROJ"]
        [--top 10] [--min-score 0.12] [--out shortlist.json]
        [--timeout 30] [--workers 8] [--jira-api PATH]

Exit codes (house contract):
    0  clean
    2  partial - a query ticket failed to fetch; the rest still scored
    1  fatal   - stderr starting with "AUTH:" means VPN/token (STOP)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from board_consistency import _run_plugin, search_all  # noqa: E402
from jira_batch_fetch import AuthFailure, resolve_jira_api  # noqa: E402
from jira_config import CONFIG  # noqa: E402

SCHEMA = "duplicate-scan/1"
DEFAULT_CORPUS_JQL = f"project = {CONFIG['project_key']}"
DEFAULT_TOP = 10
DEFAULT_MIN_SCORE = 0.12
SUMMARY_WEIGHT = 3  # a summary term counts this many times vs a description term
DESC_CAP = 2000  # chars of description that participate in scoring

TOKEN_RE = re.compile(r"[^\W_]{3,}")  # letters/digits of any script, 3+ chars
URL_RE = re.compile(r"https?://\S+")
MARKUP_RE = re.compile(r"\{[^}]*\}|[*_#|]+|h[1-6]\.")  # jira wiki noise
STOPWORDS = frozenset(
    """
    the and for with that this from are was were been will would should can
    could not have has had you your our all any but they them then than when
    what where which who how why more most into onto over under after before
    add new user users issue ticket jira please
    """.split()
    + [w.lower() for w in CONFIG.get("extra_stopwords", [])]
)


def fatal(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------- pure scoring


def tokenize(text):
    text = URL_RE.sub(" ", text or "")
    text = MARKUP_RE.sub(" ", text)
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]


def doc_terms(summary, description):
    """Weighted bag of terms for one document."""
    counts = {}
    for t in tokenize(summary):
        counts[t] = counts.get(t, 0) + SUMMARY_WEIGHT
    for t in tokenize((description or "")[:DESC_CAP]):
        counts[t] = counts.get(t, 0) + 1
    return counts


def build_index(docs):
    """docs: {key: term-counts} -> (idf, normalized tf-idf vectors)."""
    n = max(len(docs), 1)
    df = {}
    for counts in docs.values():
        for term in counts:
            df[term] = df.get(term, 0) + 1
    idf = {t: math.log(n / d) + 1.0 for t, d in df.items()}

    def vectorize(counts):
        vec = {t: c * idf.get(t, math.log(n) + 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(w * w for w in vec.values()))
        return {t: w / norm for t, w in vec.items()} if norm else {}

    return idf, vectorize


def cosine(a, b):
    if len(b) < len(a):
        a, b = b, a
    return sum(w * b.get(t, 0.0) for t, w in a.items())


def rank(query_counts, corpus_docs, vectorize, top, min_score, exclude=()):
    qvec = vectorize(query_counts)
    scored = []
    for key, counts in corpus_docs.items():
        if key in exclude:
            continue
        cvec = vectorize(counts)
        score = cosine(qvec, cvec)
        if score >= min_score:
            shared = sorted(
                (t for t in qvec if t in cvec),
                key=lambda t: -(qvec[t] * cvec[t]),
            )
            scored.append(
                {"key": key, "score": round(score, 3), "shared_terms": shared[:8]}
            )
    scored.sort(key=lambda s: -s["score"])
    return scored[:top]


# --------------------------------------------------------------------- main


def issue_text(raw):
    fields = raw.get("fields") or {}
    return (
        fields.get("summary") or "",
        fields.get("description") or "",
        (fields.get("status") or {}).get("name", ""),
    )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--query", action="append", default=[], help="ticket key (repeatable)"
    )
    ap.add_argument("--text", help="free text query instead of / besides tickets")
    ap.add_argument("--corpus-jql", default=DEFAULT_CORPUS_JQL)
    ap.add_argument("--top", type=int, default=DEFAULT_TOP)
    ap.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    ap.add_argument("--out", help="write shortlist JSON here (default: stdout)")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument(
        "--workers",
        type=int,
        default=8,
        help="parallel jira_api reads for the stage-2 shortlist",
    )
    ap.add_argument(
        "--jira-api", help="explicit path to a jira_api.py (default: sibling)"
    )
    args = ap.parse_args(argv)

    if not args.query and not args.text:
        fatal("nothing to check (use --query and/or --text)")

    jira_api = resolve_jira_api(args.jira_api)
    errors = []
    try:
        # A JQL search returns summaries but NEVER descriptions, so the
        # scoring is two-stage: a summary-vs-summary shortlist over the whole
        # corpus, then a re-rank of the top candidates with their full
        # descriptions fetched per key (bounded at 3 x --top gets per query).
        corpus_raw = search_all(jira_api, args.corpus_jql, args.timeout)
        corpus_meta, corpus_docs = {}, {}
        for raw in corpus_raw:
            key = raw.get("key")
            summary, _, status = issue_text(raw)
            corpus_meta[key] = {"summary": summary, "status": status}
            corpus_docs[key] = doc_terms(summary, "")
        if not corpus_docs:
            print(
                f"WARNING: corpus JQL matched 0 issues ({args.corpus_jql!r}) - "
                "every query will report no duplicates",
                file=sys.stderr,
            )

        queries = []
        for qkey in args.query:
            try:
                raw = _run_plugin(jira_api, ["get", qkey], args.timeout)
                summary, description, _ = issue_text(raw)
                queries.append(
                    {
                        "query": qkey,
                        "summary": summary,
                        "summary_counts": doc_terms(summary, ""),
                        "counts": doc_terms(summary, description),
                    }
                )
            except AuthFailure:
                raise
            except Exception as exc:  # noqa: BLE001 - collected, reported, exit 2
                errors.append(f"get {qkey}: {exc}")
        if args.text:
            queries.append(
                {
                    "query": "text",
                    "summary": args.text[:120],
                    "summary_counts": doc_terms(args.text, ""),
                    "counts": doc_terms(args.text, ""),
                }
            )

        _, vectorize = build_index(corpus_docs)
        results = []
        for q in queries:
            shortlist = rank(
                q["summary_counts"],
                corpus_docs,
                vectorize,
                top=args.top * 3,
                min_score=0.0,
                exclude={q["query"]},
            )
            # Read the shortlist in PARALLEL. It used to issue up to --top * 3
            # sequential jira_api subprocesses per query - thirty at the default,
            # each with its own timeout.
            #
            # Two properties the sequential loop had for free, kept here on
            # purpose: results are reassembled in SHORTLIST order, because
            # rank() sorts on a rounded score and Python's stable sort then
            # settles ties by insertion order - completion order would make the
            # top-N differ between identical runs; and a dead token stops the
            # run instead of firing the whole fan-out at it.
            gathered, auth_error = {}, None
            pool = ThreadPoolExecutor(max_workers=max(1, args.workers))
            try:
                futures = {
                    pool.submit(
                        _run_plugin, jira_api, ["get", m["key"]], args.timeout
                    ): m["key"]
                    for m in shortlist
                }
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        gathered[key] = future.result()
                    except AuthFailure as exc:
                        auth_error = exc
                        break
                    except Exception as exc:  # noqa: BLE001 - summary-only
                        gathered[key] = exc
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
            if auth_error is not None:
                raise auth_error
            full_docs = {}
            for m in shortlist:
                key = m["key"]
                raw = gathered.get(key)
                if isinstance(raw, Exception) or raw is None:
                    errors.append(
                        f"get {key}: {raw if raw is not None else 'not read'}"
                    )
                    full_docs[key] = corpus_docs[key]
                    continue
                summary, description, _ = issue_text(raw)
                full_docs[key] = doc_terms(summary, description)
            _, vectorize_full = build_index({**corpus_docs, **full_docs})
            matches = rank(
                q["counts"],
                full_docs,
                vectorize_full,
                args.top,
                args.min_score,
                exclude={q["query"]},
            )
            for m in matches:
                m.update(corpus_meta.get(m["key"], {}))
            results.append(
                {"query": q["query"], "query_summary": q["summary"], "matches": matches}
            )
    except AuthFailure as exc:
        fatal(
            f"AUTH: Jira auth failed - check network/VPN and JIRA_API_TOKEN. Detail: {exc}"
        )
    except Exception as exc:  # noqa: BLE001 - clean fatal beats a raw traceback
        fatal(f"scan failed: {exc}")

    doc = {
        "schema": SCHEMA,
        "meta": {
            "corpus_jql": args.corpus_jql,
            "corpus_size": len(corpus_docs),
            "top": args.top,
            "min_score": args.min_score,
            "errors": errors,
        },
        "results": results,
    }
    text = json.dumps(doc, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(
            f"wrote {args.out} ({len(results)} query(ies) vs {len(corpus_docs)} "
            f"corpus issues, {len(errors)} errors)"
        )
    else:
        print(text)
    sys.exit(2 if errors else 0)


if __name__ == "__main__":
    main()
