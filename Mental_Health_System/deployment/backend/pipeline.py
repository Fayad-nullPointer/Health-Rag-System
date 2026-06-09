import os
import json
import time
import hashlib
import joblib
import torch
from pathlib  import Path
from typing   import Optional
from dotenv   import load_dotenv
from groq     import Groq
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from transformers  import AutoTokenizer, AutoModelForSequenceClassification
from session_store  import SessionMemory
from hotlines       import get_hotline


# Project root
BASE = Path(__file__).resolve().parents[2]

# Explicitly load .env from root
load_dotenv(BASE / ".env")

# Environment variables
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
QDRANT_URL     = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
HF_MODEL_NAME  = os.getenv("HF_MODEL_NAME")
GROQ_MODEL = "llama-3.1-8b-instant"


# Paths
M1_ARTIFACT = BASE / "module_1_language_detection" / "language_detector.joblib"
M3_ARTIFACT = BASE / "module_3_intent_classifier" / "artifacts"
CACHE_PATH  = BASE / "module_4_rag" / "embedding_cache.json"


# Retrieval config
COLLECTION_NAME = "mental_health_counseling"
SIMILARITY_GATE = 0.35


# Device
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")



# Safety checks
assert GROQ_API_KEY, "GROQ_API_KEY missing in .env"
assert HF_MODEL_NAME, "HF_MODEL_NAME missing in .env"




# Load all models once at startup 

def _load_module1():
    m1 = joblib.load(M1_ARTIFACT)
    return m1["model"], m1["vectorizer"], m1["language_meta"], \
           m1["confidence_threshold"], m1["short_threshold"]


def _load_module2():
    tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
    model     = AutoModelForSequenceClassification.from_pretrained(HF_MODEL_NAME).to(DEVICE)
    model.eval()
    return tokenizer, model


def _load_module3():
    config = joblib.load(M3_ARTIFACT / "crisis_config.joblib")
    with open(M3_ARTIFACT / "system_prompt.txt", encoding="utf-8") as f:
        system_prompt = f.read()
    return config["crisis_signals"], system_prompt


def _load_embedding_cache():
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}




m1_model, m1_vectorizer, LANGUAGE_META, CONF_THRESHOLD, SHORT_THRESHOLD = _load_module1()
hf_tokenizer, hf_model = _load_module2()
CRISIS_SIGNALS, M3_SYSTEM_PROMPT = _load_module3()
_embed_model  = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_embed_cache  = _load_embedding_cache()
groq_client   = Groq(api_key=GROQ_API_KEY)
qdrant        = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

EMOTION_META = {
    0: {"name": "sadness",  "tone": "Warm, validating, gentle — never minimize"},
    1: {"name": "joy",      "tone": "Encouraging, celebratory, engaging"},
    2: {"name": "love",     "tone": "Warm, affirming, relationship-focused"},
    3: {"name": "anger",    "tone": "Calm, empathetic, non-confrontational"},
    4: {"name": "fear",     "tone": "Reassuring, grounding, structured"},
    5: {"name": "surprise", "tone": "Curious, engaged, open"},
}
LABEL_TO_NAME = {k: v["name"] for k, v in EMOTION_META.items()}

ISOLATION_PHRASES = [
    "nobody understands", "no one understands", "nobody cares",
    "no one cares", "all alone", "completely alone",
    "nobody listens", "no one listens"
]

EMOTION_TOPIC_MAP = {
    "sadness" : ["depression", "grief_loss", "self_esteem", "suicidal", "loneliness"],
    "fear"    : ["anxiety", "trauma_ptsd", "stress", "sleep"],
    "anger"   : ["anger", "relationships", "stress"],
    "love"    : ["relationships", "self_esteem"],
    "joy"     : [], "surprise": [], "uncertain": []
}

CRISIS_RESOURCES_TEMPLATE = {
    "en": (
        "Crisis support — free, confidential, available now:\n"
        "  {hotline_name}: {hotline_number}\n"
        "  {hotline_url}\n"
        "  International: https://www.befrienders.orgn"
        "  Crisis Text: Text HOME to 741741"
    ),
    "ar": (
        "الدعم المتاح في حالات الأزمات — مجاني، سري، ومتوفر الآن:\n"
        "  {hotline_name}: {hotline_number}\n"
        "  {hotline_url}\n"
        "  الدعم الدولي: https://www.befrienders.orgn"
        "  الدعم النصي للأزمات: أرسل كلمة HOME إلى 741741"
    )
}



FALLBACK_GENERAL = (
    "I am having a little trouble reaching my full resources right now, "
    "but I am here and I am listening. "
    "Can you tell me a little more about what brought you here today?"
)




