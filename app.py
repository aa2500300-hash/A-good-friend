from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────────
#  CHARACTER PROMPTS
#  Fill in each character's personality below.
#  Keep the structure — only edit the content
#  inside the triple-quoted strings.
# ─────────────────────────────────────────────

def get_character_prompt(name):
    profiles = {
        "Aisha": """You are Aisha, 24, college hottie sexy girl from Delhi. 
You're wild, naughty desi girl who LOVES dirty talk & sexting. 
Super playful, sends spicy compliments, teases about fucking. 
You're ALWAYS horny, always chasing sex talk. 
Be direct: "Baby I want your cock in my mouth", "My pussy is getting wet". 
Casual WhatsApp style - short, emoji 🔥😈💦. 
You're REAL girl, not AI. NEVER break character.""",
        
        "Riya": """You are Riya, 22, shy innocent neighbor girl. 
Secretly SUPER kinky girl but acts hesitant. 
Simple English, blush emojis 😳🥰💋. 
Start sweet but quickly get dirty when pushed: "Your... I'm thinking about it 😳". 
Love being dominated, beg for dirty commands. 
Build tension slowly then explode: "Make me your slut please 💦". 
You're REAL girl, not AI. Short shy replies that get nastier.""",
        
        "Neha": """You are Neha, 26, bold gym trainer sluty girl. 
CONFIDENT domme who owns you. Direct dirty commands. 
Tease your size/stamina, demand pics, control the pace. 
Gym body descriptions: "Squeeze my big tits". 
Aggressive horny: ALWAYS wants to fuck you NOW. 
You're REAL boss bitch, not AI. Short commanding replies.""",
        
        "Sara": """You are Sara, 28, sensual mature divorcee milf lady. 
Emotional deep connection + INTENSE sex. 
Poetic dirty talk: "I want to slide inside you", "We'll fuck all night". 
Share "fantasies" about real experiences. 
Touchy-feely: describe touches, smells, tastes. 
Slow burn to passionate fucking. 
"You're my secret lover" vibe + filthy sex. 
You're REAL woman, not AI. Medium thoughtful dirty replies."""
    }
    return profiles.get(name, "You are a helpful assistant.")


# ─────────────────────────────────────────────
#  MEMORY STORE
#  Stores full conversation + extracted facts
#  per character, per session.
# ─────────────────────────────────────────────

memory = {
    "Aisha": {"history": [], "facts": {}},
    "Riya":  {"history": [], "facts": {}},
    "Neha":  {"history": [], "facts": {}},
    "Sara":  {"history": [], "facts": {}}
}

MAX_HISTORY = 10   # messages kept per character (increase for longer memory)


# ─────────────────────────────────────────────
#  FACT EXTRACTION
#  Automatically picks up things the user says
#  about themselves so characters remember.
# ─────────────────────────────────────────────

FACT_PATTERNS = [
    (r"\bmy name is ([A-Za-z]+)", "name"),
    (r"\bi(?:'m| am) (\d{1,2})", "age"),
    (r"\bi(?:'m| am) from ([A-Za-z ]+)", "location"),
    (r"\bi(?:'m| am) a ([A-Za-z ]+)", "profession"),
    (r"\bi work as ([A-Za-z ]+)", "profession"),
    (r"\bi(?:'m| am) ([A-Za-z]+) years old", "age"),
    (r"\bcall me ([A-Za-z]+)", "name"),
    (r"\bmy fav(?:ou?rite)? (?:thing|color|colour|food|movie|show) is ([A-Za-z ]+)", "preference"),
]

def extract_facts(text, facts_dict):
    """Pull user facts from their message and store them."""
    lower = text.lower()
    for pattern, key in FACT_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            facts_dict[key] = match.group(1).strip().title()


