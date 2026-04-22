# Team Balancer

Local-first scaffold for a futsal player evaluation and team balancing app.

## Planned stack

- Frontend: React + Vite
- Backend: FastAPI
- Local database: SQLite for development
- Production database: PostgreSQL

## Local development

### Frontend

```powershell
& 'C:\Program Files\nodejs\npm.cmd' install
& 'C:\Program Files\nodejs\npm.cmd' run dev
```

### Backend

```powershell
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

The backend seeds the reference data into `backend\data\team_balancer.db` on startup.

### Environment configuration

Frontend:

```powershell
copy .env.example .env
```

Backend:

```powershell
copy backend\.env.example backend\.env
```

Key variables:

- Frontend: `VITE_API_BASE_URL`
- Backend: `DATABASE_URL`
- Backend: `CORS_ORIGINS`
- Backend: `PORT`

## Current local workflow

- Open the frontend at `http://127.0.0.1:5173`
- Backend runs at `http://127.0.0.1:8000`
- Seeded admin credentials: `admin / admin123`
- The API currently supports:
  - `GET /api/reference-data`
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/me`
  - `GET /api/players`
  - `POST /api/players` (admin only)

## Deployment prep

The app is now prepared for deployment with environment-based config:

- frontend API URL is no longer hardcoded
- backend database URL is no longer hardcoded
- backend CORS origins are configurable
- backend includes a production Dockerfile
- PostgreSQL support is included for Cloud SQL

### Recommended production setup

- Frontend: Firebase Hosting
- Backend: Cloud Run
- Database: Cloud SQL for PostgreSQL

### Backend container

Build locally:

```powershell
docker build -f backend/Dockerfile -t team-balancer-api .
```

Run locally with env vars:

```powershell
docker run --rm -p 8000:8080 `
  -e PORT=8080 `
  -e DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME" `
  -e CORS_ORIGINS="https://YOUR-FRONTEND-DOMAIN" `
  team-balancer-api
```

### Frontend production build

Set:

```powershell
$env:VITE_API_BASE_URL="https://YOUR-BACKEND-DOMAIN"
npm run build
```

Then deploy `dist/` to Firebase Hosting or another static host.

## Next milestone

1. Store pairwise comparison answers
2. Build the smart question selection API
3. Recompute player and category ratings
4. Generate balanced teams with goalkeeper-first assignment
