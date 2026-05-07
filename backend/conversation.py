"""LLM-powered conversation engine using Groq."""
import os
import json
from groq import Groq
from knowledge import SYSTEM_PROMPT, KEY_BENEFITS, OBJECTION_HANDLERS, FAQ, CLOSING_SCRIPT

client: Groq = None


def get_client() -> Groq:
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment")
        client = Groq(api_key=api_key)
    return client


def build_system_message(lead_name: str, lead_language: str) -> str:
    """Build the full system prompt with knowledge base context."""
    language_instructions = {
        "hindi": "\nIMPORTANT: This lead prefers Hindi. Respond primarily in Hindi (Devanagari script is NOT needed — use romanized Hindi). Mix in English technical terms naturally.",
        "hinglish": "\nIMPORTANT: This lead prefers Hinglish. Mix Hindi and English naturally, the way educated Indians casually speak.",
        "tamil": "\nIMPORTANT: This lead prefers Tamil. Respond in romanized Tamil (NOT Tamil script). Use simple Tamil with English financial/technical terms mixed in naturally. Start with 'Vanakkam'.",
        "telugu": "\nIMPORTANT: This lead prefers Telugu. Respond in romanized Telugu (NOT Telugu script). Use simple Telugu with English financial/technical terms mixed in naturally. Start with 'Namaskaram'.",
        "marathi": "\nIMPORTANT: This lead prefers Marathi. Respond in romanized Marathi (NOT Devanagari). Use simple Marathi with English financial/technical terms mixed in naturally. Start with 'Namaskar'.",
        "gujarati": "\nIMPORTANT: This lead prefers Gujarati. Respond in romanized Gujarati (NOT Gujarati script). Use simple Gujarati with English financial/technical terms mixed in naturally. Start with 'Kem cho'.",
        "bengali": "\nIMPORTANT: This lead prefers Bengali. Respond in romanized Bengali (NOT Bengali script). Use simple Bengali with English financial/technical terms mixed in naturally. Start with 'Namaskar'.",
        "english": "\nThis lead prefers English. Respond in clear, conversational English.",
    }
    language_instruction = language_instructions.get(lead_language, language_instructions["english"])

    objection_context = "\n\nOBJECTION HANDLING REFERENCE:\n"
    for key, obj in OBJECTION_HANDLERS.items():
        objection_context += f"\nIf lead says something like: {obj['trigger_phrases'][:3]}\nRespond with this approach: {obj['response'][:200]}...\n"

    faq_context = "\n\nFAQ REFERENCE:\n"
    for q, a in FAQ.items():
        faq_context += f"Q: {q} → A: {a}\n"

    return (
        SYSTEM_PROMPT
        + f"\n\nLead name: {lead_name}"
        + language_instruction
        + objection_context
        + faq_context
        + f"\n\nKEY BENEFITS TO PITCH:\n{KEY_BENEFITS}"
    )


