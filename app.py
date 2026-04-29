from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests, os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# This gets auto-patched to localhost:8000 by Cell 5
LLM_URL = "http://localhost:8000/v1/chat/completions"

# ─────────────────────────────────────────────
#  CHARACTER PROMPTS
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
# ─────────────────────────────────────────────

memory = {
    "Aisha": {"history": [], "facts": {}},
    "Riya":  {"history": [], "facts": {}},
    "Neha":  {"history": [], "facts": {}},
    "Sara":  {"history": [], "facts": {}}
}

MAX_HISTORY = 10

# ─────────────────────────────────────────────
#  FACT EXTRACTION
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
    lower = text.lower()
    for pattern, key in FACT_PATTERNS:
        match = re.search(pattern, lower)
        if match:
            facts_dict[key] = match.group(1).strip().title()

def build_memory_context(facts_dict):
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

def build_continuity_note(history):
    if len(history) < 4:
        return ""
    recent_user_msgs = [m["content"] for m in history if m["role"] == "user"][-2:]
    topics = " / ".join(recent_user_msgs)
    return f"\nRecent conversation topics: {topics[:200]}"

def trim_history(history, max_turns=MAX_HISTORY):
    if len(history) > max_turns:
        history[:] = history[:2] + history[-(max_turns - 2):]

# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_msg  = data.get("message", "").strip()
    character = data.get("character", "Aisha")
    
    # Maintain compatibility with provided character-based memory
    if character not in memory:
        return jsonify({"reply": "Unknown character."}), 400

    char_mem = memory[character]
    history  = char_mem["history"]
    facts    = char_mem["facts"]

    extract_facts(user_msg, facts)

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

    history.append({"role": "user", "content": user_msg})
    trim_history(history)

    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response = requests.post(LLM_URL, json={
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.8,
            "repeat_penalty": 1.05,
            "stream": False
        }, timeout=60)
        
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply, "history": history})

    except Exception as e:
        return jsonify({"reply": "Model is loading, please try again in a moment! 🔄", "history": history})

@app.route("/reset/<character>", methods=["POST"])
def reset_memory(character):
    if character in memory:
        memory[character] = {"history": [], "facts": {}}
        return jsonify({"status": f"{character}'s memory cleared."})
    return jsonify({"status": "Character not found."}), 404

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
    app.run(host="0.0.0.0", port=5000, debug=False)
