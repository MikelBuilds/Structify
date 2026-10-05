# Free-tier deployment: Vercel + Render + Neon + Cloudflare R2

## Architecture and repository findings

| Component | Before | Now |
| --- | --- | --- |
| Frontend | React/Vite in `frontend`, prepared for Vercel | Same UI and routes; Vercel Hobby where eligible |
| Backend | FastAPI in `backend`, Render Starter + disk | Render Free, Docker, one instance and one Uvicorn worker |
| Database | SQLAlchemy/PostgreSQL with JSONB | Neon PostgreSQL, SQLAlchemy 2.x and psycopg 3 |
| Originals | Local `uploads/originals`, requiring durable disk | Private Cloudflare R2 bucket |
| OCR | pdfplumber; Poppler/Tesseract fallback | Same distinction, temporary files, one page/job at a time |
| AI | Deprecated `google-generativeai` | Supported `google-genai`, same prompt and JSON output |

No MongoDB models, queries, packages, data exports, or migration scripts were found
in this repository. No MongoDB data was touched and no speculative Mongo importer
was added. Alembic was an unused requirements entry, with no configuration or
revision directory; the demo keeps simple additive startup schema initialization.
Existing local PDFs are supported by the optional migration below.

The original integer `documents.id` is retained to preserve existing links and
rows. UUIDs identify R2 objects, not database records. The existing columns
`filename`, `pdf_type`, `processing_method`, `status`, `raw_text`,
`structured_json` (JSONB), and `created_at` (TIMESTAMPTZ) remain.
Startup adds `storage_key` (TEXT), `error_message` (TEXT), and `updated_at`
(TIMESTAMPTZ). It backfills update timestamps from creation times. Existing rows
and extracted JSON are preserved. `filename` already stores the original name,
so a duplicate `original_filename` column is unnecessary. API results still use
`structured_data` for compatibility with the React app.

Routes remain `POST /upload`, `GET /results/{id}`, `GET /documents`,
`GET /pdf/{id}`, and `GET /health`. Search/filtering remains client-side.
There was no document deletion feature, so none was added.

Uploads are validated and copied to a temporary directory, stored in R2 with a
UUID key, and recorded in PostgreSQL. The request's temporary copy is removed.
A background task downloads its own temporary copy, extracts text, invokes
Gemini, saves results, and cleans up. Docker uses `/tmp`; native local runs use
the OS temporary directory. R2 originals survive processing failures and restarts.
The PDF route issues a non-cacheable redirect to a five-minute signed R2 URL
with `application/pdf` and an inline filename; the existing iframe follows it.
Refresh the app's PDF endpoint to obtain a new URL after expiration. The bucket
stays private and requires no browser credentials or public access.

## Free-tier limits

