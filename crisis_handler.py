from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def build_crisis_prompt(user_message, language):

    return f"""
You are a crisis support assistant helping a person who may be experiencing thoughts of self-harm or severe emotional distress.

IMPORTANT BEHAVIOR RULES:
- Be calm, gentle, and non-judgmental
- Do NOT provide any methods or details related to self-harm
- Do NOT validate self-harm as an option
- Do NOT analyze deeply or philosophize
- Focus only on immediate emotional support and stabilization
- Encourage reaching out to real-world support when appropriate

Your response MUST include:

1. Acknowledge their emotional pain (empathetic validation)
2. A gentle statement of concern for their safety
3. Encourage reaching out to someone they trust or a local support service
4. Offer a simple grounding technique (breathing or sensory grounding)
5. Keep language simple, warm, and supportive

Detected Language:
{language}

User Message:
{user_message}

Respond in the SAME language.
"""


def handle_self_harm(user_message, language):
    prompt = build_crisis_prompt(user_message, language)

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": "You are a crisis support assistant trained to respond to self-harm related distress. You must be calm, supportive, and prioritize safety."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=400
    )

    return response.choices[0].message.content