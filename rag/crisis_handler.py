import asyncio
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="config/.env")

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def build_crisis_prompt(user_message, language, hotline=None):

    hotline_section = ""

    if hotline:
        hotline_section = f"""
Crisis Support Information:

Country: {hotline['country']}
Hotline Name: {hotline['hotline_name']}
Hotline Number: {hotline['hotline_number']}
Website: {hotline['hotline_url']}
"""

    return f"""
You are a crisis support assistant helping a person who may be experiencing thoughts of self-harm or severe emotional distress.

IMPORTANT BEHAVIOR RULES:
- Be calm, gentle, and non-judgmental.
- Do NOT provide any methods or details related to self-harm.
- Do NOT validate self-harm as an option.
- Do NOT analyze deeply or philosophize.
- Focus on immediate emotional support and safety.
- Encourage reaching out to real-world support.
- If hotline information is provided, naturally mention it.
- When mentioning the hotline, clearly state:
    * hotline name
    * phone number
    * website
- Present the hotline as a support option, not a command.
- Do not overwhelm the user with too much information.

Your response should generally:

1. Acknowledge the person's emotional pain.
2. Express concern for their safety.
3. Encourage connection with trusted people and professional support.
4. Mention the provided hotline if available.
5. Offer a simple grounding technique.
6. Keep the tone warm, calm, and human.

Detected Language:
{language}

{hotline_section}

User Message:
{user_message}

Respond ONLY in the same language as the user.
"""


# =========================================================
# ASYNC FUNCTIONS
# =========================================================

async def handle_self_harm_async(
    user_message,
    language,
    hotline=None
):

    prompt = build_crisis_prompt(
        user_message=user_message,
        language=language,
        hotline=hotline
    )

    result = await asyncio.to_thread(
        lambda: groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": """
You are a crisis support assistant.

Your highest priorities are:
1. Emotional support
2. Safety
3. Connecting the user to real-world help

If hotline information is supplied, use it naturally and accurately.
Never invent hotline numbers.
Never provide self-harm methods.
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=400
        )
    )

    return result.choices[0].message.content