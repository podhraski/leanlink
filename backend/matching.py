import re
import unicodedata
import hashlib
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
from rapidfuzz import fuzz


#stopwords to ignore when comparing tokens
STOPWORDS = {"of", "the", "and", "for", "in", "at", "on", "de", "la", "le"}

#maps common country codes and abbreviations to a standard lowercase name
COUNTRY_MAP = {
    "ca": "canada", "can": "canada", "canada": "canada",
    "us": "united states", "usa": "united states", "united states": "united states",
    "uk": "united kingdom", "gb": "united kingdom", "great britain": "united kingdom",
    "united kingdom": "united kingdom",
    "au": "australia", "aus": "australia", "australia": "australia",
    "de": "germany", "deu": "germany", "germany": "germany",
    "fr": "france", "fra": "france", "france": "france",
    "jp": "japan", "jpn": "japan", "japan": "japan",
    "cn": "china", "chn": "china", "china": "china",
    "ch": "switzerland", "che": "switzerland", "switzerland": "switzerland",
    "sg": "singapore", "sgp": "singapore", "singapore": "singapore",
    "nl": "netherlands", "nld": "netherlands", "netherlands": "netherlands",
    "se": "sweden", "swe": "sweden", "sweden": "sweden",
    "dk": "denmark", "dnk": "denmark", "denmark": "denmark",
    "be": "belgium", "bel": "belgium", "belgium": "belgium",
    "fi": "finland", "fin": "finland", "finland": "finland",
    "ie": "ireland", "irl": "ireland", "ireland": "ireland",
    "it": "italy", "ita": "italy", "italy": "italy",
    "kr": "south korea", "kor": "south korea", "south korea": "south korea",
    "hk": "hong kong", "hkg": "hong kong", "hong kong": "hong kong",
    "nz": "new zealand", "nzl": "new zealand", "new zealand": "new zealand",
}


#parse a camelcase abbreviation into lowercase tokens
#e.g. 'UofT' -> ['u', 'of', 't'], 'ETHZurich' -> ['eth', 'zurich']
#returns none if the query has no lowercase (plain acronym handled elsewhere)
def parse_camel_pattern(query: str) -> Optional[List[str]]:
    if not query or ' ' in query or not any(c.isupper() for c in query) or not any(c.islower() for c in query):
        return None
    tokens = re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z][a-z]{4,}|[A-Z]|[a-z]+', query)  #single uppercase = abbreviation, capitalised word needs 4+ lowercase chars
    return [t.lower() for t in tokens] if len(tokens) >= 2 else None


#check if a name matches a parsed camelcase pattern
#stopword tokens must match exactly, other tokens just need to be a prefix
def matches_camel_pattern(pattern: List[str], name_clean: str) -> bool:
    name_tokens = name_clean.split()
    if len(pattern) != len(name_tokens):
        return False
    for p_tok, n_tok in zip(pattern, name_tokens):
        if p_tok in STOPWORDS:
            if p_tok != n_tok:
                return False
        else:
            if not n_tok.startswith(p_tok):
                return False
    return True


#lowercase, strip accents, expand common abbreviations, remove punctuation
def normalize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[-_/]", " ", s)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\buniv\b", "university", s)
    return s


#map country code or abbreviation to a standard name
def normalize_country(code: str) -> str:
    if code is None:
        return ""
    c = str(code).strip().lower()
    return COUNTRY_MAP.get(c, c)


#deterministic 12-char id from name + country using md5
def make_id(name: str, country: str) -> str:
    raw = f"{normalize_text(name)}|{normalize_country(country)}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class CandidateResult:
    id: str
    name: str
    score: float
    match: bool
    country: str = ""
    type: list = None

    def __post_init__(self):
        if self.type is None:
            self.type = [{"id": "University", "name": "University"}]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "score": self.score,
            "match": self.match,
            "type": self.type,
            "country": self.country,
        }


#small penalty applied to generic "university of x" names to boost more specific matches
GENERIC_PENALTY = 0.05


#score every institution in the pool against the query and return the top k results
def reconcile_candidates(
    query: str,
    df: pd.DataFrame,
    country: Optional[str] = None,
    top_k: int = 5,
) -> List[CandidateResult]:
    camel_pattern = parse_camel_pattern(query)
    q_clean = normalize_text(query)
    if not q_clean:
        return []
    q_original = q_clean

    #filter to country if one was provided and it actually matches rows
    pool = df
    if country:
        c_clean = normalize_country(country)
        if c_clean:
            country_mask = pool["country_clean"] == c_clean
            if country_mask.any():
                pool = pool[country_mask]

    results: List[CandidateResult] = []
    for _, row in pool.iterrows():
        if q_original == row["name_clean"]:
            raw_score = 100.0
        elif q_original == row.get("acronym", "") or q_clean == row.get("acronym", ""):
            raw_score = 95.0
        elif camel_pattern and matches_camel_pattern(camel_pattern, row["name_clean"]):
            raw_score = 85.0
        else:
            s1 = fuzz.token_sort_ratio(q_clean, row["name_clean"])
            s2 = fuzz.WRatio(q_clean, row["name_clean"])
            coverage = min(1.0, len(q_clean) / max(len(row["name_clean"]), 1))
            s3 = fuzz.partial_ratio(q_clean, row["name_clean"]) * coverage
            s4 = fuzz.token_set_ratio(q_clean, row["name_clean"])
            #scale s4 down when the query tokens are a strict subset of the result tokens
            #so partial queries like "toronto" dont tie with "university of toronto"
            q_sig = set(q_clean.split()) - STOPWORDS
            r_sig = set(row["name_clean"].split()) - STOPWORDS
            if q_sig and r_sig and q_sig < r_sig:
                s4 = s4 * len(q_sig) / len(r_sig)
            raw_score = max(s1, s2, s3, s4)
        score = round(raw_score / 100.0, 4)

        #penalise generic "university of x" names slightly unless its an exact match
        if raw_score < 100 and row["name_clean"].startswith("university of") and q_clean.startswith("university of"):
            score = max(0.0, score - GENERIC_PENALTY)

        is_match = score >= 0.90

        results.append(
            CandidateResult(
                id=str(row["id"]),
                name=str(row["name"]),
                score=round(score, 4),
                match=is_match,
                country=str(row.get("country", "")),
            )
        )

    results.sort(key=lambda x: x.score, reverse=True)
    return [r for r in results[:top_k] if r.score > 0]


