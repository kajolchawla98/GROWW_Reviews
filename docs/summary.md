# Project Summary — GROWW AI Product Intelligence Copilot

> A simple explanation of what this project does and how it works.

---

## What Is This Project?

Imagine you're a Product Manager at GROWW. Every week, thousands of users leave reviews on the Google Play Store — some love the app, some are frustrated with bugs, some want new features. Reading all these reviews manually is impossible.

**This project is like hiring an AI team of analysts** that reads every single review, finds patterns, and gives you a neat weekly report saying:

- "Hey, UPI payment failures jumped 32% this week"
- "KYC delays are the #1 complaint — here's what we should do about it"
- "Here are the 3 most important things to fix this sprint"

And it does this **automatically, every week**, delivering the report straight to your Google Docs and Gmail.

---

## How Does It Work? (The Simple Version)

Think of it like a **relay race with 8 runners** (AI agents), each doing one specific job and passing the baton to the next:

```
📥 Fetch Reviews → 🏷️ Group by Topic → 💬 Analyze Feelings → 📈 Spot Trends
     ↓                                                            ↓
📤 Email Report ← 📊 Write Report ← 🧠 Suggest Actions ← ⚡ Score Severity
```

### The 8 AI Agents (Your Virtual Team)

| # | Agent | What It Does (In Simple Words) |
|---|-------|-------------------------------|
| 1 | **Review Collector** | Goes to Google Play Store and grabs all recent GROWW reviews |
| 2 | **Topic Organizer** | Groups reviews into categories like "UPI Issues", "KYC Problems", "App Crashes" (max 5 groups) |
| 3 | **Mood Analyzer** | Reads each review and determines if the user is happy, angry, frustrated, etc. |
| 4 | **Trend Spotter** | Compares this week vs last week — finds what's getting worse or better |
| 5 | **Priority Scorer** | Gives each issue a score out of 100 so you know what to fix first |
| 6 | **Action Advisor** | Suggests specific product actions (not just "fix bugs" but "add retry guidance for UPI failures") |
| 7 | **Report Writer** | Creates a one-page weekly summary with the top insights |
| 8 | **Report Publisher** | Publishes the report to Google Docs and creates a Gmail draft for stakeholders |

---

## What Is "Multi-Agent" Architecture?

Instead of one big AI doing everything, we use **multiple small, specialized AIs** that work together like a team:

```
┌─────────────────────────────────────────────┐
│            ORCHESTRATOR (The Manager)        │
│                                             │
│  Agent 1 → Agent 2 ─┐                      │
│                      ├→ Agent 4 → Agent 5   │
│            Agent 3 ─┘                       │
│                        → Agent 6 → Agent 7  │
│                                   → Agent 8 │
└─────────────────────────────────────────────┘
```

**Why multiple agents?**
- Each agent is simple and focused (easier to test and debug)
- Some agents can run in parallel (Topic + Mood analysis happen at the same time)
- If one agent fails, it doesn't crash everything
- Each agent produces a clear, structured output that the next agent can use

---

## What Is MCP? (Model Context Protocol)

MCP is a **standard way for AI agents to use external tools** like Google Docs and Gmail.

Think of it like a universal remote control:
- Instead of building custom Google Docs integration from scratch...
- We use an MCP "server" that already knows how to talk to Google Docs
- Our AI agent just says "create a document with this content" and the MCP server handles the rest

```
Our AI Agent  →  "Hey, create a doc"  →  MCP Server  →  Google Docs API  →  📄 Document Created!
Our AI Agent  →  "Draft an email"     →  MCP Server  →  Gmail API        →  ✉️ Draft Ready!
```

**We use 2 MCP servers:**
1. **Google Docs MCP** — Creates and shares the weekly report as a Google Doc
2. **Gmail MCP** — Creates a draft email with the report summary for stakeholders

---

## What Does the User See?

### 1. Executive Dashboard
A beautiful web dashboard with:
- **Summary Cards** — Overall sentiment, review count, critical issues at a glance
- **Theme Intelligence** — The top 5 issues with severity, trends, and AI summaries
- **Trend Charts** — Visual week-over-week comparisons
- **Recommendations** — "Here's what you should do about it"

### 2. Review Replay
A live feed of review cards, each showing:
- The anonymized user quote
- Star rating
- Which topic it belongs to
- What emotion was detected
- How severe the issue is

