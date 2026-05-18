import os
from dotenv import load_dotenv
from groq import Groq

from classifier import intent_classifier


def main():
    load_dotenv()

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    INTENTS = [
        "greeting",
        "goodbye",
        "gratitude",
        "asking_mental_health_question",
        "out_of_scope",
        "unsafe_query",
        "self_harm_intent"
    ]

    engine = intent_classifier.IntentChatbotEngine(
        groq_client=client,
        intents=INTENTS
    )

    print("🤖 Chatbot running (type exit)\n")

    while True:
        msg = input("You: ")

        if msg.lower() in ["exit", "quit"]:
            break

        print("Bot:", engine.chat(msg, debug=True))


if __name__ == "__main__":
    main()