import requests
import sys

BASE = "http://127.0.0.1:8000"


#university of oxford should come back with a high score and match=true
def test_exact_match():
    r = requests.post(f"{BASE}/reconcile", json={
        "queries": {
            "q1": {
                "query": "University of Oxford",
                "limit": 5,
            }
        }
    })
    assert r.status_code == 200
    data = r.json()
    top = data["q1"]["result"][0]
    assert top["score"] >= 0.90, f"Expected high score, got {top['score']}"
    assert top["match"] is True, "Expected match=true for exact match"
    assert "Oxford" in top["name"]
    print(f"  exact match: {top['name']} score={top['score']} match={top['match']}")


#results with a canada filter should only contain canadian universities
def test_country_blocking():
    r_no_country = requests.post(f"{BASE}/reconcile", json={
        "queries": {"q1": {"query": "University of Toronto", "limit": 5}}
    })
    r_canada = requests.post(f"{BASE}/reconcile", json={
        "queries": {"q1": {"query": "University of Toronto", "limit": 5,
                           "properties": [{"p": "country", "v": "Canada"}]}}
    })
    assert r_no_country.status_code == 200
    assert r_canada.status_code == 200

    no_country_results = r_no_country.json()["q1"]["result"]
    canada_results = r_canada.json()["q1"]["result"]

    canada_countries = {r["country"] for r in canada_results}
    assert all(c == "Canada" for c in canada_countries), f"Expected all Canada, got {canada_countries}"
    print(f"  country blocking: without filter got {len(no_country_results)} results, with Canada filter got {len(canada_results)} Canadian results")


#send three queries at once and check all three keys come back
def test_multi_query():
    r = requests.post(f"{BASE}/reconcile", json={
        "queries": {
            "q1": {"query": "MIT", "limit": 3},
            "q2": {"query": "Stanford", "limit": 3},
            "q3": {"query": "Harvard University", "limit": 3},
        }
    })
    assert r.status_code == 200
    data = r.json()
    assert "q1" in data and "q2" in data and "q3" in data
    print(f"  multi-query: q1={data['q1']['result'][0]['name']}, q2={data['q2']['result'][0]['name']}, q3={data['q3']['result'][0]['name']}")


#prefix search should return at least one result
def test_suggest():
    r = requests.get(f"{BASE}/suggest", params={"prefix": "University of C"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["result"]) > 0
    print(f"  suggest: got {len(data['result'])} suggestions, first={data['result'][0]['name']}")


#look up oxford by id and check the preview returns the right data
def test_preview():
    r = requests.post(f"{BASE}/reconcile", json={
        "queries": {"q1": {"query": "University of Oxford", "limit": 1}}
    })
    oxford_id = r.json()["q1"]["result"][0]["id"]

    r2 = requests.get(f"{BASE}/preview", params={"id": oxford_id})
    assert r2.status_code == 200
    data = r2.json()
    assert data["name"] == "University of Oxford"
    assert "country" in data
    print(f"  preview: {data['name']}, country={data['country']}, rank={data.get('rank')}")


#unknown id should return a 404
def test_preview_404():
    r = requests.get(f"{BASE}/preview", params={"id": "nonexistent_id"})
    assert r.status_code == 404
    print(f"  preview 404: correctly returned 404 for unknown id")


#get /reconcile with no params should return the service manifest
def test_metadata():
    r = requests.get(f"{BASE}/reconcile")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Lean Link"
    assert "defaultTypes" in data
    print(f"  metadata: name={data['name']}, types={data['defaultTypes']}")


if __name__ == "__main__":
    tests = [
        ("Exact match yields high score", test_exact_match),
        ("Country blocking changes results", test_country_blocking),
        ("Multiple queries in one request", test_multi_query),
        ("Suggest endpoint works", test_suggest),
        ("Preview endpoint works", test_preview),
        ("Preview returns 404 for unknown id", test_preview_404),
        ("GET /reconcile returns metadata", test_metadata),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            print(f"[TEST] {name}")
            fn()
            print(f"  PASSED\n")
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}\n")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    sys.exit(1 if failed > 0 else 0)
