"""Lead scoring module — classifies leads as Hot, Warm, or Cold."""
from models import LeadStatus


def score_conversation(messages: list[dict], duration_seconds: int) -> dict:
    """
    Score a lead based on conversation signals.
    
    Signals used:
    - Engagement duration (longer = more interested)
    - Number of messages exchanged
    - Positive intent phrases (asking about sign-up, process, etc.)
    - Objection patterns (resolved objections = warmer)
    - Negative signals (firm rejection, quick exit)
    
    Returns: {"score": 0-100, "status": "hot"|"warm"|"cold", "signals": [...]}
    """
    score = 50  # Start neutral
    signals = []
    
    user_messages = [m for m in messages if m.get("role") == "user"]
    user_text = " ".join(m.get("content", "").lower() for m in user_messages)
    msg_count = len(user_messages)
    
    # --- Positive signals ---
    
    # High-intent phrases
    hot_phrases = [
        "sign up", "signup", "register", "link bhejo", "send link", 
        "how to join", "kaise join", "start karna hai", "interested",
        "let's do it", "ready", "send me", "bhej do", "haan chalega",
        "sign karna hai", "process kya hai", "documents kya chahiye",
        "how many clients", "kitne clients", "i have clients"
    ]
    for phrase in hot_phrases:
        if phrase in user_text:
            score += 12
            signals.append(f"High-intent: '{phrase}'")
    
    # Asking questions = engaged
    question_indicators = ["?", "kya", "kaise", "kitna", "how", "what", "when", "where"]
    questions_asked = sum(1 for m in user_messages if any(q in m.get("content", "").lower() for q in question_indicators))
    if questions_asked >= 3:
        score += 10
        signals.append(f"Asked {questions_asked} questions — engaged")
    elif questions_asked >= 1:
        score += 5
        signals.append(f"Asked {questions_asked} question(s)")
    
    # Duration-based scoring
    if duration_seconds > 300:  # 5+ minutes
        score += 15
        signals.append("Long conversation (5+ min)")
    elif duration_seconds > 120:  # 2+ minutes
        score += 8
        signals.append("Good engagement (2+ min)")
    elif duration_seconds < 30:
        score -= 15
        signals.append("Very short conversation (<30s)")
    
    # Message count
    if msg_count >= 8:
        score += 10
        signals.append(f"High message count ({msg_count})")
    elif msg_count >= 4:
        score += 5
    elif msg_count <= 2:
        score -= 10
        signals.append("Low engagement (<=2 messages)")
    
    # --- Negative signals ---
    
    cold_phrases = [
        "not interested", "interest nahi", "don't call", "mat karo call",
        "no thanks", "nahi chahiye", "waste of time", "stop", "bye",
        "already told you no", "spam"
    ]
    for phrase in cold_phrases:
        if phrase in user_text:
            score -= 20
            signals.append(f"Rejection signal: '{phrase}'")
    
    # --- Objection patterns ---
    objection_keywords = [
        "already with", "broker hai", "contacts nahi", "don't have clients",
        "trust", "bharosa", "think about", "sochna", "later", "baad mein",
        "support", "problem"
    ]
    objections_raised = sum(1 for kw in objection_keywords if kw in user_text)
    if objections_raised > 0 and msg_count > 4:
        # Raised objections but continued talking = engaged, working through concerns
        score += 5
        signals.append(f"Raised {objections_raised} objection(s) but stayed engaged")
    elif objections_raised > 2 and msg_count <= 3:
        score -= 10
        signals.append("Multiple objections with quick exit")
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Classify
    if score >= 70:
        status = LeadStatus.HOT
    elif score >= 40:
        status = LeadStatus.WARM
    else:
        status = LeadStatus.COLD
    
    return {
        "score": score,
        "status": status,
        "signals": signals
    }


def get_recommended_action(status: LeadStatus, lead_name: str) -> str:
    """Get recommended next action based on lead status."""
    if status == LeadStatus.HOT:
        return f"IMMEDIATE: Transfer {lead_name} to RM queue. Lead is ready to sign up. Share full conversation context with RM."
    elif status == LeadStatus.WARM:
        return f"FOLLOW-UP: Send WhatsApp sign-up link to {lead_name}. Schedule callback in 2-3 days. Lead is interested but needs time."
    else:
        return f"NURTURE: Log {lead_name} for future nurture campaign. No immediate action needed. Re-engage in 2-4 weeks."


def detect_objections(messages: list[dict]) -> list[str]:
    """Detect which objections were raised in the conversation."""
    user_text = " ".join(
        m.get("content", "").lower() for m in messages if m.get("role") == "user"
    )
    
    objections = []
    
    objection_map = {
        "Already with another broker": ["already with", "broker hai", "already partnered", "another broker"],
        "Not enough contacts": ["don't have contacts", "contacts nahi", "small network", "kam log"],
        "Support concerns": ["support", "client issues", "problems", "customer service"],
        "Trust/credibility": ["trust", "bharosa", "safe", "genuine", "scam", "fraud"],
        "Need time to decide": ["think about", "sochna", "later", "baad mein", "not now", "abhi nahi"],
    }
    
    for objection_name, keywords in objection_map.items():
        if any(kw in user_text for kw in keywords):
            objections.append(objection_name)
    
    return objections


def detect_topics(messages: list[dict]) -> list[str]:
    """Detect topics covered in the conversation."""
    all_text = " ".join(m.get("content", "").lower() for m in messages)
    
    topics = []
    topic_map = {
        "Brokerage share": ["100%", "brokerage", "share", "commission"],
        "Zero joining fee": ["zero fee", "no fee", "joining fee", "free"],
        "Daily payouts": ["daily", "payout", "payment", "RISE portal"],
        "Eligibility": ["eligible", "who can", "documents", "kyc", "pan"],
        "Sign-up process": ["sign up", "register", "link", "process"],
        "Client support": ["support", "help", "service"],
        "Platform/technology": ["app", "platform", "trading", "technology"],
        "SEBI registration": ["sebi", "registered", "license", "compliant"],
    }
    
    for topic_name, keywords in topic_map.items():
        if any(kw in all_text for kw in keywords):
            topics.append(topic_name)
    
    return topics
