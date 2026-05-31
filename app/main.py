# =========================================================
# 📦 IMPORTS
# =========================================================
from groq import Groq
import os
from dotenv import load_dotenv

from rag.rag_pipeline import rag_pipeline
from classifier import emotion_inference, language_inference, intent_classifier
from rag.crisis_handler import handle_self_harm


# =========================================================
# INIT
# =========================================================
load_dotenv(dotenv_path="config/.env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# language + emotion models (shared globally)
language_model = language_inference.LanguagePredictor()
emotion_model = emotion_inference.EmotionClassifier()

# =========================================================
# INTENT SETUP
# =========================================================
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

# =========================================================
# ROUTING CONFIG
# =========================================================
RAG_INTENTS = {
    "asking_mental_health_question",
    "self_harm_intent"
}

LOCALIZED_INTENTS = {
    "greeting",
    "goodbye",
    "gratitude",
    "out_of_scope",
    "unsafe_query"
}

# =========================================================
# MAIN LOOP
# =========================================================
print("🤖 Chatbot running (type exit)\n")

while True:
    msg = input("You: ")

    if msg.lower() in ["exit", "quit"]:
        break

    # ---------------------------------------------
    # 1. SHARED PREPROCESSING (NO DUPLICATION)
    # ---------------------------------------------
    language = language_model.predict(msg)
    language = str(language)

    emotion_result = emotion_model.predict(msg)
    emotion = emotion_result["emotion"]

    # ---------------------------------------------
    # 2. INTENT CLASSIFICATION
    # ---------------------------------------------
    intent_data = engine.classify_intent(
        user_message=msg,
        language=language   # IMPORTANT: injected, not recomputed
    )

    intent_data = engine.apply_confidence_threshold(intent_data)

    intent = intent_data["intent"]
    print(intent)

    # ---------------------------------------------
    # 3. ROUTING LOGIC (CORE DECISION POINT)
    # ---------------------------------------------
    if intent == "self_harm_intent":

        response = handle_self_harm(msg, language)
    
    elif intent == "asking_mental_health_question":

        response = rag_pipeline(
            query=msg,
            chat_history="",
            language=language,
            emotion=emotion,
            return_metadata=False
        )

    else:

        response = engine.build_response(
            intent=intent,
            language=language
        )

    # ---------------------------------------------
    # 4. OUTPUT
    # ---------------------------------------------
    print("\nBot:", response, "\n")