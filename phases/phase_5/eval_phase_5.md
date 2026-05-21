# Phase 5: MCP Publishing (Docs & Gmail) - Evaluation & Exit Criteria

## Objective
Verify that the `PublishingAgent` successfully orchestrates data via the remote MCP Server to push the generated Weekly Pulse report to Google Docs and Gmail drafts.

## Acceptance Criteria

1. **Environment Configuration**
   - [ ] `.env` includes `MCP_SERVER_URL` pointing to the remote server.
   - [ ] `.env` includes `PUBLISH_DOC_ID` and `PUBLISH_EMAIL_TO` variables.

2. **Publishing Agent Implementation**
   - [ ] `PublishingAgent` is implemented in `backend/app/agents/publishing_agent.py`.
   - [ ] Calls `POST /append_to_doc` on the MCP server with `doc_id` and markdown `content`.
   - [ ] Calls `POST /create_email_draft` on the MCP server with `to`, `subject`, and HTML `body`.
   - [ ] Gracefully handles HTTP timeout or 500 status code errors from the remote server.

3. **API Endpoints**
   - [ ] `POST /api/v1/pulses/{pulse_id}/publish` accepts `target` query param (`google_docs`, `gmail`, `both`).
   - [ ] Returns a structured JSON payload with individual success/failure statuses for each target.

4. **Dashboard Integration**
   - [ ] "Publish to Docs" button exists in the Weekly Pulse tab.
   - [ ] "Draft in Gmail" button exists in the Weekly Pulse tab.
   - [ ] UI displays proper loading state (`Publishing...` / `Drafting...`).
   - [ ] UI shows success or error messages cleanly after completion.

## Testing Instructions

1. Ensure your backend is running: `python -m uvicorn app.main:app --port 8000`.
2. Ensure you have run the pipeline at least once to generate a Weekly Pulse.
3. Open the UI at `http://localhost:3000` and navigate to the **Weekly Pulse** tab.
4. Click **Publish to Docs**.
   - **Expected**: Loading state appears, then a success message shows `Successfully published to google docs!`.
5. Click **Draft in Gmail**.
   - **Expected**: Loading state appears, then a success message shows `Successfully published to gmail!`.
6. **(Verification)**: Open the target Google Doc (using the ID from `.env`) and check if the timestamped Markdown pulse report was appended! Check your Gmail drafts for the new email.

## Exit Status
✅ **Project Complete**
