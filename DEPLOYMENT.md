# Deploy Structify: Vercel frontend + Render backend

The React frontend runs on Vercel. The OCR backend runs in Docker on Render,
with PostgreSQL (your existing Neon database works) and a persistent PDF disk.
The Render blueprint selects a paid Starter service because persistent storage
is required. Review the host's current pricing before creating it.

## 1. Deploy the backend

Push this repository to GitHub, then create a Render Blueprint from the repo.
Render reads `render.yaml`. Set the prompted environment variables:

- `DATABASE_URL`: PostgreSQL connection URL, including `sslmode=require` for Neon.
- `GEMINI_API_KEY`: your Gemini API key; keep it on the backend only.
- `CORS_ORIGINS`: exact frontend origin, e.g. `https://structify.vercel.app`,
  without a trailing slash. Multiple origins can be comma-separated.

The container installs Tesseract and Poppler. Do not copy Windows OCR paths into
Render environment variables. Startup creates missing tables; existing data is
preserved. This is initial schema creation, not a migration framework.
After deployment, visit `https://YOUR-API.onrender.com/health`; expect
`{"status":"ok"}`. The health check verifies database connectivity.

## 2. Deploy the frontend on Vercel

Import the same GitHub repository. Set:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Node.js | 24.x |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://YOUR-API.onrender.com` |

Use the backend origin without `/api` or a trailing slash. Set the variable for
Production and any Preview environments you intend to use. It is embedded at
build time, so redeploy after changing it. `vercel.json` supports refreshing
React Router routes. Update Render's `CORS_ORIGINS` with the final Vercel domain.
Use a stable preview domain if preview deployments need backend access.

## 3. Verify the deployed app

- Upload a digital PDF and a scanned PDF; wait for completed results.
- Open each original PDF and verify its JSON output.
- Upload two PDFs with the same filename and confirm both originals remain distinct.
- Refresh a document detail route and the History route directly.
- Restart the backend and confirm completed documents and originals persist.

## Operating limits

This is a single-user/demo application: all API users can view every document,
and uploads consume your Gemini quota. CORS is not authentication. Protect the
backend and frontend with an identity-aware access gateway before uploading
private documents or opening access to untrusted users. Vercel frontend-only
protection does not protect the separate backend. A public multi-user launch
requires backend authentication, per-user document ownership, and rate limits.

Run exactly one backend instance and one Uvicorn worker. Processing uses
in-process background tasks, not a durable queue; interrupted jobs are marked
failed on startup and must be uploaded again. Add a durable worker queue and
object storage before horizontal scaling. Back up both PostgreSQL and the PDF
disk; database backups alone do not contain the originals. Existing local PDFs
must be copied to the persistent upload directory if retaining historical data.

## Local development

Copy `backend/.env.example` to `backend/.env` and fill in your values. Install
`backend/requirements.txt`, then run `uvicorn main:app --reload` from `backend`.
Run `npm ci` and `npm run dev` from `frontend`. Vite proxies `/api` to port 8000,
so no frontend environment file is required locally.

## Validation commands

Frontend: `npm ci`, `npm run lint`, `npm run build` from `frontend`.
Backend: `python -B -m unittest discover -s tests -v` from `backend`.
The backend regression tests mock database access and Gemini processing; live
PostgreSQL, OCR, and Gemini still require the deployed smoke checks above.
The existing Google Generative AI SDK is deprecated; migrate to Google Gen AI
before relying on long-term SDK support.
