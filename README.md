# GROWW AI Product Intelligence Copilot

AI-native Product Intelligence Copilot that transforms GROWW app reviews into weekly executive pulses via multi-agent AI workflows.

## Quick Start

### 1. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 3. Trigger the Pipeline

```bash
# Start ingestion
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"app_id": "com.nextbillion.groww", "weeks": 4}'

# Check status
curl http://localhost:8000/api/v1/pipeline/status/{pipeline_run_id}

# View reviews
curl http://localhost:8000/api/v1/reviews?limit=10
```

### 4. API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger docs.

### 5. Automated Pipeline Scheduling

The project includes a GitHub Actions workflow that automatically runs the pipeline daily at 10:00 AM UTC to fetch fresh data.

**Setup Instructions:**

1. Push your code to a GitHub repository
2. Go to repository Settings → Secrets and variables → Actions
3. Add a new secret named `API_URL` with your backend API URL (e.g., `https://your-backend-url.com`)
4. The workflow will automatically run daily at 10:00 AM UTC
5. You can also manually trigger the workflow from the Actions tab in GitHub

**Customize Schedule:**

Edit `.github/workflows/daily-pipeline.yml` to change the cron schedule. Use [crontab.guru](https://crontab.guru/) to convert your desired time to cron format.

## Documentation

| Document | Description |
|----------|-------------|
| [Problem Statement](docs/problem_statement.md) | What we're building and why |
| [Architecture](docs/architecture.md) | Detailed technical architecture |
| [Implementation Plan](docs/phase-wise-implementation.md) | 5-phase build plan |
| [Summary](docs/summary.md) | Simple explanation of the project |

## Project Status

- [x] Phase 1 — Data Ingestion & Storage
- [ ] Phase 2 — Core AI Analysis Agents
- [ ] Phase 3 — Intelligence & Scoring
- [ ] Phase 4 — Executive Dashboard
- [ ] Phase 5 — MCP Publishing (Docs + Gmail)