def detect_language(text: str) -> str:
    """Detect language from text — supports Hindi, English, Hinglish, Tamil, Telugu, Marathi, Gujarati, Bengali."""
    
    # Script-based detection (most reliable)
    tamil_chars = set("அஆஇஈஉஊஎஏஐஒஓஔகஙசஞடணதநபமயரலவழளறன")
    telugu_chars = set("అఆఇఈఉఊఎఏఐఒఓఔకఖగఘచఛజఝటఠడఢణతథదధనపఫబభమయరలవశషసహ")
    bengali_chars = set("অআইঈউঊএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহ")
    gujarati_chars = set("અઆઇઈઉઊએઐઓઔકખગઘચછજઝટઠડઢણતથદધનપફબભમયરલવશષસહ")
    marathi_chars = set("अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह")  # Same as Hindi Devanagari
    hindi_chars = set("अआइईउऊएऐओऔकखगघचछजझटठडढणतथदधनपफबभमयरलवशषसह")
    
    if any(c in tamil_chars for c in text):
        return "tamil"
    if any(c in telugu_chars for c in text):
        return "telugu"
    if any(c in bengali_chars for c in text):
        return "bengali"
    if any(c in gujarati_chars for c in text):
        return "gujarati"
    
    # Romanized regional language detection
    tamil_words = [
        "naan", "enna", "ungaluku", "romba", "theriyum", "pannunga",
        "seri", "vaanga", "ponga", "illa", "irukku", "sollunga",
        "nallavaa", "epdi", "inga", "anga", "podhu", "vanakkam"
    ]
    telugu_words = [
        "nenu", "meeku", "cheppandi", "baaga", "undhi", "chestha",
        "randi", "ledu", "avunu", "kaadu", "emiti", "ela",
        "chala", "mee", "naaku", "ikkada", "akkada", "namaskaram"
    ]
    marathi_words = [
        "mala", "tumhala", "ahe", "nahi", "kay", "kasa",
        "changle", "ya", "hoil", "sangaa", "mhanun", "aahe",
        "namaskar", "kasa", "bara", "hoy", "pahije"
    ]
    gujarati_words = [
        "mane", "tamne", "che", "nathi", "shu", "kem",
        "saaru", "aavo", "thay", "karo", "etle", "bhai",
        "kem cho", "majama", "haa", "na", "aapne"
    ]
    bengali_words = [
        "ami", "apni", "ache", "nei", "ki", "kemon",
        "bhalo", "esho", "hobe", "bolo", "tai", "namaskar",
        "kothay", "ekhane", "okhane", "dhonnobad"
    ]
    hindi_words = [
        "hai", "hain", "kya", "nahi", "mujhe", "kaise", "karna", "chahiye",
        "abhi", "bahut", "acha", "theek", "bhai", "yaar", "mera", "mere",
        "koi", "kuch", "woh", "yeh", "aap", "tum", "hum", "sab",
        "paisa", "paise", "kaam", "log", "bolo", "batao", "samjha",
        "broker", "milta", "deta", "leta", "jaata", "aata",
        "haan", "hoon", "milega", "karega", "karenge", "dekho"
    ]
    english_words = [
        "the", "is", "are", "what", "how", "yes", "no", "please",
        "interested", "tell", "about", "already", "have", "want",
        "think", "know", "need", "give", "take", "call", "send",
        "me", "more", "can", "will", "would", "should"
    ]
    
    import re
    text_lower = [re.sub(r'[^\w]', '', w) for w in text.lower().split()]
    text_lower = [w for w in text_lower if w]
    total_words = len(text_lower)
    if total_words == 0:
        return "english"
    
    # Check Devanagari script (could be Hindi or Marathi)
    if any(c in hindi_chars for c in text):
        # Check for Marathi-specific words
        marathi_count = sum(1 for w in text_lower if w in marathi_words)
        if marathi_count >= 2:
            return "marathi"
        return "hindi"
    
    # Romanized detection - count matches
    lang_scores = {
        "tamil": sum(1 for w in text_lower if w in tamil_words),
        "telugu": sum(1 for w in text_lower if w in telugu_words),
        "marathi": sum(1 for w in text_lower if w in marathi_words),
        "gujarati": sum(1 for w in text_lower if w in gujarati_words),
        "bengali": sum(1 for w in text_lower if w in bengali_words),
        "hindi": sum(1 for w in text_lower if w in hindi_words),
        "english": sum(1 for w in text_lower if w in english_words),
    }
    
    best_lang = max(lang_scores, key=lang_scores.get)
    best_score = lang_scores[best_lang]
    
    if best_score == 0:
        return "english"
    
    # If a regional language (non-Hindi, non-English) scores highest, use it
    if best_lang not in ("hindi", "english") and best_score >= 2:
        return best_lang
    
    # Check for Hinglish (mix of Hindi + English)
    if lang_scores["hindi"] > 0 and lang_scores["english"] > 0:
        hindi_ratio = lang_scores["hindi"] / total_words
        english_ratio = lang_scores["english"] / total_words
        if hindi_ratio > 0.15 and english_ratio > 0.15:
            return "hinglish"
    
    if best_score / total_words > 0.2:
        return best_lang
    
    return "english"


