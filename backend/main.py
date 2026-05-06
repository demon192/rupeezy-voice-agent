"""FastAPI backend for Rupeezy Voice Agent."""
import os
import time
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import database as db
from models import Lead, ConversationRequest, LeadBatchUpload
from conversation import generate_response, generate_opening, generate_summary
from scoring import score_conversation, get_recommended_action, detect_objections, detect_topics


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield

app = FastAPI(title="RupeezyVoice Agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# --- Lead Management ---

@app.post("/api/leads")
async def create_lead(lead: Lead):
    lead_id = await db.create_lead(lead.name, lead.phone, lead.language.value, lead.source)
    return {"id": lead_id, "message": f"Lead {lead.name} created"}


@app.post("/api/leads/batch")
async def batch_upload_leads(batch: LeadBatchUpload):
    leads_data = [{"name": l.name, "phone": l.phone, "language": l.language.value, "source": l.source} for l in batch.leads]
    ids = await db.batch_create_leads(leads_data)
    return {"ids": ids, "count": len(ids), "message": f"{len(ids)} leads uploaded"}


@app.get("/api/leads")
async def list_leads():
    leads = await db.get_all_leads()
    return {"leads": leads}


@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: int):
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@app.post("/api/leads/csv")
async def upload_csv_leads(data: dict):
    """Upload leads from CSV text. Expects {csv_text: "name,phone,language\\n..."}"""
    import csv
    import io
    reader = csv.DictReader(io.StringIO(data["csv_text"]))
    leads = []
    for row in reader:
        leads.append({
            "name": row.get("name", "").strip(),
            "phone": row.get("phone", "").strip(),
            "language": row.get("language", "english").strip().lower(),
            "source": "csv_upload"
        })
    leads = [l for l in leads if l["name"] and l["phone"]]
    if not leads:
        raise HTTPException(400, "No valid leads found in CSV")
    ids = await db.batch_create_leads(leads)
    return {"ids": ids, "count": len(ids), "message": f"{len(ids)} leads uploaded from CSV"}


# --- Conversation ---

@app.post("/api/conversation/start/{lead_id}")
async def start_conversation(lead_id: int):
    """Start a new conversation with a lead. Loads previous call context for multi-turn memory."""
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    # Check for existing active conversation
    existing = await db.get_active_conversation(lead_id)
    if existing:
        return {
            "conversation_id": existing["id"],
            "messages": existing["messages"],
            "message": "Resuming existing conversation"
        }
    
    # Load previous conversation context for multi-turn memory
    previous_context = await db.get_previous_summary(lead_id)
    
    # Create new conversation
    conv_id = await db.create_conversation(lead_id)
    
    # Generate opening (with context from previous calls if any)
    opening = await generate_opening(lead["name"], lead["language"], previous_context)
    
    messages = [{"role": "assistant", "content": opening, "timestamp": datetime.now().isoformat()}]
    await db.update_conversation_messages(conv_id, messages)
    await db.update_lead_status(lead_id, "in_progress")
    
    return {
        "conversation_id": conv_id,
        "opening": opening,
        "messages": messages,
        "has_previous_context": previous_context is not None
    }