#first try prefix matches, then fill remaining slots with fuzzy matches
def suggest_candidates(
    prefix: str,
    df: pd.DataFrame,
    limit: int = 1,
) -> List[dict]:
    p_clean = normalize_text(prefix)
    if not p_clean:
        return []

    starts = df[df["name_clean"].str.startswith(p_clean)]
    results = []
    for _, row in starts.head(limit).iterrows():
        results.append({"id": str(row["id"]), "name": str(row["name"]), "score": 1.0})

    if len(results) < limit:
        remaining = limit - len(results)
        seen_ids = {r["id"] for r in results}
        fuzzy_results = []
        for _, row in df.iterrows():
            if str(row["id"]) in seen_ids:
                continue
            s = fuzz.WRatio(p_clean, row["name_clean"]) / 100.0
            if s >= 0.5:
                fuzzy_results.append(
                    {"id": str(row["id"]), "name": str(row["name"]), "score": round(s, 4)}
                )
        fuzzy_results.sort(key=lambda x: x["score"], reverse=True)
        results.extend(fuzzy_results[:remaining])

    return results


#figure out which csv columns map to name, country, rank, year, score
def _detect_columns(df: pd.DataFrame) -> dict:
    mapping = {}
    cols_lower = {c.lower(): c for c in df.columns}

    for try_name in ["name", "institution", "university", "institution name"]:
        if try_name in cols_lower:
            mapping["name"] = cols_lower[try_name]
            break
    if "name" not in mapping:
        for c in df.columns:
            if "name" in c.lower() or "institution" in c.lower():
                mapping["name"] = c
                break

    for try_country in ["country", "country/territory", "location"]:
        if try_country in cols_lower:
            mapping["country"] = cols_lower[try_country]
            break
    if "country" not in mapping:
        for c in df.columns:
            if "country" in c.lower() or "territory" in c.lower():
                mapping["country"] = c
                break

    for try_rank in ["rank", "ranking", "overall rank"]:
        if try_rank in cols_lower:
            mapping["rank"] = cols_lower[try_rank]
            break
    if "rank" not in mapping:
        for c in df.columns:
            if "rank" in c.lower():
                mapping["rank"] = c
                break

    for try_year in ["year"]:
        if try_year in cols_lower:
            mapping["year"] = cols_lower[try_year]
            break

    for try_score in ["overall score", "score", "overall"]:
        if try_score in cols_lower:
            mapping["score_col"] = cols_lower[try_score]
            break

    return mapping


#load the csv and build the in-memory dataframe used for all matching
def load_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_map = _detect_columns(df)

    if "name" not in col_map:
        raise ValueError("Could not find institution name column in dataset")

    name_col = col_map["name"]
    country_col = col_map.get("country")
    rank_col = col_map.get("rank")
    year_col = col_map.get("year")
    score_col = col_map.get("score_col")

    #deduplicate: keep the most recent entry per institution
    if year_col and year_col in df.columns:
        df = (
            df.sort_values(year_col, ascending=False)
            .drop_duplicates(subset=[name_col] + ([country_col] if country_col else []))
            .reset_index(drop=True)
        )
    else:
        df = df.drop_duplicates(subset=[name_col]).reset_index(drop=True)

    df["name"] = df[name_col].astype(str).str.strip()
    df["country"] = df[country_col].astype(str).str.strip() if country_col else ""
    df["name_clean"] = df["name"].apply(normalize_text)
    df["country_clean"] = df["country"].apply(normalize_country)
    df["id"] = df.apply(lambda r: make_id(r["name"], r["country"]), axis=1)
    df["acronym"] = df["name_clean"].apply(
        lambda n: "".join(t[0] for t in n.split() if t not in STOPWORDS and t)  #first letter of each non-stopword token
    )

    if rank_col and rank_col in df.columns:
        df["rank"] = df[rank_col]
    else:
        df["rank"] = None

    if year_col and year_col in df.columns:
        df["year"] = df[year_col]
    else:
        df["year"] = None

    if score_col and score_col in df.columns:
        df["overall_score"] = df[score_col]
    else:
        df["overall_score"] = None

    keep_cols = ["id", "name", "country", "name_clean", "country_clean", "acronym", "rank", "year", "overall_score"]
    return df[[c for c in keep_cols if c in df.columns]]