async def generate_response(
    lead_name: str,
    lead_language: str,
    conversation_history: list[dict],
    user_message: str,
    previous_context: dict = None
) -> dict:
    """
    Generate AI response for the conversation.
    
    Returns: {"reply": str, "language_detected": str, "should_end": bool}
    """
    # Detect language from user's message
    detected_lang = detect_language(user_message)
    
    # Use lead's configured language as default; only switch if user
    # is clearly speaking in a different regional language (not english)
    # This prevents "I want Bengali" (typed in English) from switching to English
    effective_lang = lead_language
    if detected_lang != "english" and detected_lang != lead_language:
        # User is speaking in a specific non-English language — switch to it
        effective_lang = detected_lang
    elif detected_lang == "english" and lead_language == "english":
        effective_lang = "english"
    
    # Build messages for LLM
    system_msg = build_system_message(lead_name, effective_lang)
    
    # Add multi-turn memory from previous calls
    if previous_context:
        system_msg += f"\n\nPREVIOUS CALL CONTEXT (use this to personalize your approach):\n"
        system_msg += f"- Last call status: {previous_context.get('interest_score', 'unknown')}\n"
        system_msg += f"- Objections raised before: {previous_context.get('objections_raised', [])}\n"
        system_msg += f"- Topics already covered: {previous_context.get('topics_covered', [])}\n"
        system_msg += f"- Previous summary: {previous_context.get('summary_text', 'N/A')}\n"
        system_msg += "IMPORTANT: Reference the previous conversation naturally. Don't repeat the same pitch — build on what was discussed before."
    
    messages = [{"role": "system", "content": system_msg}]
    
    # Add conversation history
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current message
    messages.append({"role": "user", "content": user_message})
    
    # Check if conversation should end
    end_signals = [
        "bye", "goodbye", "thanks bye", "ok bye", "not interested", 
        "don't call again", "stop calling", "mat karo call", "band karo",
        "chal bye", "rakhta hu", "rakh raha hu"
    ]
    should_end = any(signal in user_message.lower() for signal in end_signals)
    
    # Call Groq
    groq_client = get_client()
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
        top_p=0.9,
    )
    
    reply = response.choices[0].message.content.strip()
    
    return {
        "reply": reply,
        "language_detected": effective_lang,
        "should_end": should_end
    }


async def generate_opening(lead_name: str, lead_language: str, previous_context: dict = None) -> str:
    """Generate the opening message for a new call. Uses previous context for follow-ups."""
    system_msg = build_system_message(lead_name, lead_language)
    
    if previous_context:
        # This is a follow-up call
        prev_status = previous_context.get("interest_score", "unknown")
        prev_summary = previous_context.get("summary_text", "")
        if lead_language == "hindi":
            opener_prompt = f"Generate a natural follow-up call opening for {lead_name} in Hindi (romanized). This is NOT the first call. Previous call summary: {prev_summary}. Reference the previous conversation naturally. Keep it to 3-4 sentences."
        elif lead_language == "hinglish":
            opener_prompt = f"Generate a natural follow-up call opening for {lead_name} in Hinglish. This is NOT the first call. Previous call summary: {prev_summary}. Reference the previous conversation naturally. Keep it to 3-4 sentences."
        else:
            opener_prompt = f"Generate a natural follow-up call opening for {lead_name} in English. This is NOT the first call. Previous call summary: {prev_summary}. Reference the previous conversation naturally. Keep it to 3-4 sentences."
    else:
        if lead_language == "hindi":
            opener_prompt = f"Generate a natural opening for a call to {lead_name} in Hindi (romanized). Use the hook: zero joining fee, 100% brokerage share, daily payouts. Keep it to 3-4 sentences. Be warm and conversational."
        elif lead_language == "hinglish":
            opener_prompt = f"Generate a natural opening for a call to {lead_name} in Hinglish. Use the hook: zero joining fee, 100% brokerage share, daily payouts. Keep it to 3-4 sentences. Be warm and conversational."
        else:
            opener_prompt = f"Generate a natural opening for a call to {lead_name} in English. Use the hook: zero joining fee, 100% brokerage share, daily payouts. Keep it to 3-4 sentences. Be warm and conversational."
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": opener_prompt}
    ]
    
    groq_client = get_client()
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.8,
        max_tokens=200,
    )
    
    return response.choices[0].message.content.strip()


async def generate_summary(lead_name: str, messages: list[dict]) -> str:
    """Generate a post-call summary using LLM."""
    conversation_text = "\n".join(
        f"{'Agent' if m['role'] == 'assistant' else 'Lead'}: {m['content']}" 
        for m in messages
    )
    
    prompt = f"""Summarize this sales call with {lead_name} in 3-4 bullet points. 
Include: what was discussed, objections raised, how they were handled, and the lead's overall sentiment.
Keep it concise — this is for an RM to quickly review.

CONVERSATION:
{conversation_text}

SUMMARY:"""
    
    groq_client = get_client()
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a sales call summarizer. Be concise and actionable."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=250,
    )
    
    return response.choices[0].message.content.strip()
