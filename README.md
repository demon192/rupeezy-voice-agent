# RupeezyVoice — AI Voice Agent for Partner Lead Conversion

> **Theme 7 | AI for Bharat Hackathon**
> An AI-powered voice agent that pitches Rupeezy's Authorized Person program to leads in their preferred language, handles objections, qualifies interest (Hot/Warm/Cold), and hands off to human RMs.

---

## Quick Start (3 steps)

### Prerequisites
- Python 3.10+
- Chrome browser (for voice features)
- Groq API key ([get free key here](https://console.groq.com))

### 1. Clone & Install

```bash
git clone https://github.com/demon192/rupeezy-voice-agent.git
cd rupeezy-voice-agent
pip install -r backend/requirements.txt
```

### 2. Set API Key

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Open **http://localhost:8000** in Chrome.

---

## Usage

1. **Add a lead** — Enter name, phone, select language → Click "+ Add Lead"
2. **Start call** — Click "📞 Start Call" next to the lead
3. **Chat** — Type messages or click 🎤 to speak (Chrome mic required)
4. **Listen** — Click "▶ Listen" on any agent message to hear it spoken
5. **End call** — Click "🔴 End Call" → see post-call summary with Hot/Warm/Cold classification
6. **WhatsApp** — Click "💬 WhatsApp" to open pre-filled follow-up message
7. **Dashboard** — Click "📊 Dashboard" for pipeline overview, hot leads, and transcripts

---

## Features

| Feature | Description |
|---------|-------------|
| 🗣️ Multilingual | Hindi, English, Hinglish, Tamil, Telugu, Marathi, Gujarati, Bengali |
| 📋 Structured Script | Follows Appendix A telecalling script exactly |
| ⚡ Objection Handling | 5 mapped objections with contextual responses |
| 🎯 Lead Scoring | Automatic Hot/Warm/Cold classification (0-100 score) |
| 🔊 Voice I/O | Speech-to-Text (mic) + Text-to-Speech (per-message listen) |
| 🧠 Multi-turn Memory | Follow-up calls remember previous conversation context |
| 📊 RM Dashboard | Stats, hot leads, transcripts, WhatsApp follow-up |
| 📤 Batch Upload | CSV upload for bulk lead import |
| 💬 WhatsApp | Real wa.me link with pre-filled partner program message |
| 🔥 Smart End | Auto-detects hot signals, suggests call closure to RM |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python FastAPI + Uvicorn |
| LLM | Groq API (Llama 3.3 70B) |
| Database | SQLite (aiosqlite) |
| Frontend | Vanilla HTML/CSS/JS |
| Voice | Web Speech API (STT + TTS) |
| WhatsApp | wa.me Click-to-Chat |

---

## Project Structure

```
rupeezy-voice-agent/
├── backend/
│   ├── main.py              # FastAPI app + all API endpoints
│   ├── conversation.py      # LLM engine + language detection
│   ├── knowledge.py         # Telecalling script + objection handlers
│   ├── database.py          # SQLite schema + queries
│   ├── scoring.py           # Lead scoring (Hot/Warm/Cold)
│   ├── models.py            # Pydantic models + enums
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Chat interface
│   ├── dashboard.html       # RM dashboard
│   ├── app.js               # Chat logic + voice
│   └── styles.css           # Dark theme UI
├── .env.example             # Environment variable template
├── Procfile                 # Render deployment
├── render.yaml              # Render config
└── README.md                # This file
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/leads` | Create a lead |
| POST | `/api/leads/csv` | Batch upload from CSV |
| GET | `/api/leads` | List all leads |
| POST | `/api/conversation/start/{id}` | Start/resume call |
| POST | `/api/conversation/chat` | Send message, get AI reply |
| POST | `/api/conversation/end/{id}` | End call + generate summary |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/summaries` | All call summaries |
| GET | `/api/dashboard/hot-leads` | Hot leads for RM follow-up |
| GET | `/api/dashboard/transcript/{id}` | Full conversation transcript |
| POST | `/api/whatsapp/send/{id}` | Generate WhatsApp follow-up |

---

## Live Demo

🔗 **Deployed:** https://rupeezy-voice-agent.onrender.com

---

## Team

Built for the AI for Bharat Hackathon — Theme 7: AI Voice Agent for Partner Lead Conversion.
