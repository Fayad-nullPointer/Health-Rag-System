import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Langchain & Qdrant
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain
from groq import Groq

# Custom Classifiers
# Ensure your PYTHONPATH encompasses the root directory so the classifier module imports correctly.
from classifier.intent_classifier import IntentChatbotEngine
from classifier.language_inference import LanguagePredictor
from classifier.emotion_inference import EmotionPredictor

load_dotenv()

# Setup Global State
groq_client = None
intent_engine = None
emotion_predictor = None
language_predictor = None
rag_chain = None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    global groq_client, intent_engine, emotion_predictor, language_predictor, rag_chain
    print("Initializing Models and Pipeline... (This may take a moment)")

    # 1. Initialize Classifiers
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    intents = [
        "greeting", "goodbye", "gratitude", 
        "asking_mental_health_question", "self_harm_intent", 
        "unsafe_query", "out_of_scope"
    ]
    
    print("Loading Intent Classifier...")
    intent_engine = IntentChatbotEngine(groq_client=groq_client, intents=intents)
    
    print("Loading Language Predictor...")
    language_predictor = LanguagePredictor()
    
    print("Loading Emotion Predictor...")
    emotion_predictor = EmotionPredictor("/media/ahmed-fayad/3b40def2-87b7-41ce-8913-2981f887941c/home/ITI Cont.../NLP and LLM/NLP Final Project/emotion-bert-final")

    # 2. Initialize Embeddings and Vector DB
    print("Loading Vector Store & RAG Chain...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={'device': 'cpu'}, 
        encode_kwargs={'normalize_embeddings': True} 
    )

    qdrant_client = QdrantClient(
        url=os.getenv("QDRANT_URL"), 
        api_key=os.getenv("QDRANT_API_KEY")
    )

    vectorstore = QdrantVectorStore(
        client=qdrant_client,
        collection_name="mental_health_index_using_bge-small-en-v1.5",
        embedding=embeddings
    )

    # Use pure Qdrant retriever for faster startup (BM25 requires loading+chunking the dataset in memory)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # 3. Create RAG Chain
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile", # Or mixtral-8x7b-32768
        temperature=0.7
    )

    system_prompt = (
        "You are a compassionate, professional mental health assistant. "
        "Use the following pieces of retrieved counseling advice to answer the user's question. "
        "If you don't know the answer with the provided context, just say that you don't know, don't try to make up medical advice. "
        "Always maintain an empathetic and supportive tone.\n"
        "IMPORTANT: You MUST reply in the following language: {language}\n\n"
        "Context:\n{context}"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    print("Pipeline Initialized Successfully!")
    yield

# Initialize FastAPI App
app = FastAPI(title="Unified RAG Pipeline & Classifier API", lifespan=lifespan)

# Request / Response Schemas
class ChatRequest(BaseModel):
    user_message: str

class ChatResponse(BaseModel):
    original_message: str
    detected_language: str
    detected_emotion: str
    detected_intent: str
    response: str
    source: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    msg = request.user_message

    try:
        # A) Predict Language
        detected_lang = language_predictor.predict(msg)
        if isinstance(detected_lang, list): 
            detected_lang = detected_lang[0]

        # B) Predict Emotion
        emotion_res = emotion_predictor.predict(msg)
        detected_emotion = emotion_res[0]["label"] if emotion_res else "unknown"

        # C) Predict Intent using Intent Engine
        # The intent engine requires the message. Wait, IntentEngine uses chat completion.
        intent_data = intent_engine.classify_intent(msg)
        intent_name = intent_data.get("intent", "out_of_scope")

        # D) Orchestrate final action based on intent
        if intent_name == "asking_mental_health_question":
            # If it's an actual mental health question, run it through the RAG context
            rag_result = rag_chain.invoke({
                "input": msg,
                "language": detected_lang
            })
            final_answer = rag_result["answer"]
            source = "RAG Model"
        else:
            # Otherwise, use the standard fallback router (e.g. self-harm safety message, greeting, etc)
            # Route method returns localized and safe responses built into your engine.
            final_answer = intent_engine.route(msg, intent_data)
            source = f"Intent Engine / Router ({intent_name})"

        return ChatResponse(
            original_message=msg,
            detected_language=str(detected_lang),
            detected_emotion=detected_emotion,
            detected_intent=intent_name,
            response=final_answer,
            source=source
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=FileResponse)
def read_root():
    return "index.html"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