@app.post("/api/conversation/chat")
async def chat(request: ConversationRequest):
    """Send a message and get AI response."""
    lead = await db.get_lead(request.lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    conv = await db.get_active_conversation(request.lead_id)
    if not conv:
        raise HTTPException(400, "No active conversation. Start one first.")
    
    # Load previous call context for multi-turn memory
    previous_context = await db.get_previous_summary(request.lead_id)
    
    # Add user message
    messages = conv["messages"]
    messages.append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate AI response
    result = await generate_response(
        lead_name=lead["name"],
        lead_language=lead["language"],
        conversation_history=messages[:-1],
        user_message=request.message,
        previous_context=previous_context
    )
    
    # Add AI response
    messages.append({
        "role": "assistant",
        "content": result["reply"],
        "timestamp": datetime.now().isoformat()
    })
    
    await db.update_conversation_messages(conv["id"], messages)
    
    # Detect hot signals — suggest RM to end call
    hot_phrases = [
        "sign up", "signup", "link bhejo", "interested", "haan chalega",
        "register", "join karna", "ready", "start karna", "haan bhai",
        "let's do it", "send me", "bhej do", "kar do", "theek hai chalega"
    ]
    user_lower = request.message.lower()
    suggest_end = any(phrase in user_lower for phrase in hot_phrases) and len(messages) >= 6
    
    # If call should end, generate summary
    if result["should_end"]:
        await end_and_summarize(request.lead_id, conv["id"], messages)
    
    return {
        "reply": result["reply"],
        "language_detected": result["language_detected"],
        "is_ended": result["should_end"],
        "suggest_end": suggest_end,
        "messages": messages
    }


@app.post("/api/conversation/end/{lead_id}")
async def end_conversation_endpoint(lead_id: int):
    """Manually end a conversation and generate summary."""
    conv = await db.get_active_conversation(lead_id)
    if not conv:
        raise HTTPException(400, "No active conversation")
    
    summary = await end_and_summarize(lead_id, conv["id"], conv["messages"])
    return summary


async def end_and_summarize(lead_id: int, conv_id: int, messages: list[dict]) -> dict:
    """End conversation, score lead, generate summary."""
    lead = await db.get_lead(lead_id)
    
    # Calculate duration
    if messages:
        start = datetime.fromisoformat(messages[0].get("timestamp", datetime.now().isoformat()))
        end = datetime.fromisoformat(messages[-1].get("timestamp", datetime.now().isoformat()))
        duration = int((end - start).total_seconds())
    else:
        duration = 0
    
    # Score the lead
    score_result = score_conversation(messages, duration)
    
    # Detect objections and topics
    objections = detect_objections(messages)
    topics = detect_topics(messages)
    
    # Get recommended action
    action = get_recommended_action(score_result["status"], lead["name"])
    
    # Generate LLM summary
    summary_text = await generate_summary(lead["name"], messages)
    
    # Save
    summary_data = {
        "lead_id": lead_id,
        "conversation_id": conv_id,
        "duration_seconds": duration,
        "messages_count": len(messages),
        "language_used": lead["language"],
        "objections_raised": objections,
        "topics_covered": topics,
        "interest_score": score_result["status"].value,
        "score_numeric": score_result["score"],
        "recommended_action": action,
        "summary_text": summary_text,
    }
    
    await db.create_summary(summary_data)
    await db.end_conversation(conv_id)
    await db.update_lead_status(lead_id, score_result["status"].value, score_result["score"])
    
    return {
        "summary": summary_data,
        "scoring_signals": score_result["signals"],
        "message": f"Call ended. Lead classified as {score_result['status'].value.upper()}"
    }


# --- Dashboard ---

@app.get("/api/dashboard/stats")
async def dashboard_stats():
    return await db.get_dashboard_stats()


@app.get("/api/dashboard/summaries")
async def dashboard_summaries():
    summaries = await db.get_all_summaries()
    return {"summaries": summaries}


@app.get("/api/dashboard/hot-leads")
async def hot_leads():
    """Get hot leads ready for RM handoff."""
    leads = await db.get_all_leads()
    hot = [l for l in leads if l["status"] == "hot"]
    
    # Get their summaries for context
    summaries = await db.get_all_summaries()
    hot_summaries = {s["lead_id"]: s for s in summaries if s["interest_score"] == "hot"}
    
    results = []
    for lead in hot:
        results.append({
            "lead": lead,
            "summary": hot_summaries.get(lead["id"]),
            "handoff_ready": True
        })
    return {"hot_leads": results, "count": len(results)}


@app.get("/api/dashboard/transcript/{lead_id}")
async def get_transcript(lead_id: int):
    """Get full conversation transcript for a lead."""
    conversations = await db.get_all_conversations_for_lead(lead_id)
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return {"lead": lead, "conversations": conversations}


@app.post("/api/whatsapp/send/{lead_id}")
async def send_whatsapp(lead_id: int):
    """Generate WhatsApp follow-up link using wa.me click-to-chat."""
    lead = await db.get_lead(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    from knowledge import WHATSAPP_FOLLOWUP
    import urllib.parse
    
    message = WHATSAPP_FOLLOWUP.format(lead_name=lead["name"])
    
    # Build wa.me link (strip leading 0 or +, ensure country code)
    phone = lead["phone"].replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if not phone.startswith("91"):
        phone = "91" + phone
    
    wa_url = f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
    
    # Log the WhatsApp message
    await db.log_whatsapp(lead_id, message)
    
    return {
        "lead_id": lead_id,
        "phone": lead["phone"],
        "message_preview": message,
        "wa_url": wa_url,
        "status": "sent"
    }


@app.get("/api/whatsapp/log")
async def get_whatsapp_log():
    """Get all WhatsApp messages sent."""
    logs = await db.get_whatsapp_logs()
    return {"messages": logs}


# --- Frontend serving ---

@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


# Mount static files last
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
