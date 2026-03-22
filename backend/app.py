import os
import json
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine, Base, SessionLocal
from matching import load_dataset, reconcile_candidates, suggest_candidates
from models import QueryLog
import seed_db

app = FastAPI(title="Lean Link Reconciliation API")

#create tables on startup if they dont exist yet
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.join(os.path.dirname(__file__), "THE_World_University_Rankings_2016-2026.csv")
DATASET = None
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")


#seed the database then load everything into memory for fast matching
@app.on_event("startup")
def startup():
    global DATASET
    seed_db.main()
    DATASET = load_dataset(CSV_PATH)
    print(f"Loaded {len(DATASET)} institutions from dataset")


#service manifest returned when get /reconcile is called with no query params
#openrefine reads this to know what the service supports
SERVICE_METADATA = {
    "name": "Lean Link",
    "identifierSpace": f"{API_BASE}/entities/",
    "schemaSpace": f"{API_BASE}/schema/",
    "view": {"url": "/preview?id={{id}}"},
    "preview": {
        "url": "/preview?id={{id}}",
        "width": 400,
        "height": 300,
    },
    "suggest": {
        "entity": {
            "service_url": "/suggest",
            "service_path": "",
            "flyout_service_url": "/preview",
        }
    },
    "defaultTypes": [{"id": "University", "name": "University"}],
    "properties": [
        {"id": "country", "name": "Country", "type": {"id": "string", "name": "String"}}
    ],
}


#if queries param exists run matching, otherwise return the manifest
@app.get("/reconcile")
def reconcile_get(queries: str = Query(None)):
    if queries:
        return _handle_queries(queries)
    return JSONResponse(content=SERVICE_METADATA)


#openrefine sends requests as form data, but also support plain json
@app.post("/reconcile")
async def reconcile_post(request: Request):
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        queries_str = form.get("queries")
        if queries_str:
            return _handle_queries(queries_str)
        return JSONResponse(status_code=400, content={"error": "Missing 'queries' in form data"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON payload"})

    if not body:
        return JSONResponse(status_code=400, content={"error": "Empty request body"})

    queries_data = body.get("queries")
    if queries_data is None:
        queries_data = body

    if not queries_data or not isinstance(queries_data, dict):
        return JSONResponse(status_code=400, content={"error": "Missing or invalid 'queries' object"})

    return _process_queries(queries_data)


#save the query and top result to the database
#wrapped in try/finally so a db error never crashes the api response
def _log_query(query_text: str, country, candidates: list):
    try:
        db = SessionLocal()
        top = candidates[0] if candidates else None
        db.add(QueryLog(
            query_text=query_text,
            country_filter=country,
            top_result_id=top.id if top else None,
            top_result_name=top.name if top else None,
            top_score=top.score if top else None,
            top_match=top.match if top else None,
            result_count=len(candidates),
        ))
        db.commit()
    except Exception:
        pass
    finally:
        db.close()


#decode the json string and pass it on to _process_queries
def _handle_queries(queries_str: str):
    try:
        queries_data = json.loads(queries_str)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON in queries parameter"})
    return _process_queries(queries_data)


#run matching for each query and return results keyed by query id
def _process_queries(queries_data: dict):
    results = {}
    for qid, qobj in queries_data.items():
        if isinstance(qobj, str):  #allow plain string as shorthand for {"query": "..."}
            qobj = {"query": qobj}

        query_text = qobj.get("query", "").strip()
        if not query_text:
            results[qid] = {"result": []}
            continue

        limit = int(qobj.get("limit", 5))

        country = None
        props = qobj.get("properties", [])
        if isinstance(props, list):
            for p in props:
                if isinstance(p, dict) and p.get("p", "").lower() == "country":  #pull country out of the w3c properties array
                    country = p.get("v")
                    break

        candidates = reconcile_candidates(query_text, DATASET, country=country, top_k=limit)
        _log_query(query_text, country, candidates)
        results[qid] = {"result": [c.to_dict() for c in candidates]}

    return JSONResponse(content=results)


#openrefine uses "prefix" for typeahead, some clients send "string" instead
@app.get("/suggest")
def suggest(
    prefix: str = Query(None),
    string: str = Query(None),
):
    search_term = prefix or string
    if not search_term or not search_term.strip():
        return JSONResponse(status_code=400, content={"error": "Missing 'prefix' or 'string' parameter"})

    results = suggest_candidates(search_term.strip(), DATASET, limit=10)
    return JSONResponse(content={"result": results})


#returns entity details shown in openrefines flyout panel
@app.get("/preview")
def preview(id: str = Query(None)):
    if not id or not id.strip():
        return JSONResponse(status_code=400, content={"error": "Missing 'id' parameter"})

    row = DATASET[DATASET["id"] == id.strip()]
    if row.empty:
        return JSONResponse(status_code=404, content={"error": f"Entity with id '{id}' not found"})

    r = row.iloc[0]
    result = {
        "id": str(r["id"]),
        "name": str(r["name"]),
        "country": str(r.get("country", "")),
        "source": "THE World University Rankings",
    }
    if "rank" in r and r["rank"] is not None:
        try:
            result["rank"] = int(float(r["rank"]))
        except (ValueError, TypeError):
            result["rank"] = str(r["rank"])
    if "year" in r and r["year"] is not None:
        try:
            result["year"] = int(float(r["year"]))
        except (ValueError, TypeError):
            result["year"] = str(r["year"])
    if "overall_score" in r and r["overall_score"] is not None:
        try:
            result["overall_score"] = float(r["overall_score"])
        except (ValueError, TypeError):
            pass

    return JSONResponse(content=result)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
