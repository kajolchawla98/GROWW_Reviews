import logging
import httpx
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from app.config import settings
from app.models.database import PulseRecord

logger = logging.getLogger(__name__)

class PublishingAgent:
    """
    Agent 8 — Publishes Pulse reports to Google Docs and Gmail drafts via the MCP Server.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.mcp_url = settings.MCP_SERVER_URL.rstrip('/')
        
    async def publish_pulse(
        self, 
        pulse_id: str, 
        target: str = "both", 
        doc_id: Optional[str] = None, 
        email_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a specific pulse report via MCP server.
        target can be: "google_docs", "gmail", "both"
        """
        pulse = self.db.query(PulseRecord).filter(
            (PulseRecord.id == pulse_id) | (PulseRecord.pulse_id == pulse_id)
        ).first()
        if not pulse:
            raise ValueError(f"Pulse with ID {pulse_id} not found")
            
        doc_id = doc_id or settings.PUBLISH_DOC_ID
        email_to = email_to or settings.PUBLISH_EMAIL_TO
        
        results = {"status": "success", "targets": []}
        
        async with httpx.AsyncClient() as client:
            # 1. Publish to Google Docs
            if target in ["google_docs", "both"] and doc_id:
                try:
                    logger.info("Publishing to Google Doc: %s", doc_id)
                    resp = await client.post(
                        f"{self.mcp_url}/append_to_doc",
                        json={"doc_id": doc_id, "content": pulse.markdown_content},
                        timeout=30.0
                    )
                    resp.raise_for_status()
                    results["targets"].append({"type": "google_docs", "status": "success"})
                except Exception as e:
                    logger.error("Failed to publish to Google Docs: %s", e)
                    results["targets"].append({"type": "google_docs", "status": "error", "message": str(e)})
                    
            # 2. Publish to Gmail Draft
            if target in ["gmail", "both"] and email_to:
                try:
                    logger.info("Creating Gmail draft for: %s", email_to)
                    # Convert markdown to basic HTML for email body
                    html_body = pulse.markdown_content.replace('\n', '<br>')
                    resp = await client.post(
                        f"{self.mcp_url}/create_email_draft",
                        json={
                            "to": email_to,
                            "subject": f"GROWW Product Pulse - {pulse.week_label}",
                            "body": html_body
                        },
                        timeout=30.0
                    )
                    resp.raise_for_status()
                    results["targets"].append({"type": "gmail", "status": "success"})
                except Exception as e:
                    logger.error("Failed to create Gmail draft: %s", e)
                    results["targets"].append({"type": "gmail", "status": "error", "message": str(e)})
                    
        return results