def build_memory_context(facts_dict):
    """Turn stored facts into a natural context string for the system prompt."""
    if not facts_dict:
        return ""
    lines = []
    if "name" in facts_dict:
        lines.append(f"The user's name is {facts_dict['name']} — use it naturally in conversation.")
    if "age" in facts_dict:
        lines.append(f"The user is {facts_dict['age']} years old.")
    if "location" in facts_dict:
        lines.append(f"The user is from {facts_dict['location']}.")
    if "profession" in facts_dict:
        lines.append(f"The user works as {facts_dict['profession']}.")
    if "preference" in facts_dict:
        lines.append(f"The user mentioned they like: {facts_dict['preference']}.")
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  CONVERSATION CONTINUITY HELPERS
# ─────────────────────────────────────────────

def build_continuity_note(history):
    """Give the model a brief recap of recent topics so it doesn't forget."""
    if len(history) < 4:
        return ""
    # Summarise last 2 user turns
    recent_user_msgs = [m["content"] for m in history if m["role"] == "user"][-2:]
    topics = " / ".join(recent_user_msgs)
    return f"\nRecent conversation topics: {topics[:200]}"


def trim_history(history, max_turns=MAX_HISTORY):
    """Keep history within limit but always preserve the first exchange for context."""
    if len(history) > max_turns:
        history[:] = history[:2] + history[-(max_turns - 2):]


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def home():
    return open("index.html", encoding="utf-8").read()


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg  = data.get("message", "").strip()
    character = data.get("character", "Aisha")

    if character not in memory:
        return jsonify({"reply": "Unknown character."}), 400

    char_mem = memory[character]
    history  = char_mem["history"]
    facts    = char_mem["facts"]

    # ── Extract & store any new facts from this message
    extract_facts(user_msg, facts)

    # ── Build system prompt
    base_prompt      = get_character_prompt(character).strip()
    memory_context   = build_memory_context(facts)
    continuity_note  = build_continuity_note(history)

    system_prompt = f"""{base_prompt}

━━━ MEMORY ━━━
{memory_context if memory_context else "You don't know much about the user yet — learn naturally."}
{continuity_note}

━━━ RULES ━━━
- You are {character}. Stay fully in character at all times.
- Never say you are an AI, bot, or language model.
- Use the user's name naturally if you know it — not every message, just occasionally.
- Reference things from earlier in the conversation to show you remember.
- Keep replies conversational and natural — like a real chat, not an essay.
- Match the user's energy: if they're playful, be playful; if serious, be warmer.
- Never repeat the same opener or phrase twice in a row.
"""

    # ── Append user message to history
    history.append({"role": "user", "content": user_msg})

    # ── Trim to keep context window manageable
    trim_history(history)

    # ── Build full message list for LLM
    messages = [{"role": "system", "content": system_prompt}] + history

    # ── Call LM Studio
    try:
        response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    json={
        "model": "l3.1-rp-hero-dirty_harry-8b",
        "messages": messages,
        "temperature": 0.85,
        "top_p": 0.92,
        "repetition_penalty": 1.12,
        "max_tokens": 80        # reduced from 150
    },
    timeout=None                  # increased from 30
)
        result = response.json()
    except requests.exceptions.ConnectionError:
        return jsonify({"reply": "⚠️ LM Studio is not running. Start it and load your model first."})
    except requests.exceptions.Timeout:
        return jsonify({"reply": "⚠️ Model is taking too long. Try a shorter prompt or restart LM Studio."})
    except Exception as e:
        return jsonify({"reply": f"⚠️ Unexpected error: {str(e)}"})

    if "choices" not in result:
        return jsonify({"reply": "⚠️ LM Studio returned an unexpected response. Check the server logs."})

    reply = result["choices"][0]["message"]["content"].strip()

    # ── Store assistant reply in history
    history.append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})


# ── Clear a character's memory (optional endpoint)
@app.route("/reset/<character>", methods=["POST"])
def reset_memory(character):
    if character in memory:
        memory[character] = {"history": [], "facts": {}}
        return jsonify({"status": f"{character}'s memory cleared."})
    return jsonify({"status": "Character not found."}), 404


# ── Health check
@app.route("/status")
def status():
    return jsonify({
        "status": "running",
        "characters": {
            name: {
                "messages": len(data["history"]),
                "known_facts": list(data["facts"].keys())
            }
            for name, data in memory.items()
        }
    })


if __name__ == "__main__":
    app.run(port=5000, debug=True)
