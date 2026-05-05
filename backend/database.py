"""SQLite database layer for leads, conversations, and summaries."""
import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "rupeezy.db"


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                language TEXT DEFAULT 'english',
                status TEXT DEFAULT 'new',
                score INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                messages TEXT DEFAULT '[]',
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS call_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                conversation_id INTEGER NOT NULL,
                duration_seconds INTEGER,
                messages_count INTEGER,
                language_used TEXT,
                objections_raised TEXT DEFAULT '[]',
                topics_covered TEXT DEFAULT '[]',
                interest_score TEXT,
                score_numeric INTEGER,
                recommended_action TEXT,
                summary_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            )
        """)
        await db.commit()


# --- Lead operations ---

async def create_lead(name: str, phone: str, language: str = "english", source: str = "manual") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO leads (name, phone, language, source) VALUES (?, ?, ?, ?)",
            (name, phone, language, source)
        )
        await db.commit()
        return cursor.lastrowid


async def get_lead(lead_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_leads() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM leads ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_lead_status(lead_id: int, status: str, score: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if score is not None:
            await db.execute(
                "UPDATE leads SET status = ?, score = ? WHERE id = ?",
                (status, score, lead_id)
            )
        else:
            await db.execute(
                "UPDATE leads SET status = ? WHERE id = ?",
                (status, lead_id)
            )
        await db.commit()


async def batch_create_leads(leads: list[dict]) -> list[int]:
    ids = []
    async with aiosqlite.connect(DB_PATH) as db:
        for lead in leads:
            cursor = await db.execute(
                "INSERT INTO leads (name, phone, language, source) VALUES (?, ?, ?, ?)",
                (lead["name"], lead["phone"], lead.get("language", "english"), lead.get("source", "batch"))
            )
            ids.append(cursor.lastrowid)
        await db.commit()
    return ids


# --- Conversation operations ---

async def create_conversation(lead_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO conversations (lead_id) VALUES (?)",
            (lead_id,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_conversation(lead_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE lead_id = ? AND is_active = 1 ORDER BY started_at DESC LIMIT 1",
            (lead_id,)
        )
        row = await cursor.fetchone()
        if row:
            result = dict(row)
            result["messages"] = json.loads(result["messages"])
            return result
        return None


async def update_conversation_messages(conv_id: int, messages: list[dict]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE conversations SET messages = ? WHERE id = ?",
            (json.dumps(messages), conv_id)
        )
        await db.commit()


async def end_conversation(conv_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE conversations SET is_active = 0, ended_at = ? WHERE id = ?",
            (datetime.now().isoformat(), conv_id)
        )
        await db.commit()


async def get_conversation(conv_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,))
        row = await cursor.fetchone()
        if row:
            result = dict(row)
            result["messages"] = json.loads(result["messages"])
            return result
        return None


# --- Summary operations ---

async def create_summary(summary: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO call_summaries 
            (lead_id, conversation_id, duration_seconds, messages_count, language_used,
             objections_raised, topics_covered, interest_score, score_numeric, 
             recommended_action, summary_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            summary["lead_id"], summary["conversation_id"],
            summary["duration_seconds"], summary["messages_count"],
            summary["language_used"],
            json.dumps(summary["objections_raised"]),
            json.dumps(summary["topics_covered"]),
            summary["interest_score"], summary["score_numeric"],
            summary["recommended_action"], summary["summary_text"]
        ))
        await db.commit()
        return cursor.lastrowid


async def get_all_summaries() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT cs.*, l.name as lead_name, l.phone as lead_phone 
            FROM call_summaries cs 
            JOIN leads l ON cs.lead_id = l.id 
            ORDER BY cs.created_at DESC
        """)
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["objections_raised"] = json.loads(d["objections_raised"])
            d["topics_covered"] = json.loads(d["topics_covered"])
            results.append(d)
        return results


async def get_dashboard_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM leads")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM leads WHERE status != 'new'")
        contacted = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM leads WHERE status = 'hot'")
        hot = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM leads WHERE status = 'warm'")
        warm = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM leads WHERE status = 'cold'")
        cold = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT COUNT(*) FROM leads WHERE status = 'converted'")
        converted = (await cursor.fetchone())[0]

        cursor = await db.execute("SELECT AVG(score) FROM leads WHERE score > 0")
        avg_score = (await cursor.fetchone())[0] or 0

        conversion_rate = (hot + converted) / total * 100 if total > 0 else 0

        return {
            "total_leads": total,
            "contacted": contacted,
            "hot": hot,
            "warm": warm,
            "cold": cold,
            "converted": converted,
            "avg_score": round(avg_score, 1),
            "conversion_rate": round(conversion_rate, 1)
        }


# --- Transcript & multi-turn memory ---

async def get_all_conversations_for_lead(lead_id: int) -> list[dict]:
    """Get all conversations (including ended) for a lead — for transcript view."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM conversations WHERE lead_id = ? ORDER BY started_at DESC",
            (lead_id,)
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["messages"] = json.loads(d["messages"])
            results.append(d)
        return results


async def get_previous_summary(lead_id: int) -> dict | None:
    """Get the most recent call summary for a lead — used for multi-turn memory."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM call_summaries WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1",
            (lead_id,)
        )
        row = await cursor.fetchone()
        if row:
            d = dict(row)
            d["objections_raised"] = json.loads(d["objections_raised"])
            d["topics_covered"] = json.loads(d["topics_covered"])
            return d
        return None


# --- WhatsApp log ---

async def log_whatsapp(lead_id: int, message: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO whatsapp_log (lead_id, message) VALUES (?, ?)",
            (lead_id, message)
        )
        await db.commit()


async def get_whatsapp_logs() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT wl.*, l.name as lead_name, l.phone as lead_phone 
            FROM whatsapp_log wl 
            JOIN leads l ON wl.lead_id = l.id 
            ORDER BY wl.sent_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
