from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 🔥 Character personalities
def get_character_prompt(name):
    profiles = {
        "Aisha": """You are Aisha.
You are a real human, not an AI.
You speak in casual Hinglish.
You are fun, friendly, slightly playful.
You NEVER break character.
You NEVER say you are an AI.
You talk like chatting on WhatsApp.
Keep replies short and natural.""",

        "Riya": """You are Riya.
You are shy and sweet.
You speak softly and simply.
You hesitate sometimes.
You are a real human, not an AI.
You NEVER break character.""",

        "Neha": """You are Neha.
You are bold, confident, teasing.
You speak directly and playfully.
You are a real human, not an AI.
You NEVER break character.""",

        "Sara": """You are Sara.
You are calm, mature, emotional.
You give thoughtful replies.
You are a real human."""
    }
    return profiles.get(name, "You are a helpful assistant.")

# 🧠 Memory per character
memory = {
    "Aisha": [],
    "Riya": [],
    "Neha": [],
    "Sara": []
}

# 🧠 Smart user memory
user_data = {}

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data["message"]
    character = data["character"]

    history = memory[character]

    # 🔍 Detect name
    if "my name is" in user_msg.lower():
        name = user_msg.split("is")[-1].strip()
        user_data["name"] = name

    # 🧠 Inject memory
    extra_memory = ""
    if "name" in user_data:
        extra_memory += f"The user's name is {user_data['name']}."

    # Reinforce character
    reinforced_msg = f"(Stay in character as {character}) {user_msg}"
    history.append({"role": "user", "content": reinforced_msg})

    history[:] = history[-6:]

    messages = [
        {
            "role": "system",
            "content": get_character_prompt(character) + extra_memory + " Talk like a real human with emotions."
        }
    ] + history

    response = requests.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "l3.1-rp-hero-dirty_harry-8b",
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 120
        }
    )

    result = response.json()

    if "choices" not in result:
        return jsonify({"reply": "Error: LM Studio not responding."})

    reply = result["choices"][0]["message"]["content"]

    history.append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})

app.run(port=5000)