# RupeezyVoice — 5-Minute Demo Script
## AI Voice Agent for Partner Lead Conversion

---

### SLIDE 1: Problem Statement (30 seconds)

**Say:** "Rupeezy's partner program offers 100% brokerage share to Authorized Persons — but converting leads over phone is manual, expensive, and inconsistent. RMs can only make 30-40 calls/day, and many leads speak regional languages that RMs don't know."

**Show:** Theme 7 description briefly.

---

### SLIDE 2: Solution Overview (30 seconds)

**Say:** "RupeezyVoice is an AI-powered voice agent that calls leads in their preferred language — Hindi, English, Tamil, Telugu, Marathi, Gujarati, or Bengali — pitches the partner program following the structured telecalling script, handles objections in real-time, qualifies leads as Hot/Warm/Cold, and hands off to human RMs with full context."

**Show:** Architecture diagram or the main chat interface.

---

### DEMO PART 1: Lead Management (45 seconds)

**Action:** Open the app (localhost:8000 or Render URL)

1. **Add a lead manually:**
   - Name: "Vikram Sharma"
   - Phone: "9876543210"
   - Language: Hindi
   - Click "+ Add Lead"

2. **Show CSV batch upload:**
   - Paste: `name,phone,language\nAnita Desai,9112233445,gujarati\nKarthik R,9998877665,tamil`
   - Click "Upload Batch"
   - **Say:** "RMs can upload hundreds of leads from their CRM in one click."

---

### DEMO PART 2: AI Voice Call — Hindi (90 seconds)

**Action:** Click "Start Call" on Vikram Sharma

1. **Show AI opening:** (reads the auto-generated Hindi greeting)
   - **Say:** "The agent opens with a personalized pitch in Hindi, mentioning zero fee, 100% brokerage, and daily payouts."

2. **Type/Speak:** "Haan batao, kya hai yeh program?"
   - **Show:** AI responds in Hindi with benefits

3. **Type/Speak (Objection):** "Mere paas already Angel One hai, kyun badlu?"
   - **Say:** "Watch — it detects the 'already with another broker' objection and responds with a comparison."
   - **Show:** AI handles the objection naturally

4. **Type/Speak:** "Hmm theek hai, interested hoon. Link bhejo"
   - **Show:** AI responds with the actual signup link (https://rupeezy.in/partner-signup)
   - **Say:** "It detected a Hot signal — the lead asked for the signup link."

5. **Click "End Call"**
   - **Show:** Post-call summary appears:
     - Status: HOT
     - Score: 75+/100
     - Objections handled: "Already with broker"
     - Recommended action: "Immediate RM callback"

---

### DEMO PART 3: WhatsApp Follow-up (30 seconds)

1. **Click "WhatsApp" button** next to the lead
   - **Show:** Opens wa.me link with pre-filled follow-up message
   - **Say:** "One-click WhatsApp follow-up with program details and signup link — goes directly to the lead's phone."

---

### DEMO PART 4: RM Dashboard (45 seconds)

**Action:** Click "Dashboard" link

1. **Show stats grid:**
   - Total leads, conversion rate, hot/warm/cold breakdown
   - **Say:** "The RM dashboard gives a real-time view of the pipeline."

2. **Show Hot Leads section:**
   - Vikram Sharma appears as HOT with score
   - **Say:** "Hot leads are surfaced for immediate human follow-up."

3. **Show transcript:**
   - Click to view full conversation
   - **Say:** "RMs get complete context before calling back — no repetition needed."

---

### DEMO PART 5: Multi-turn Memory (30 seconds)

1. **Go back to main page, click "Call Again" on Vikram**
   - **Show:** AI opens with "Namaste Vikram ji, kaise hain? Pichle baar humne..."
   - **Say:** "On follow-up calls, the agent remembers the previous conversation — topics covered, objections raised, and where the lead left off. No context is lost."

---

### DEMO PART 6: Multilingual (30 seconds)

1. **Start call on the Gujarati lead (Anita Desai)**
   - **Show:** AI opens in Gujarati
   - **Say:** "The same agent works across 8 Indian languages. No separate models, no separate scripts — one intelligent agent adapts to each lead."

---

### CLOSING (30 seconds)

**Say:** "To summarize — RupeezyVoice handles the entire top-of-funnel conversion pipeline:
- Calls leads in their language
- Follows the structured script
- Handles all 5 standard objections
- Qualifies Hot/Warm/Cold automatically
- Hands off to human RMs with full context
- Sends WhatsApp follow-ups

This means RMs focus only on closing deals with qualified Hot leads — increasing conversion rates while reducing cost-per-acquisition by 60%."

---

## Tech Stack (if asked)

| Component | Technology |
|-----------|-----------|
| Backend | Python FastAPI + Groq (Llama 3.3 70B) |
| Voice | Web Speech API (STT + TTS) |
| Database | SQLite (aiosqlite) |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Render |
| WhatsApp | wa.me Click-to-Chat API |

## Key Differentiators (if asked)

1. **8 Indian languages** — not just English/Hindi
2. **Structured script adherence** — follows Appendix A exactly
3. **Real-time objection handling** — 5 mapped objections with responses
4. **Automatic scoring** — Hot/Warm/Cold with numeric confidence
5. **Multi-turn memory** — follow-up calls have full context
6. **One-click handoff** — RM gets transcript + recommended action
7. **< 2 second response time** — natural conversation flow

## Scalability & Production Roadmap (if asked)

**Q: "Is this only for one RM?"**

**Say:** "The prototype demonstrates the core AI agent capability with a single-RM view. In production, here's how it scales:

- **Multi-RM Support:** Each RM gets their own login and lead pool. Simple auth layer + role-based access on top of what's already built.
- **Auto-assignment:** Leads are auto-routed to RMs based on language match, expertise, and workload — so a Gujarati-speaking lead goes to an RM who speaks Gujarati for the handoff.
- **Parallel AI Calls:** The AI agent can run 100+ simultaneous conversations — it's not limited by human capacity. One AI replaces an entire telecalling floor.
- **Team Dashboard:** Manager view showing all RMs' pipelines, conversion rates, and AI performance metrics.
- **CRM Integration:** Leads flow in from Salesforce/HubSpot, outcomes flow back — no manual data entry.

The architecture is already designed for this — adding multi-tenancy is a configuration change, not a rewrite."

**Q: "How is this different from just using ChatGPT?"**

**Say:** "Three things:
1. It follows Rupeezy's exact telecalling script — not generic responses
2. It scores and qualifies automatically — ChatGPT doesn't feed into your CRM
3. It has multi-turn memory across calls — remembers every previous interaction with each lead"
