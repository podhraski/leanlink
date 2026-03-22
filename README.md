## Lean Link
http://3.146.241.103/

## Running with Docker locally

docker-compose up --build

Then, you can access these:
- Frontend: http://localhost
- API docs: http://localhost:8000/docs


## Running without docker

**Backend** — from `backend/`:
- python -m venv .venv
- .venv\Scripts\activate
- pip install -r requirements.txt
- uvicorn app:app --reload --port 8000

**Requires Postgre Instance**:
- Set `DATABASE_URL` in `backend/.env`:
- DATABASE_URL=postgresql+psycopg://{username}:{password}@localhost:5432/leanlink

**Frontend** — from project root:
- npm install
- npx vite --config vite.config.ts



## Tests

**Unit tests**:
- cd backend
- python test_unit.py

**Integration tests** (requires backend running on port 8000):
- cd backend
- python test_api.py