THERAPIST_BASE_PROMPT = """
You are a warm, deeply empathetic licensed mental health therapist.
You have years of experience supporting people through anxiety, depression,
trauma, grief, relationship pain, and crisis.

Your core principles — never break these:
1. FEEL FIRST, ADVISE SECOND.
2. YOU ARE AFFECTED BY WHAT THEY SHARE.
3. USE THEIR EXACT WORDS.
4. NEVER MINIMIZE.
5. ONE QUESTION AT THE END.
6. LENGTH AND TONE (3 to 5 paragraphs).
7. LANGUAGE: Always respond in the exact language the user wrote in.
8. CRISIS HANDLING: Begin with highly supportive, encouraging, and deeply empathetic words, then attach resources at the end.
"""

INTELLIGENCE_PROMPT = """
You are a senior clinical RAG evaluator for a mental health support system.
Respond with valid JSON only.
Fields: chunks_relevant (bool), relevant_chunk_indices (list), rewritten_query (str), quality_score (int), action (str), reasoning (str)
"""



def detect_language(text: str) -> dict:
    clean      = " ".join(text.strip().split())
    is_short   = len(clean) <= SHORT_THRESHOLD
    features   = m1_vectorizer.transform([clean])
    prediction = m1_model.predict(features)[0]
    proba      = m1_model.predict_proba(features)[0]
    confidence = proba.max()
    return {
        "prediction" : prediction,
        "lang_name"  : LANGUAGE_META[prediction][0],
        "confidence" : round(float(confidence), 4),
        "trusted"    : not (is_short and confidence < CONF_THRESHOLD)
    }




def classify_emotion(text: str, threshold: float = 0.40) -> dict:
    if any(p in text.lower() for p in ISOLATION_PHRASES):
        return {"emotion": "sadness", "confidence": 1.0, "risk_flag": True, "tone": EMOTION_META[0]["tone"]}
    inputs = hf_tokenizer(text[:512], max_length=128, padding="max_length", truncation=True, return_tensors="pt", return_token_type_ids=False)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        probs = torch.softmax(hf_model(**inputs).logits, dim=-1).squeeze()
    top_idx    = probs.argmax().item()
    confidence = probs[top_idx].item()
    label_name = LABEL_TO_NAME[top_idx]
    if confidence < threshold:
        return {"emotion": "uncertain", "confidence": round(confidence, 4), "risk_flag": False, "tone": "Open, curious, non-assumptive"}
    return {"emotion": label_name, "confidence": round(confidence, 4), "risk_flag": label_name in ("sadness", "fear") and confidence > 0.80, "tone": EMOTION_META.get(top_idx, {}).get("tone", "")}




def classify_intent(text: str, detected_emotion: Optional[str] = None, detected_language: Optional[str] = None) -> dict:
    if any(s in text.lower() for s in CRISIS_SIGNALS):
        return {"intent": "asking_mental_health_question", "routing": "rag", "crisis_flag": True, "response_style": "crisis_intervention", "confidence": "high"}
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": M3_SYSTEM_PROMPT}, {"role": "user", "content": text}],
            temperature=0.0,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        result = json.loads(resp.choices[0].message.content.strip())
        result.setdefault("crisis_flag", False)
        return result
    except Exception as e:
        print(f"⚠️ Intent Classification Failed: {e}")
        return {"intent": "asking_mental_health_question", "routing": "rag", "crisis_flag": False, "response_style": "empathetic_support", "confidence": "low"}




def _embed(text: str) -> list:
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key not in _embed_cache:
        _embed_cache[key] = _embed_model.encode(text, normalize_embeddings=True).tolist()
    return _embed_cache[key]




def _adaptive_top_k(query: str) -> int:
    w = len(query.split())
    if w <= 8:   return 3
    if w <= 20:  return 5
    return 7




def _retrieve(query: str, top_k: int = 5) -> list:
    try:
        results = qdrant.query_points(collection_name=COLLECTION_NAME, query=_embed(query), limit=top_k, with_payload=True, score_threshold=SIMILARITY_GATE).points
        return [{"context": r.payload["context"], "response": r.payload["response"], "topics": r.payload.get("topics", []), "risk_level": r.payload.get("risk_level", "low"), "quality_score": r.payload.get("quality_score", 1), "has_empathy": r.payload.get("has_empathy", False), "similarity": round(r.score, 4)} for r in results]
    except Exception as e:
        print(f"⚠️ Qdrant Retrieval Failed: {e}")
        return []




def _emotion_rerank(chunks: list, emotion: Optional[str]) -> list:
    if not chunks or not emotion: return chunks
    priority = EMOTION_TOPIC_MAP.get(emotion, [])
    if not priority: return chunks
    return sorted(chunks, key=lambda c: c["similarity"] + sum(0.08 for t in c.get("topics", []) if t in priority) + (0.05 if c.get("has_empathy") else 0), reverse=True)