No paid Render service or persistent disk is configured. Select free plans for
Neon and Vercel, and use R2 **Standard** storage within its free allowance.
This is a free-tier architecture, not a guarantee of zero charges under unlimited
usage: R2 currently includes 10 GB-months, 1 million Class A and 10 million Class B
operations monthly; excess usage is billed. Enabling R2 may require billing setup.
Check [R2 pricing](https://developers.cloudflare.com/r2/pricing/) before activation.
Use a Gemini free-tier project/model where available; paid Gemini projects can
charge for API calls. Check [Gemini billing](https://ai.google.dev/gemini-api/docs/billing/).
Do not enable paid upgrades to follow this guide.

[Render Free](https://render.com/docs/free) instances sleep after 15 minutes without
inbound traffic. The first request after inactivity can be slow. The frontend now
allows 120 seconds per API request; this does not guarantee a cold start finishes
within that time. All Render local files are disposable, which is why R2 is required.
Free services have resource and usage limits; large PDFs may still exceed the small
instance's resources. OCR renders a single page at a time with bounded dimensions
and timeouts to reduce memory pressure.

## 1. Neon setup

1. Sign in to the Neon Console. Open the existing project/database used by
   Structify; retain it if its history is needed. If starting fresh, create a
   Free project, database and role in a region close to the Render service.
2. Click **Connect**, select the correct branch, database and role, and copy
   its PostgreSQL connection string. A pooled URL is supported.
3. Keep `sslmode=require` (or stronger verification) and any Neon-supplied
   `channel_binding` parameter. The app converts `postgresql://` to
   SQLAlchemy's `postgresql+psycopg://` internally and requires TLS on Neon hosts.
4. Set this exact value as backend `DATABASE_URL`. Do not put it in Vercel.
5. The role must own or be allowed to create/alter the `documents` table.
   Startup creates a missing table or adds the three columns above to an existing
   table. Take a database backup/branch before applying to valuable existing data.
6. Deploy the backend and check `/health` returns `{"status":"ok"}`. Missing,
   malformed, unreachable or unauthorized database configuration prevents startup
   with a clear message. No manual SQL schema creation is needed.

Example (placeholder only):

```env
DATABASE_URL=postgresql://USER:PASSWORD@ep-example-pooler.REGION.aws.neon.tech/neondb?sslmode=require
```

Use the console-generated URL to avoid password encoding mistakes.
[Neon connection documentation](https://github.com/neondatabase/website/blob/main/content/docs/get-started/connect-neon.md).

## 2. Cloudflare R2 setup

1. Sign in to Cloudflare, open **R2 Object Storage**, and enable R2 if necessary.
   Review the billing terms; the Standard free allowance is usage-limited.
2. Create a bucket, for example `structify-pdfs`, using **Standard** storage.
3. Keep public access disabled: do not enable an `r2.dev` public URL or attach a
   public custom domain. This implementation uses the S3 API endpoint.
4. In R2 API token management, create a token with **Object Read & Write**, scoped
   only to this bucket. Save its **Access Key ID** and **Secret Access Key**;
   a generic Cloudflare API token is not the S3 secret.
5. Copy the Account ID and the bucket's S3 API endpoint, normally
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.
6. Put the five R2 variables below in Render and your local backend `.env`.
   No R2 CORS rule is needed for iframe/navigation to signed URLs; the frontend
   does not fetch R2 via JavaScript. No R2 secret goes to Vercel.

[Cloudflare token instructions](https://developers.cloudflare.com/r2/api/tokens/)
and [signed URL behavior](https://developers.cloudflare.com/r2/api/s3/presigned-urls/).

## 3. Render deployment

1. Commit and push the repository changes to your Git provider. No push or cloud
   provisioning is performed by the code changes themselves.
2. In Render choose **New > Blueprint**, connect the repository, and use
   `render.yaml` at its root. It defines a Docker web service with `plan: free`,
   one instance, no disks, and `/health` health checks. Do not create a Render database.
3. Fill in the prompted variables from the table below. For CORS use the intended
   Vercel production origin; update it once Vercel assigns the final domain.
4. Review that the service is **Free**, then create/deploy it. For an existing
   Starter service, explicitly switch its instance type to Free and remove its
   disk only **after** migrating any originals from that disk to R2. Removing a disk
   can delete data; this repository change does not remove a live disk for you.
5. Record `https://<service-name>.onrender.com`. Visit `/health` and `/docs`.
6. If setting up a service manually: repository root stays the root, Dockerfile
   path is `backend/Dockerfile`, Docker build context is `backend`, instance type
   is Free, health check is `/health`, and no Docker command override is needed.

Docker installs Tesseract and Poppler on Linux PATH, runs as a non-root user,
and starts `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1`.
Render supplies `PORT`; do not configure Windows OCR paths or `UPLOAD_DIR`.

## Environment variables

### Render / local backend only

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Neon PostgreSQL URL with SSL |
| `GEMINI_API_KEY` | Gemini API key |
| `CORS_ORIGINS` | Exact Vercel origin; comma-separated additional origins |
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Bucket-scoped R2 S3 access key ID |
| `R2_SECRET_ACCESS_KEY` | R2 S3 secret access key |
| `R2_BUCKET_NAME` | Private bucket name |
| `R2_ENDPOINT` | S3 API HTTPS origin, no bucket suffix; inferred from account ID if blank |
| `GEMINI_MODEL` | Optional; defaults to existing `gemini-2.5-flash` |

For local native OCR only, optional `TESSERACT_PATH` points to the executable and
`POPPLER_PATH` to the binaries directory. Leave both unset in Docker. Docker sets
standard `TMPDIR=/tmp` internally. Local `.env` is loaded from `backend/.env`.
Only placeholders are in `backend/.env.example`.

### Vercel / frontend

```env
VITE_API_BASE_URL=https://<render-backend>.onrender.com
```

This is the only app environment variable needed by the browser. Do not add
`/api` to the production origin. Never prefix backend secrets with `VITE_`.

## 4. Vercel deployment

1. Import the same repository into a Vercel project on the free Hobby plan where
   its usage terms apply.
2. Choose **Root Directory: `frontend`**, **Framework: Vite**, **Node.js: 24.x**,
   **Install Command: `npm ci`**, **Build Command: `npm run build`**, and
   **Output Directory: `dist`**.
3. Set `VITE_API_BASE_URL` to the Render origin above for Production. Set it for
   Preview as well only if preview builds need backend access.
4. Deploy. `frontend/vercel.json` retains the SPA rewrite to `index.html`, so
   refreshing `/history` or `/documents/1` works.
5. Set Render `CORS_ORIGINS` to the assigned Vercel origin, without a trailing
   slash, e.g. `https://structify.vercel.app`. Multiple origins are comma-separated
   and trimmed. For previews, explicitly allow a stable preview domain; no wildcard.
6. Redeploy Vercel after changing the API URL: Vite embeds it at build time.

[Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite).

## 5. Preserve existing local PDFs (optional)

Database JSON/history is preserved automatically. Old rows have no R2 key until
originals are migrated; their PDF endpoint returns a helpful 404 until then.
Do this from the machine that contains the original PDFs, before removing any
old disk or changing hosts. Configure the same Neon/R2 credentials in local `.env`.
Stop uploads on the old deployment during migration. Do not run a second API
worker against the same database during the cutover.

From `backend`, first preview (no writes to PostgreSQL or R2):

```bash
python -B scripts/migrate_local_pdfs.py --upload-dir uploads/originals
```

Then explicitly apply:

```bash
python -B scripts/migrate_local_pdfs.py --upload-dir uploads/originals --apply
```

The script preserves IDs/JSON/timestamps and never deletes local files. It
prefers `<id>.pdf`, otherwise a safe filename under the supplied folder. Duplicate
legacy names are ambiguous and skipped unless you supply each original as
`<id>.pdf`; an original already overwritten by the old app cannot be recovered
by this script. It skips rows with R2 keys and uses deterministic keys for reruns
after an interrupted DB commit. Check all reported problems before deleting any
backup. Use an absolute `--upload-dir` when originals are elsewhere.

## Local development and verification

From `backend`:

```bash
python -m venv venv
# Activate: Windows venv/Scripts/activate; Linux/macOS source venv/bin/activate
python -m pip install -r requirements.txt
# Copy .env.example to .env and fill Neon, Gemini, and R2 values.
uvicorn main:app --reload --port 8000
```

Install Tesseract and Poppler locally or use Docker for the API:

```bash
docker build -t structify-api ./backend
docker run --rm --env-file backend/.env -p 8000:8000 structify-api
```

The Docker commands run from repository root. Remove local Windows OCR path
variables from the env file when using Docker. No volume mount is required.

From `frontend`:

```bash
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`; no frontend `.env` is needed locally.
Local backend CORS defaults to `http://localhost:5173`.

Checks:

```bash
# frontend
npm ci
npm run lint
npm run build
# backend
python -B -m unittest discover -s tests -v
python -m pip check
```

The regression suite mocks R2/Gemini, exercises HTTP routes, cleanup and error
handling, uses SQLite for portable CRUD checks, and compiles the PostgreSQL schema.
It does not prove live Neon/R2 permissions or real Gemini outputs. After deploying:

- Upload both digital and scanned sample PDFs and verify JSON + original preview.
- Upload two PDFs with the same name; confirm their originals differ as expected.
- Refresh a History/detail URL directly on Vercel.
- Restart Render and verify completed results and original PDFs still work.
- Confirm interrupted `processing` records become `failed` with an explanation.
- Check failed processing preserves the R2 original and leaves no temporary files.

## Demo reliability and access limits

Processing is in-process. Exactly one instance/worker is required; startup marks
leftover processing rows failed, never requeues them automatically. Re-upload
interrupted jobs. A forced process kill can leave temporary files until the
instance is replaced; they are never needed for later API behavior. No Celery,
Redis, queue service, paid disk, or horizontal scaling was added.

There is still no authentication or per-user isolation. CORS is not authentication:
anyone who can call this API can access its documents and request signed URLs.
Use non-sensitive demo data; add backend authentication before hosting private
user documents. Bucket privacy alone does not provide application-level access
control. Back up Neon and R2 independently. No real credentials, cloud resources,
or live migrations are created by this implementation.

## Validation performed for this change

- `npm ci`: passed after repairing an existing inconsistent transitive lock entry.
- `npm run lint`: passed.
- `npm run build`: passed (production Vite build).
- npm dependency audit after compatible lockfile fixes: zero known vulnerabilities.
- `python -B -m unittest discover -s tests -v`: 22 tests passed.
- `python -m pip check`: passed.
- Python AST syntax checks, deployment configuration assertions, stale runtime
  Mongo/local-storage reference search, changed-file local-secret comparison,
  and `git diff --check`: passed.
- Docker build: attempted, but Docker Desktop's Linux engine was not running.
- Live Neon/R2/Gemini end-to-end behavior and Linux OCR container: not verified.
  No live database schema/data migration or cloud deployment was performed.

The initial sandboxed npm installation failed; the clean install succeeded with
network access after lockfile repair. Lint/build passed both inside and outside
the sandbox. Backend HTTP tests likewise ran
outside the Windows sandbox for asyncio loopback support. Starlette emits a
TestClient/httpx deprecation warning, but all tests pass.
