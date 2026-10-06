# Structify deployment

Architecture: React/Vite on Vercel, FastAPI/Docker on Render Free, Neon PostgreSQL,
Tesseract + Poppler OCR, and Gemini through `google-genai`. Uploaded PDFs are
processed in `/tmp` and deleted; extracted JSON, raw text and metadata persist in
Neon. Permanent PDF preview is intentionally unavailable.

Follow A–G in order. All URLs and credentials below are placeholders.

## A. Neon

1. Open [Neon Console](https://console.neon.tech/).
2. Select your existing project/database, or create a project on the Free plan.
   Keep the existing database if you want its document history.
3. Click **Connect**, select the correct branch, database and role, and copy the
   PostgreSQL connection string. Both pooled and direct Neon URLs are supported.
4. Ensure the URL contains `sslmode=require` (or `verify-ca`/`verify-full`). Keep
   additional Neon-provided parameters such as `channel_binding=require`.
5. Save this URL for Render's `DATABASE_URL` environment variable. Never put it in
   Vercel or commit it to GitHub. For local development, use `backend/.env`.

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
```

SQLAlchemy uses psycopg 3, checks pooled connections before reuse, and allows up
to five connections per worker (pool size 3 plus 2 overflow), with a 10-second
connection timeout. Missing/malformed database URLs fail clearly. Neon hosts use
TLS. Startup retains the existing create-table/additive-upgrade behavior; the
role must have permission to create/alter the `documents` table. Back up valuable
existing data before first deployment. No destructive schema migration is added.

## B. Gemini

Open [Google AI Studio](https://aistudio.google.com/apikey) and create/select a
Gemini API key. Set it as `GEMINI_API_KEY` in Render and, for local development,
`backend/.env`. Use a free-tier project/model without enabling paid billing.

The optional `GEMINI_MODEL` defaults to `gemini-2.5-flash`; use a model available
to your account. The supported `google-genai` SDK is used, with the existing
extraction prompt and JSON structure. Gemini failures mark the document failed
with a safe stage/type explanation. The API key never goes into Vite variables.

## C. GitHub

From the Structify repository root, review the changes and run:

```bash
git status
git add .
git commit -m "prepare Structify deployment"
git push
```

These commands are for you to execute; preparation does not automatically commit
or push. `.env`, `.env.*` variants and Python bytecode are ignored, while
`.env.example` templates remain tracked. Review `git status` before staging to
avoid including unrelated files. Existing local credentials/data are preserved.

## D. Render

1. Open Render and choose **New → Blueprint**.
2. Connect GitHub and select the Structify repository and intended branch.
3. Render reads `render.yaml` at the repository root.
4. Confirm the web service uses Docker and the **Free** plan.
5. Confirm there is **no persistent disk** and exactly **one instance**.
6. Set the environment variables below. Initially, `CORS_ORIGINS` can be
   `http://localhost:5173` or your expected Vercel origin.
7. Create/deploy the Blueprint and wait for the service to become healthy.
8. Copy the assigned backend URL, e.g. `https://BACKEND.onrender.com`.
9. Open `https://BACKEND.onrender.com/health`. Expect HTTP 200 with:

```json
{"status":"ok"}
```

| Render variable | Value |
| --- | --- |
| `DATABASE_URL` | Neon connection string with SSL |
| `GEMINI_API_KEY` | Backend Gemini API key |
| `CORS_ORIGINS` | Initially `http://localhost:5173`, later your Vercel origin |
| `GEMINI_MODEL` | Optional; Blueprint supplies `gemini-2.5-flash` |

Render supplies `PORT` automatically. No storage credentials or `UPLOAD_DIR`
are needed. Remove obsolete storage variables from an existing service. Do not
set local Windows `TESSERACT_PATH`/`POPPLER_PATH` values on Render.

The Dockerfile uses `backend` as its build context, installs Tesseract and Poppler,
runs as a non-root user, sets `TMPDIR=/tmp`, and starts:

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-graceful-shutdown 180
```

The health endpoint executes `SELECT 1`; database failure returns HTTP 503.
It never calls Gemini. If startup cannot initialize the database, check the URL,
SSL, connectivity and table permissions. No Render database needs to be created.

For manual service setup, use Dockerfile `backend/Dockerfile`, Docker build
context `backend`, health check `/health`, and leave the Docker command override
empty. The Blueprint already sets these values.

## E. Vercel

Import the same GitHub repository into Vercel. Use Hobby for an eligible personal
project and configure:

| Setting | Value |
| --- | --- |
| Root Directory | `frontend` |
| Framework | Vite |
| Node.js | 24.x |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

Set this single browser-safe environment variable for Production:

```env
VITE_API_BASE_URL=https://BACKEND.onrender.com
```

Use the Render origin with no `/api` suffix. Then deploy. The value is embedded
at build time, so redeploy after changing it. If enabling Preview deployments,
configure their API variable and explicitly allow their origin on the backend.

Never add `DATABASE_URL`, `GEMINI_API_KEY`, passwords or other backend secrets to
Vercel/Vite variables. `vercel.json` retains the SPA rewrite to `index.html`, so
React Router routes work when opened/refreshed directly.

## F. Final CORS update

After Vercel assigns `https://APP.vercel.app`, set this in Render:

```env
CORS_ORIGINS=https://APP.vercel.app
```

Use no trailing slash. Save and restart/redeploy the Render service to load the
new value. Multiple explicit origins can be comma-separated, for example:

```env
CORS_ORIGINS=https://APP.vercel.app,http://localhost:5173
```

Whitespace is trimmed. Wildcard `*` is rejected with credentials. CORS controls
browser access; it is not authentication.

## G. Smoke test

1. Open the deployed frontend.
2. Upload a digital PDF.
3. Confirm processing completes.
4. Inspect the extracted JSON/data and test copy/download.
5. Upload a scanned PDF.
6. Confirm OCR works and processing completes.
7. Upload two PDFs with the same filename.
8. Confirm both database records remain distinct (different document IDs).
9. Open `/history` directly and refresh it.
10. Open a `/documents/<id>` detail route directly and refresh it.
11. Restart/redeploy Render.
12. Confirm previously extracted results still exist in Neon.
13. Confirm the app does **not** expect original PDFs to remain available:
    detail pages show saved JSON only, and old `/pdf/<id>` links return **410 Gone**.

Permanent PDF preview is intentionally unavailable. The sample files under
`backend/test_files` can be used for digital/scanned tests.

## Local development and checks

From `backend`, create/activate a Python 3.12 virtual environment, install
`requirements.txt`, and copy `.env.example` to `.env` with your backend values.
For native local OCR only, optional `TESSERACT_PATH` and `POPPLER_PATH` can identify
binaries not on PATH. Start with `uvicorn main:app --reload --port 8000`.

From `frontend`, run `npm ci` and `npm run dev`. Vite's `/api` proxy targets
localhost port 8000; no frontend env file is required locally. If using an env
file, use your actual API origin rather than the example's deployment placeholder.

Run:

```bash
# From frontend
npm ci
npm run lint
npm run build
node --test tests/deployment.test.js

# From backend
python -B -m unittest discover -s tests -v

# From repository root, with Docker running
docker build -t structify-api:deployment-check ./backend
```

## Operating limits and compatibility

Uploads use unique temporary directories, including for duplicate filenames.
The background task owns its temporary original and cleans it in `finally` after
success, OCR/Gemini failure or database failure. Invalid requests clean up before
returning. OCR renders one bounded-size page at a time. Native local development
uses the OS temporary directory; Docker uses `/tmp`.

Run only one worker/instance. On restart, interrupted `processing` records become
failed and must be uploaded again. Forced termination cannot execute cleanup;
temporary files are disposable and never required after restart. An old nullable
`storage_key` column, if present, remains unused rather than being dropped.
Existing databases/JSON and local user files are not deleted by preparation.

Render Free may sleep. API requests allow up to 120 seconds for a slow wake-up;
network/timeout errors explain what to retry. Result polling waits two seconds
**after each response**, so requests never overlap; reset/navigation abort polling.
There are no automatic upload retries, which could create duplicate records. If
an upload response times out, check History before uploading the same file again.

The app has no user authentication or per-user document isolation. Use non-sensitive
demo documents until backend access control is implemented. Free-tier quotas,
Gemini model availability and Render resource limits apply. No paid storage or
billing configuration is required by the app. Render may independently request
card verification for some accounts; do not enable paid billing to follow this
no-card setup. Provider verification cannot be guaranteed by repository code.

References: [Render Free](https://render.com/docs/free),
[Render verification](https://community.render.com/t/the-deployement-of-a-web-service-fails/36005),
[Vercel Vite deployment](https://vercel.com/docs/frameworks/frontend/vite),
[Neon connections](https://github.com/neondatabase/website/blob/main/content/docs/get-started/connect-neon.md),
[Gemini billing](https://ai.google.dev/gemini-api/docs/billing/).

## Validation from repository preparation

- `npm ci`: passed; npm reported zero known vulnerabilities.
- `npm run lint`: passed.
- `npm run build`: passed.
- `node --test tests/deployment.test.js`: 5 tests passed.
- `python -B -m unittest discover -s tests -v`: 16 tests passed.
- Python syntax/imports, static Render/Vercel config checks, environment-ignore
  checks and `git diff --check`: passed.
- Secret scan: no suspicious matches in tracked working files or 133 historical
  source/configuration blobs. Local credentials were compared without printing
  or modifying them. Pattern scanning is not a guarantee that every secret is detectable.
- Runtime search found no active R2/S3/boto3/MongoDB/legacy Gemini integration or
  permanent upload path. Remaining mentions describe compatibility or regression tests.
- Docker build: attempted; Docker Desktop's Linux engine was not running, so no
  image was built or tested.

Backend tests mock external services and use SQLite for portable CRUD tests plus
PostgreSQL schema compilation. They emit a Starlette TestClient/httpx deprecation
warning. Real Neon permissions, Gemini processing, Linux OCR/container behavior
and deployed routing still need the smoke test above. No Git push, provider-account
change or live deployment was performed.
