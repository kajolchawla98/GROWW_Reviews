# Deployment Guide

This guide covers deploying the GROWW AI Product Intelligence Copilot to production.

---

## Local Development (Run Both Frontend + Backend)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Groq API key → https://console.groq.com/keys

### 1. Start the Backend

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt   # first time only

uvicorn app.main:app --reload --port 8000
```

Backend will be live at: http://localhost:8000  
API docs at: http://localhost:8000/docs

### 2. Start the Frontend (new terminal)

```bash
cd frontend
npm install        # first time only
npm run dev
```

Frontend will be live at: http://localhost:3000

### 3. Run the Pipeline (first time)

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d "{\"app_id\": \"com.nextbillion.groww\", \"weeks\": 4}"
```

Or click the **🔄 Refresh Now** button on the Weekly Pulse tab in the UI.

---

## Production Deployment

### Backend → Railway

#### Prerequisites
- Railway account → https://railway.app
- GitHub repo with this code
- Groq API key

#### Steps

1. Go to https://railway.app → New Project → Deploy from GitHub repo
2. Select your repository, set **Root Directory** to `backend`
3. Railway auto-detects the `Procfile` and uses:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add these environment variables in Railway → Variables:

   | Variable | Value |
   |---|---|
   | `GROQ_API_KEY` | Your Groq API key from console.groq.com |
   | `DEBUG` | `false` |
   | `GROWW_APP_ID` | `com.nextbillion.groww` |
   | `REVIEW_WEEKS` | `4` |
   | `GROQ_MODEL` | `llama-3.1-8b-instant` |
   | `GROQ_MODEL_LARGE` | `llama-3.3-70b-versatile` |
   | `GROQ_RPM` | `28` |
   | `GROQ_RPD` | `14000` |
   | `GROQ_TPM` | `5500` |
   | `BATCH_SIZE` | `50` |
   | `LLM_BATCH_SIZE` | `25` |
   | `MCP_SERVER_URL` | `https://saksham-mcp-server-production-0909.up.railway.app` |
   | `PUBLISH_DOC_ID` | Your Google Doc ID |
   | `PUBLISH_EMAIL_TO` | Your email |

   > **Database**: Leave `DATABASE_URL` unset to use SQLite (fine for demo).  
   > For production persistence, add a Railway PostgreSQL plugin and it will auto-set `DATABASE_URL`.

5. Click **Deploy**. Railway gives you a URL like `https://your-backend.up.railway.app`

6. Verify:
   ```bash
   curl https://your-backend.up.railway.app/health
   ```
   Expected:
   ```json
   {"status": "healthy", "database": "connected", "version": "0.3.0"}
   ```

---

### Frontend → Vercel

#### Prerequisites
- Vercel account → https://vercel.com
- Backend deployed on Railway (you need the URL)

#### Steps

1. Go to https://vercel.com → Add New Project → Import GitHub repo
2. Set **Root Directory** to `frontend`
3. Add this environment variable:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://your-backend.up.railway.app/api/v1` |

4. Click **Deploy**. Vercel gives you a URL like `https://your-app.vercel.app`

5. Verify: open the Vercel URL in your browser — the dashboard should load.

---

### GitHub Actions Scheduler

This triggers the pipeline automatically every day at 10 AM UTC.

#### Steps

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Click **New repository secret**:

   | Secret | Value |
   |---|---|
   | `API_URL` | `https://your-backend.up.railway.app` (no trailing slash, no `/api/v1`) |

3. Go to the **Actions** tab → select **Daily Pipeline Run** → click **Run workflow** to test it manually first.

4. After confirming it works, the cron (`0 10 * * *`) will run it daily automatically.

---

## Environment Variables Reference

### Backend (.env for local / Railway Variables for prod)

```env
# Required
GROQ_API_KEY=gsk_...

# Optional (defaults shown)
DEBUG=false
GROWW_APP_ID=com.nextbillion.groww
REVIEW_WEEKS=4
REVIEW_LANGUAGE=en
REVIEW_COUNTRY=in
MAX_REVIEWS=1000
MIN_WORD_COUNT=6
GROQ_MODEL=llama-3.1-8b-instant
GROQ_MODEL_LARGE=llama-3.3-70b-versatile
GROQ_RPM=28
GROQ_RPD=14000
GROQ_TPM=5500
BATCH_SIZE=50
LLM_BATCH_SIZE=25
MCP_SERVER_URL=https://saksham-mcp-server-production-0909.up.railway.app
PUBLISH_DOC_ID=your_google_doc_id
PUBLISH_EMAIL_TO=your@email.com

# For production PostgreSQL (Railway auto-sets this if you add the plugin)
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

### Frontend (Vercel Environment Variables)

```env
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app/api/v1
```

### GitHub Actions Secrets

```
API_URL=https://your-backend.up.railway.app
```

---

## Verification Checklist

- [ ] `GET /health` returns `{"status": "healthy"}`
- [ ] `POST /api/v1/pipeline/run` returns HTTP 202
- [ ] Frontend loads at Vercel URL without console errors
- [ ] Weekly Pulse tab shows data after pipeline completes
- [ ] GitHub Actions workflow runs successfully (check Actions tab)
- [ ] "Last updated" date on Pulse tab updates after each run

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Backend won't start | Check `GROQ_API_KEY` is set in `.env` |
| Frontend shows "No data yet" | Run the pipeline first via curl or the UI button |
| `NEXT_PUBLIC_API_URL` not working | Make sure it ends with `/api/v1`, not just the base URL |
| GitHub Actions fails with "API_URL not set" | Add `API_URL` secret in repo Settings → Secrets |
| Pipeline fails mid-run | Check `/api/v1/pipeline/status/{run_id}` or Railway logs |
| SQLite data lost on Railway redeploy | Add Railway PostgreSQL plugin for persistent storage |

---

## Cost Estimate

| Service | Free Tier | Paid |
|---|---|---|
| Vercel (frontend) | 100 GB bandwidth/mo | $20/mo Pro |
| Railway (backend) | $5 credit/mo | ~$5–15/mo |
| Groq API | 14,400 req/day free | Pay-as-you-go |
| **Total** | **~$0** | **~$25–35/mo** |
