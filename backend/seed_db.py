import os
import pandas as pd
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Institution
from matching import make_id, normalize_text


#find the best matching column name from a list of candidates, with substring fallback
def pick_col(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower(): c for c in cols}
    for want in candidates:
        if want.lower() in lower:
            return lower[want.lower()]
    for c in cols:
        cl = c.lower()
        for want in candidates:
            if want.lower() in cl:
                return c
    return None


#read the csv, deduplicate by name+country, then insert all rows into the database
def main():
    here = os.path.dirname(__file__)
    csv_path = os.path.join(here, "THE_World_University_Rankings_2016-2026.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"missing csv at {csv_path}")

    df = pd.read_csv(csv_path)
    cols = list(df.columns)

    name_col = pick_col(cols, ["university", "university name", "institution", "name"])
    country_col = pick_col(cols, ["country", "location", "nation"])
    rank_col = pick_col(cols, ["rank", "world rank", "overall rank", "rank overall"])
    year_col = pick_col(cols, ["year", "edition", "date"])

    if not name_col:
        raise RuntimeError(f"could not find a university name column in: {cols}")

    df["_name"] = df[name_col].astype(str).fillna("")
    df["_country"] = df[country_col].astype(str).fillna("") if country_col else ""
    df["_rank"] = pd.to_numeric(df[rank_col], errors="coerce") if rank_col else None
    df["_year"] = pd.to_numeric(df[year_col], errors="coerce") if year_col else None
    df["_name_norm"] = df["_name"].map(normalize_text)

    #keep most recent year per institution to avoid duplicates
    if year_col:
        df = df.sort_values("_year", ascending=False)
        df = df.drop_duplicates(subset=["_name_norm", "_country"], keep="first")
    else:
        df = df.drop_duplicates(subset=["_name_norm", "_country"], keep="first")

    db: Session = SessionLocal()
    try:
        #clear existing rows so ids stay in sync with matching.py
        db.query(Institution).delete()
        db.commit()

        rows = []
        for _, r in df.iterrows():
            name = str(r["_name"]).strip()
            if not name or name.lower() == "nan":
                continue

            country = None
            if country_col:
                c = str(r["_country"]).strip()
                country = c if c and c.lower() != "nan" else None

            inst = Institution(
                id=make_id(name, country),
                name=name,
                name_norm=r["_name_norm"],
                country=country,
                rank=int(r["_rank"]) if rank_col and pd.notna(r["_rank"]) else None,
                year=int(r["_year"]) if year_col and pd.notna(r["_year"]) else None,
                source="World_University_Rankings",
            )
            rows.append(inst)

        db.add_all(rows)
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    main()