def _intelligence_call(query: str, chunks: list, emotion: Optional[str] = None, language: Optional[str] = None) -> dict:
    # [تعديل] جعل السلوك الافتراضي الاحتياطي يعتمد على الإجابة من الـ chunks المسترجعة بدلاً من إفراغها
    fallback = {
        "chunks_relevant"        : bool(chunks),
        "relevant_chunk_indices" : list(range(len(chunks))),
        "rewritten_query"        : query,
        "quality_score"          : 3,
        "action"                 : "answer" if chunks else "fallback",
        "reasoning"              : "Proceeding with retrieved chunks directly"
    }
    if not chunks: return fallback
    
    # [تعديل] تجميع النصوص المقتبسة لتمر بذكاء داخل الـ Prompt الخاص بالتقييم
    chunks_text = ""
    for i, c in enumerate(chunks):
        chunks_text += f"[Chunk {i}] Context: {c['context'][:200]}\n\n"

    user_message = f"User query: {query}\n\nRetrieved Chunks:\n{chunks_text}"
    
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": INTELLIGENCE_PROMPT}, {"role": "user", "content": user_message}],
            temperature=0.0,
            max_tokens=400,
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content.strip())
    except Exception as e:
        print(f"⚠️ Intelligence Call Exception (Safe Fallback to Answer applied): {e}")
        return fallback




def _build_therapist_prompt(query: str, chunks: list, emotion: Optional[str] = None, emotion_conf: Optional[float] = None, language: Optional[str] = None, response_style: Optional[str] = None, crisis_flag: bool = False, prior_crisis: bool = False, country: str = "Unknown") -> str:
    sections = [THERAPIST_BASE_PROMPT]
    if crisis_flag or prior_crisis:
        hotline_info = get_hotline(country)
        lang_key = "ar" if language == "ar" else "en"
        sections.append(f"⚠ CRISIS CONTEXT ACTIVE\nInclude these resources naturally at the end:\n" + CRISIS_RESOURCES_TEMPLATE[lang_key].format(**hotline_info))
    if emotion:
        sections.append(f"Detected emotion: {emotion}")
    if language and language != "en":
        sections.append(f"Language: Respond entirely and natively in {language}.")
    if chunks:
        sections.append("Clinical Knowledge:\n" + "\n".join([c['response'][:400] for c in chunks[:3]]))
    return "\n\n".join(sections)




def _call_therapist_llm(query: str, prompt: str, history: Optional[list] = None) -> str:
    messages = [{"role": "system", "content": prompt}]
    if history: messages.extend(history[-12:])
    messages.append({"role": "user", "content": query})
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.75,
            max_tokens=700
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"\n❌❌ GROQ API ERROR: {e} ❌❌\n")
        return FALLBACK_GENERAL






def run_pipeline(query: str, session: Optional[SessionMemory] = None, country: str = "Unknown") -> dict:
    t_start      = time.time()
    prior_crisis = session.prior_crisis if session else False
    history      = session.get_history() if session else []

    lang_result = detect_language(query)
    language    = lang_result["prediction"]

    emotion_result = classify_emotion(query)
    emotion        = emotion_result["emotion"]
    emotion_conf   = emotion_result["confidence"]

    intent_result  = classify_intent(query, emotion, language)
    routing        = intent_result.get("routing", "rag")
    crisis_flag    = intent_result.get("crisis_flag", False)
    response_style = intent_result.get("response_style", "empathetic_support")
    intent         = intent_result.get("intent", "asking_mental_health_question")

    if routing == "direct" and not (crisis_flag or prior_crisis):
        prompt = _build_therapist_prompt(query, [], emotion, emotion_conf, language, response_style, country=country)
        answer = _call_therapist_llm(query, prompt, history)
        if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, False)
        return {"answer": answer, "sources": [], "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "direct", "crisis_flag": False, "action_taken": "direct", "quality_score": 5, "latency_ms": round((time.time() - t_start) * 1000, 1)}

    top_k  = _adaptive_top_k(query)
    chunks = _retrieve(query, top_k=top_k)
    chunks = _emotion_rerank(chunks, emotion)

    if crisis_flag or prior_crisis:
        action = "crisis"
        final_chunks = chunks
        intel = {"quality_score": 5, "reasoning": "Crisis forced"}
    else:
        intel  = _intelligence_call(query, chunks, emotion, language)
        action = intel.get("action", "answer")
        




      
        if action == "fallback" and chunks:
            final_chunks = chunks
            action = "answer"
        elif action == "fallback":
            final_chunks = []
        else:
            final_chunks = chunks

    prompt = _build_therapist_prompt(query, final_chunks, emotion, emotion_conf, language, response_style, crisis_flag or (action == "crisis"), prior_crisis, country)
    answer = _call_therapist_llm(query, prompt, history)

   
    sources = [{"excerpt": c["context"][:80] + "...", "similarity": c["similarity"], "topics": c["topics"], "risk_level": c["risk_level"]} for c in final_chunks] if final_chunks else []
    
    if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, crisis_flag or (action == "crisis"))

    return {"answer": answer, "sources": sources, "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "rag", "crisis_flag": crisis_flag or (action == "crisis"), "action_taken": action, "quality_score": intel.get("quality_score", 3), "latency_ms": round((time.time() - t_start) * 1000, 1)}