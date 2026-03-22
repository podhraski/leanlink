import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

from matching import (
    normalize_text,
    normalize_country,
    make_id,
    parse_camel_pattern,
    matches_camel_pattern,
    reconcile_candidates,
    suggest_candidates,
    STOPWORDS,
)


# ---------------------------------------------------------------------------
# setup df
# ---------------------------------------------------------------------------

def make_test_df():
    """Small labelled DataFrame for unit testing matching logic in isolation."""
    rows = [
        {"name": "University of Oxford",                   "country": "United Kingdom"},
        {"name": "Oxford Brookes University",               "country": "United Kingdom"},
        {"name": "University of Toronto",                   "country": "Canada"},
        {"name": "Toronto Metropolitan University",         "country": "Canada"},
        {"name": "Massachusetts Institute of Technology",   "country": "United States"},
        {"name": "Muroran Institute of Technology",         "country": "Japan"},
        {"name": "Université de Montréal",                  "country": "Canada"},
    ]
    df = pd.DataFrame(rows)
    df["name_clean"]    = df["name"].apply(normalize_text)
    df["country_clean"] = df["country"].apply(normalize_country)
    df["id"]            = df.apply(lambda r: make_id(r["name"], r["country"]), axis=1)
    df["acronym"]       = df["name_clean"].apply(
        lambda n: "".join(t[0] for t in n.split() if t not in STOPWORDS and t)
    )
    df["rank"]          = None
    df["year"]          = None
    df["overall_score"] = None
    return df


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

def test_normalize_text_lowercases():
    assert normalize_text("University of Toronto") == "university of toronto"

def test_normalize_text_expands_univ_abbreviation():
    assert normalize_text("Univ of Toronto") == "university of toronto"

def test_normalize_text_handles_none():
    assert normalize_text(None) == ""

def test_normalize_text_collapses_whitespace():
    assert normalize_text("  MIT  ") == "mit"

# ---------------------------------------------------------------------------
# normalize_country
# ---------------------------------------------------------------------------

def test_normalize_country_expands_ca():
    assert normalize_country("CA") == "canada"

def test_normalize_country_expands_usa():
    assert normalize_country("USA") == "united states"

# ---------------------------------------------------------------------------
# make_id
# ---------------------------------------------------------------------------

def test_make_id_is_deterministic():
    assert make_id("University of Toronto", "Canada") == make_id("University of Toronto", "Canada")

def test_make_id_is_12_chars():
    assert len(make_id("MIT", "United States")) == 12

def test_make_id_differs_by_country():
    assert make_id("University of Toronto", "Canada") != make_id("University of Toronto", "United Kingdom")


# ---------------------------------------------------------------------------
# parse_camel_pattern
# ---------------------------------------------------------------------------

def test_parse_camel_pattern_uoft():
    assert parse_camel_pattern("UofT") == ["u", "of", "t"]

def test_parse_camel_pattern_eth_zurich():
    result = parse_camel_pattern("ETHZurich")
    assert result is not None
    assert "eth" in result

def test_parse_camel_pattern_plain_acronym_returns_none():
    assert parse_camel_pattern("MIT") is None  # all uppercase, no lowercase

def test_parse_camel_pattern_plain_word_returns_none():
    assert parse_camel_pattern("oxford") is None  # no uppercase


# ---------------------------------------------------------------------------
# matches_camel_pattern
# ---------------------------------------------------------------------------

def test_matches_camel_uoft_matches_toronto():
    assert matches_camel_pattern(["u", "of", "t"], "university of toronto") is True

def test_matches_camel_stopword_must_match_exactly():
    # "of" in pattern is a stopword and must match exactly, not just be a prefix
    assert matches_camel_pattern(["u", "of", "t"], "university oxford toronto") is False


# ---------------------------------------------------------------------------
# reconcile_candidates
# ---------------------------------------------------------------------------

def test_exact_match_scores_1():
    df = make_test_df()
    results = reconcile_candidates("University of Oxford", df)
    assert results[0].score == 1.0
    assert results[0].match is True
    assert "Oxford" in results[0].name

def test_exact_match_is_auto_matched():
    df = make_test_df()
    results = reconcile_candidates("Massachusetts Institute of Technology", df)
    assert results[0].match is True
    assert results[0].score == 1.0

def test_acronym_mit_surfaces_mit():
    df = make_test_df()
    results = reconcile_candidates("MIT", df)
    names = [r.name for r in results]
    assert "Massachusetts Institute of Technology" in names

