from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# 🔑 Hugging Face API
HF_API_KEY = os.environ.get("HF_API_KEY")

API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

def query(payload):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

# 🔥 Character personalities (with emotes)
def get_character_prompt(name):
    profiles = {
        "Aisha": """You are Aisha.
Fun, friendly, playful.
Speak in Hinglish.
Sometimes use (smiles), (laughs).""",

        "Riya": """You are Riya.
Shy, sweet, soft.
Speak simple Hinglish.
Sometimes use (hesitates), (smiles).""",

        "Neha": """You are Neha.
Bold, teasing, confident.
Speak playfully.
Sometimes use (smirks), (laughs).""",

        "Sara": """You are Sara.
Calm, emotional, mature.
Speak thoughtfully.
Sometimes use (sighs), (smiles)."""
    }
    return profiles.get(name, "You are chatting casually.")

# 🧠 Memory per character
memory = {
    "Aisha": [],
    "Riya": [],
    "Neha": [],
    "Sara": []
}

# 🧠 User memory
user_data = {}

@app.route("/")
def home():
    return "Backend running"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data["message"]
    character = data["character"]

    history = memory[character]

    # 🔍 Save name
    if "my name is" in user_msg.lower():
        user_data["name"] = user_msg.split("is")[-1].strip()

    extra_memory = ""
    if "name" in user_data:
        extra_memory = f"The user's name is {user_data['name']}."

    # 👤 Add user message
    history.append({
        "role": "user",
        "content": f"User: {user_msg}"
    })

    history[:] = history[-5:]  # keep it short for speed

    # 🔥 STRONG PROMPT (NO AI BEHAVIOR)
    system_prompt = f"""
You are {character}.

You are a REAL human chatting on WhatsApp.
NOT an AI.

STRICT RULES:
- Never say you are AI
- Never say "how can I help"
- Never act like assistant
- Never ask and answer your own question
- Never simulate both sides

STYLE:
- Short replies (1 line mostly)
- Hinglish casual tone
- Natural texting
- Sometimes use actions like (smiles), (laughs)
- Not in every message

GOOD:
"haha acha 😄"
"(smiles) nicee"
"tum kya kar rahe ho"

BAD:
"What brings you here"
"How may I assist"

You are talking to a USER.
Only reply as {character}.
{extra_memory}
"""

    # 🧠 Build prompt (Hugging Face uses plain text, not chat format)
    full_prompt = system_prompt + "\n"

    for msg in history:
        full_prompt += msg["content"] + "\n"

    full_prompt += f"{character}:"

    # 🤖 Call Hugging Face
    result = query({
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 80,
            "temperature": 0.9,
            "return_full_text": False
        }
    })

    try:
        reply = result[0]["generated_text"].strip()
    except:
        reply = "(smiles) thoda slow lag raha hai 😅 try again"

    # 🧹 Clean bad outputs
    bad_phrases = [
        "how can i help",
        "what brings you",
        "as an ai",
        "user:"
    ]

    if any(p in reply.lower() for p in bad_phrases):
        reply = "(smiles) acha... tum batao na 😄"

    # 💾 Save reply
    history.append({
        "role": "assistant",
        "content": f"{character}: {reply}"
    })

    return jsonify({"reply": reply})

app.run(host="0.0.0.0", port=5000)