### 3. Ask Reviews (Chat)
Type natural questions like:
- "What are users most frustrated about?"
- "Summarize KYC complaints"
- "What changed after the latest release?"

The AI searches through all reviews and gives you a grounded answer with evidence.

### 4. Weekly Pulse (Auto-Generated)
A one-page executive report that gets:
- Published to Google Docs automatically
- Drafted in Gmail ready to send to your team

---

## Project Folder Structure

```
GROWW/
├── docs/                          # All documentation
│   ├── problem_statement.md       # What we're building and why
│   ├── architecture.md            # Technical architecture (detailed)
│   ├── phase-wise-implementation.md  # 6-phase build plan
│   └── summary.md                 # This file — simple explanation
│
├── phases/                        # Phase-specific eval/testing docs
│   ├── phase_1/eval_phase_1.md    # Data Ingestion testing
│   ├── phase_2/eval_phase_2.md    # AI Analysis testing
│   ├── phase_3/eval_phase_3.md    # Intelligence & Scoring testing
│   ├── phase_4/eval_phase_4.md    # Dashboard UI testing
│   ├── phase_5/eval_phase_5.md    # MCP Publishing testing
│   └── phase_6/eval_phase_6.md    # Ask Reviews & Polish testing
│
├── backend/                       # Python FastAPI backend
│   ├── app/
│   │   ├── main.py                # FastAPI app entry point
│   │   ├── config.py              # Environment configuration
│   │   ├── agents/                # AI agents (one per file)
│   │   │   └── ingestion_agent.py # Agent 1: Fetch & clean reviews
│   │   ├── models/                # Database models (SQLAlchemy)
│   │   │   └── database.py        # Reviews, PipelineRuns tables
│   │   ├── schemas/               # Data contracts (Pydantic)
│   │   │   └── review.py          # ReviewRecord, API schemas
│   │   ├── services/              # Business logic services
│   │   │   ├── pipeline_runner.py # Orchestrator (runs all agents)
│   │   │   └── vector_store.py    # ChromaDB for semantic search
│   │   └── api/                   # API route handlers
│   │       └── routes.py          # REST endpoints
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment variable template
│
└── frontend/                      # Next.js dashboard (Phase 4)
```

---

## How the Data Flows

```
Google Play Store
       ↓
  [Fetch Reviews]  ──→  SQLite/PostgreSQL (structured data)
       ↓                        ↓
  [Strip PII]              [REST API]  →  Dashboard
       ↓                        
  [Embed Text]  ──→  ChromaDB (vector search)  →  "Ask Reviews" Chat
       ↓
  [AI Analysis Pipeline]
       ↓
  [Weekly Pulse Report]
       ↓
  [MCP Publish]  ──→  Google Docs + Gmail Draft
```

---

## Key Technologies Used

| What | Technology | Why |
|------|-----------|-----|
| Backend server | **FastAPI** (Python) | Fast, async, auto-generates API docs |
| Database | **SQLite** (dev) / **PostgreSQL** (prod) | Stores reviews and analysis results |
| Vector search | **ChromaDB** | Enables semantic "find similar reviews" |
| Review scraping | **google-play-scraper** | Fetches Play Store reviews easily |
| AI/LLM | **OpenAI GPT-4o** or **Google Gemini** | Powers the AI agents |
| Frontend | **Next.js** (React) | Modern web dashboard |
| Publishing | **MCP servers** | Standardized Google Docs/Gmail integration |

---

## The 6 Phases of Building This

| Phase | What Gets Built | Duration |
|-------|----------------|----------|
| **1** | Fetch reviews + store in database + vector store | ~1 week |
| **2** | Topic grouping + sentiment analysis (2 AI agents) | ~10 days |
| **3** | Trend detection + impact scoring + recommendations | ~1 week |
| **4** | Web dashboard with all visualizations | ~10 days |
| **5** | Google Docs + Gmail publishing via MCP | ~1 week |
| **6** | "Ask Reviews" chat + final polish | ~1 week |

**Current Status**: Phase 1 implemented ✅

---

## Privacy & Safety

- **No user names stored** — all reviews are anonymized
- **No emails or phone numbers** — PII is stripped before storage
- **Gmail creates drafts, not sent emails** — human review before sending
- **All API keys in environment variables** — never hardcoded