def test_acronym_mit_scores_high():
    df = make_test_df()
    results = reconcile_candidates("MIT", df)
    mit = next(r for r in results if r.name == "Massachusetts Institute of Technology")
    assert mit.score >= 0.90

def test_accent_insensitive_match():
    df = make_test_df()
    results = reconcile_candidates("Universite de Montreal", df)
    names = [r.name for r in results]
    assert "Université de Montréal" in names

def test_country_filter_restricts_pool():
    df = make_test_df()
    results = reconcile_candidates("University of Toronto", df, country="Canada")
    assert all(r.country == "Canada" for r in results)

def test_ambiguous_short_query_not_scored_perfect():
    df = make_test_df()
    results = reconcile_candidates("Oxford", df)
    assert results[0].score < 1.0

def test_ambiguous_short_query_surfaces_multiple_candidates():
    df = make_test_df()
    results = reconcile_candidates("Oxford", df, top_k=5)
    names = [r.name for r in results]
    assert "University of Oxford" in names
    assert "Oxford Brookes University" in names

def test_results_sorted_descending():
    df = make_test_df()
    results = reconcile_candidates("Oxford", df)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)

def test_empty_query_returns_empty():
    df = make_test_df()
    assert reconcile_candidates("", df) == []


# ---------------------------------------------------------------------------
# suggest_candidates
# ---------------------------------------------------------------------------

def test_suggest_prefix_match():
    df = make_test_df()
    results = suggest_candidates("university of ox", df, limit=5)
    names = [r["name"] for r in results]
    assert "University of Oxford" in names

def test_suggest_respects_limit():
    df = make_test_df()
    results = suggest_candidates("university", df, limit=2)
    assert len(results) <= 2

def test_suggest_empty_prefix_returns_empty():
    df = make_test_df()
    assert suggest_candidates("", df) == []


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        # normalize_text
        ("normalize_text: lowercases input",                    test_normalize_text_lowercases),
        ("normalize_text: expands 'univ' abbreviation",         test_normalize_text_expands_univ_abbreviation),
        ("normalize_text: handles None input",                  test_normalize_text_handles_none),
        ("normalize_text: collapses whitespace",                test_normalize_text_collapses_whitespace),
        # normalize_country
        ("normalize_country: expands 'CA' to 'canada'",         test_normalize_country_expands_ca),
        ("normalize_country: expands 'USA'",                    test_normalize_country_expands_usa),
        # make_id
        ("make_id: deterministic for same inputs",              test_make_id_is_deterministic),
        ("make_id: produces 12-char output",                    test_make_id_is_12_chars),
        ("make_id: differs by country",                         test_make_id_differs_by_country),
        # parse_camel_pattern
        ("parse_camel_pattern: UofT -> [u, of, t]",             test_parse_camel_pattern_uoft),
        ("parse_camel_pattern: ETHZurich contains 'eth'",       test_parse_camel_pattern_eth_zurich),
        ("parse_camel_pattern: all-caps returns None",          test_parse_camel_pattern_plain_acronym_returns_none),
        ("parse_camel_pattern: all-lower returns None",         test_parse_camel_pattern_plain_word_returns_none),
        # matches_camel_pattern
        ("matches_camel_pattern: UofT matches Toronto",         test_matches_camel_uoft_matches_toronto),
        ("matches_camel_pattern: stopword must match exactly",  test_matches_camel_stopword_must_match_exactly),
        # reconcile_candidates
        ("reconcile: exact match scores 1.0",                   test_exact_match_scores_1),
        ("reconcile: exact match is auto-matched",              test_exact_match_is_auto_matched),
        ("reconcile: MIT acronym surfaces MIT",                 test_acronym_mit_surfaces_mit),
        ("reconcile: MIT acronym scores >= 0.90",               test_acronym_mit_scores_high),
        ("reconcile: accent-insensitive match",                 test_accent_insensitive_match),
        ("reconcile: country filter restricts pool",            test_country_filter_restricts_pool),
        ("reconcile: short query not scored 1.0",               test_ambiguous_short_query_not_scored_perfect),
        ("reconcile: short query surfaces multiple candidates", test_ambiguous_short_query_surfaces_multiple_candidates),
        ("reconcile: results sorted descending",                test_results_sorted_descending),
        ("reconcile: empty query returns []",                   test_empty_query_returns_empty),
        # suggest_candidates
        ("suggest: prefix match surfaces correct result",       test_suggest_prefix_match),
        ("suggest: respects limit",                             test_suggest_respects_limit),
        ("suggest: empty prefix returns []",                    test_suggest_empty_prefix_returns_empty),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    sys.exit(1 if failed > 0 else 0)
