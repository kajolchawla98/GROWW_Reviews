import logging
import json
from typing import Dict, Any

from groq import Groq
from app.config import settings
from app.services.vector_store import VectorStoreService
from app.services.groq_client import groq_limiter

logger = logging.getLogger(__name__)

class AskReviewsAgent:
    """
    RAG Assistant — Queries the vector store for context and generates an LLM answer.
    """
    
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        
    async def ask(self, query: str) -> Dict[str, Any]:
        """
        Retrieves context and generates answer with citations.
        """
        logger.info(f"RAG Query: '{query}'")
        
        # 1. Retrieve Context
        try:
            results = self.vector_store.search(query, top_k=10)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"answer": "I'm having trouble searching the database right now.", "citations": []}
            
        docs = results.get('documents', [[]])[0]
        metas = results.get('metadatas', [[]])[0]
        
        if not docs:
            return {"answer": "I couldn't find any relevant reviews to answer your question.", "citations": []}
            
        # Format Context
        context_str = ""
        citations = []
        for i, (doc, meta) in enumerate(zip(docs, metas)):
            context_str += f"[Citation {i+1}] Review: \"{doc}\"\n"
            context_str += f"Rating: {meta.get('rating')} | Date: {meta.get('review_date')}\n\n"
            citations.append({
                "id": i+1,
                "text": doc,
                "rating": meta.get('rating'),
                "date": meta.get('review_date')
            })
            
        # 2. Generate LLM Answer
        prompt = f"""
You are the GROWW AI Product Intelligence Assistant. 
Answer the PM's question based ONLY on the following user reviews context.
Whenever you state a fact or quote a user, you MUST cite it using [Citation #].

CONTEXT:
{context_str}

QUESTION:
{query}

Respond in JSON format:
{{
    "answer": "Your detailed answer using markdown and citations like [Citation 1]...",
    "confidence": 0.95
}}
"""
        
        try:
            groq_limiter.wait_if_needed(estimated_tokens=500)
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            groq_limiter.record_request(actual_tokens=response.usage.total_tokens)
            
            response_data = json.loads(response.choices[0].message.content)
            
            return {
                "answer": response_data.get("answer", "No answer generated."),
                "citations": citations,
                "confidence": response_data.get("confidence", 0.0)
            }
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {"answer": "I retrieved the reviews but failed to generate a summary.", "citations": citations}
