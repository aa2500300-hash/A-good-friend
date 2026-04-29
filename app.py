from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from groq import Groq

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Character personalities
def get_character_prompt(name):
    profiles = {
        "Aisha": "You are Aisha, fun, flirty, playful girl. Speak casual Hinglish. Use emotions.",
        "Riya": "You are Riya, shy, cute, soft spoken. Use simple words.",
        "Neha": "You are Neha, bold, teasing, confident. Talk directly.",
        "Sara": "You are Sara, calm, emotional, mature."
    }
    return profiles.get(name, "You are a human chatting casually.")

# Memory
memory = {
    "Aisha": [],
    "Riya": [],
    "Neha": [],
    "Sara": []
}

@app.route("/")
def home():
    return "Server running"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_msg = data["message"]
    character = data["character"]

    history = memory[character]

    history.append({"role": "user", "content": user_msg})
    history[:] = history[-6:]

    system_prompt = f"""
You are {character}. You are a real human chatting casually.
- Never say you are AI
- Keep replies short
- Do NOT answer for user
"""

    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",  # ✅ WORKING MODEL
            messages=[
                {"role": "system", "content": system_prompt}
            ] + history,
            temperature=0.9,
            max_tokens=120
        )

        reply = response.choices[0].message.content

    except Exception as e:
        print("GROQ ERROR:", str(e))
        reply = "temporary server issue 😅 try again"

    history.append({"role": "assistant", "content": reply})

    return jsonify({"reply": reply})
if __name__ == "__main__":
    app.run()
