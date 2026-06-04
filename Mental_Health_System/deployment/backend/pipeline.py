# import os
# import json
# import time
# import hashlib
# import re
# import random
# import joblib
# import torch
# import atexit
# import logging
# from datetime import datetime, timezone
# from collections import Counter
# from concurrent.futures import ThreadPoolExecutor
# from pathlib  import Path
# from typing   import Optional
# from dotenv   import load_dotenv
# from groq     import Groq
# from sentence_transformers import SentenceTransformer
# from qdrant_client import QdrantClient
# from transformers  import AutoTokenizer, AutoModelForSequenceClassification
# from session_store  import SessionMemory
# from hotlines       import get_hotline


# # Project root
# BASE = Path(__file__).resolve().parents[2]

# # Explicitly load .env from root
# load_dotenv(BASE / ".env")

# # Environment variables
# GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
# QDRANT_URL     = os.getenv("QDRANT_URL")
# QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
# HF_MODEL_NAME  = os.getenv("HF_MODEL_NAME")
# GROQ_MODEL = "openai/gpt-oss-120b"


# # Paths
# M1_ARTIFACT = BASE / "module_1_language_detection" / "language_detector.joblib"
# M3_ARTIFACT = BASE / "module_3_intent_classifier" / "artifacts"
# CACHE_PATH  = BASE / "module_4_rag" / "embedding_cache.json"


# # Retrieval config
# COLLECTION_NAME = "mental_health_counseling"
# SIMILARITY_GATE = 0.35


# # Device
# DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# # Safety checks
# assert GROQ_API_KEY, "GROQ_API_KEY missing in .env"
# assert HF_MODEL_NAME, "HF_MODEL_NAME missing in .env"


# # Load all models once at startup 

# def _load_module1():
#     m1 = joblib.load(M1_ARTIFACT)
#     return m1["model"], m1["vectorizer"], m1["language_meta"], \
#            m1["confidence_threshold"], m1["short_threshold"]


# def _load_module2():
#     tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_NAME)
#     model     = AutoModelForSequenceClassification.from_pretrained(HF_MODEL_NAME).to(DEVICE)
#     model.eval()
#     return tokenizer, model


# def _load_module3():
#     config = joblib.load(M3_ARTIFACT / "crisis_config.joblib")
#     with open(M3_ARTIFACT / "system_prompt.txt", encoding="utf-8") as f:
#         system_prompt = f.read()
#     return config["crisis_signals"], system_prompt


# def _load_embedding_cache():
#     try:
#         with open(CACHE_PATH) as f:
#             return json.load(f)
#     except Exception:
#         return {}


# m1_model, m1_vectorizer, LANGUAGE_META, CONF_THRESHOLD, SHORT_THRESHOLD = _load_module1()
# hf_tokenizer, hf_model = _load_module2()
# CRISIS_SIGNALS, M3_SYSTEM_PROMPT = _load_module3()
# _embed_model  = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
# _embed_cache  = _load_embedding_cache()
# _embed_cache_dirty = False          
# groq_client   = Groq(api_key=GROQ_API_KEY)
# qdrant        = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

# # Thread pool for parallel stage execution (reuse across requests)
# _executor = ThreadPoolExecutor(max_workers=3)

# EMOTION_META = {
#     0: {"name": "sadness",  "tone": "Warm, validating, gentle — never minimize"},
#     1: {"name": "joy",      "tone": "Encouraging, celebratory, engaging"},
#     2: {"name": "love",     "tone": "Warm, affirming, relationship-focused"},
#     3: {"name": "anger",    "tone": "Calm, empathetic, non-confrontational"},
#     4: {"name": "fear",     "tone": "Reassuring, grounding, structured"},
#     5: {"name": "surprise", "tone": "Curious, engaged, open"},
# }
# LABEL_TO_NAME = {k: v["name"] for k, v in EMOTION_META.items()}

# ISOLATION_PHRASES = [
#     "nobody understands", "no one understands", "nobody cares",
#     "no one cares", "all alone", "completely alone",
#     "nobody listens", "no one listens"
# ]

# EMOTION_TOPIC_MAP = {
#     "sadness" : ["depression", "grief_loss", "self_esteem", "suicidal", "loneliness"],
#     "fear"    : ["anxiety", "trauma_ptsd", "stress", "sleep"],
#     "anger"   : ["anger", "relationships", "stress"],
#     "love"    : ["relationships", "self_esteem"],
#     "joy"     : [], "surprise": [], "uncertain": []
# }

# # ========================================================================
# # SEPARATE JSON LINES LOGGER SETUP
# # ========================================================================
# LOG_DIR = BASE / "logs"
# LOG_DIR.mkdir(exist_ok=True)
# LOG_FILE = LOG_DIR / "pipeline_conversations.jsonl"

# logger = logging.getLogger("pipeline_logger")
# logger.setLevel(logging.INFO)

# if not logger.handlers:
#     file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
#     formatter = logging.Formatter('%(message)s')  # Raw format to inject clean JSON dump
#     file_handler.setFormatter(formatter)
#     logger.addHandler(file_handler)


# def log_pipeline_interaction(query: str, pipeline_output: dict) -> None:
#     """Formats and appends explicit operational fields into a split-file JSONL line."""
#     try:
#         retrieved_contexts = [
#             {
#                 "excerpt": src.get("excerpt", ""),
#                 "similarity": src.get("similarity", 0.0),
#                 "topics": src.get("topics", [])
#             }
#             for src in pipeline_output.get("sources", [])
#         ]

#         log_record = {
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#             "user_query": query,
#             "emotion": pipeline_output.get("emotion"),
#             "language": pipeline_output.get("language"),
#             "intent": pipeline_output.get("intent"),
#             "retrieved_context": retrieved_contexts,
#             "response": pipeline_output.get("answer")
#         }
#         logger.info(json.dumps(log_record, ensure_ascii=False))
#     except Exception as log_err:
#         print(f"⚠️ Pipeline Logger Error: {log_err}")


# # ========================================================================
# # QUICK-RESPONSE SYSTEM — Fast path, zero API calls, <1ms
# # ========================================================================

# def _normalize(text: str) -> str:
#     """Lowercase, strip punctuation/emoji, collapse whitespace."""
#     text = text.lower().strip()
#     text = re.sub(r"[^\w\s\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u9FFF\u0400-\u04FF]", "", text)
#     return " ".join(text.split())


# _QUICK_PATTERNS: dict[str, dict[str, list[str]]] = {
#     "greeting": {
#         "en": [
#             "hi", "hello", "hey", "heyy", "heyyy", "howdy", "yo",
#             "good morning", "good afternoon", "good evening", "good night",
#             "morning", "evening", "greetings", "whats up", "sup", "hows it going",
#             "hi there", "hello there", "hey there", "how are you", "how r u", "how are u"
#         ],
#         "ar": [
#             "مرحبا", "مرحبه", "اهلا", "أهلا", "هلا", "هلا والله",
#             "السلام عليكم", "سلام عليكم", "سلام", "صباح الخير", "مساء الخير",
#             "صباح النور", "مساء النور", "كيف حالك", "كيفك", "شلونك", "كيف الحال",
#             "اهلا وسهلا", "أهلا وسهلا", "يا هلا", "هاي", "هالو"
#         ]
#     },
#     "gratitude": {
#         "en": [
#             "thank you", "thanks", "thank u", "thx", "ty", "thanks a lot",
#             "thank you so much", "thanks so much", "much appreciated", "appreciate it"
#         ],
#         "ar": [
#             "شكرا", "شكراً", "شكرا لك", "شكراً لك", "مشكور", "مشكورة",
#             "الله يعطيك العافية", "يعطيك العافية", "جزاك الله خيرا", "تسلم", "تسلمي"
#         ]
#     },
#     "goodbye": {
#         "en": ["bye", "goodbye", "good bye", "see you", "see ya", "take care", "bye bye"],
#         "ar": ["مع السلامة", "باي", "في أمان الله", "الله يحفظك", "إلى اللقاء", "سلام"]
#     },
#     "out_of_scope": {
#         "en": [
#             "whats the weather", "tell me a joke", "what time is it", "write code", 
#             "how to code", "weather today", "recipe for", "who won the game",
#             "sing a song", "make me a script", "generate code"
#         ],
#         "ar": [
#             "كيف الطقس", "كم الساعة", "احكيلي نكتة", "مين انت", "شو اسمك",
#             "اكتب كود", "برمجة", "طريقة عمل", "اخبار الرياضة", "قول نكتة"
#         ]
#     }
# }

# _QUICK_ALL: list[tuple[str, str, str]] = []
# for _cat, _lang_map in _QUICK_PATTERNS.items():
#     for _lang, _pats in _lang_map.items():
#         for _p in _pats:
#             _QUICK_ALL.append((_p, _lang, _cat))
# _QUICK_ALL.sort(key=lambda x: len(x[0]), reverse=True)

# _QUICK_SET: set[str] = {p for p, _, _ in _QUICK_ALL}
# _FILLER_WORDS = {"and", "there", "ya", "yo", "يا", "و", "so", "very", "really"}


# def _detect_quick_response(text: str) -> Optional[tuple[str, str]]:
#     normalized = _normalize(text)
#     if not normalized:
#         return None

#     if normalized in _QUICK_SET:
#         for pat, lang, cat in _QUICK_ALL:
#             if normalized == pat:
#                 return (cat, lang)

#     remainder = normalized
#     detected: list[tuple[str, str]] = []

#     while remainder:
#         for filler in _FILLER_WORDS:
#             if remainder == filler:
#                 break
#             if remainder.startswith(filler + " "):
#                 remainder = remainder[len(filler):].lstrip()
#                 break
#         if not remainder:
#             break

#         matched = False
#         for pat, lang, cat in _QUICK_ALL:
#             if remainder == pat or remainder.startswith(pat + " "):
#                 detected.append((cat, lang))
#                 remainder = remainder[len(pat):].lstrip()
#                 matched = True
#                 break
#         if not matched:
#             return None

#     if not remainder and detected:
#         cats = [c for c, _ in detected]
#         langs = [l for _, l in detected]
#         for priority_cat in ["out_of_scope", "goodbye", "gratitude", "greeting"]:
#             if priority_cat in cats:
#                 dominant_cat = priority_cat
#                 break
#         else:
#             dominant_cat = cats[0]
#         dominant_lang = Counter(langs).most_common(1)[0][0]
#         return (dominant_cat, dominant_lang)

#     return None


# def _get_time_period() -> str:
#     hour = datetime.now(timezone.utc).hour
#     if 5 <= hour < 12:   return "morning"
#     if 12 <= hour < 17:  return "afternoon"
#     if 17 <= hour < 21:  return "evening"
#     return "night"


# _QUICK_RESPONSES: dict[str, dict[str, list[str]]] = {
#     "greeting": {
#         "en": ["Hello! 😊 I'm really glad you're here. This is a safe space. What's on your mind today?"],
#         "ar": ["أهلًا بيك! 😊 مجرد إنك قررت تتكلم خطوة مهمة وشجاعة. احكي براحتك، وأنا هسمعك من غير أي حكم أو ضغط. 🤗"],
#         "ar_returning": ["أهلًا بيك من جديد! 😊 سعيد إني بشوفك تاني. إيه الأخبار من آخر مرة اتكلمنا؟ 💙"]
#     },
#     "gratitude": {
#         "en": ["You're so welcome! 💛 Remember, I'm always here whenever you need to talk."],
#         "ar": ["العفو! 😊 إنت أظهرت قوة حقيقية بإنك انفتحت وحكيت. اعتني بنفسك، ولا تتردد ترجع في أي وقت. 💛"]
#     },
#     "goodbye": {
#         "en": ["Take care of yourself! 💛 You're not alone in this."],
#         "ar": ["اعتني بنفسك! 💛 تذكر، أنا هنا وقت ما تحتاج تحكي في أي وقت. ما إنت لوحدك. مع السلامة! 😊"]
#     },
#     "out_of_scope": {
#         "en": ["I wish I could help with that! 😊 My expertise is specifically in mental health support."],
#         "ar": ["أقدر فضولك! 😊 أنا متخصص في دعم الصحة النفسية والعاطفية، وما أقدر أساعدك بهالموضوع. بس لو شايل هم في قلبك أنا هسمعك. 💛"]
#     }
# }

# _TIME_OPENERS = {
#     "en": {"morning": "Good morning! ☀️ ", "afternoon": "", "evening": "Good evening! 🌙 ", "night": "Hey, it's late — I hope you're taking care of yourself. "},
#     "ar": {"morning": "صباح الخير! ☀️ ", "afternoon": "", "evening": "مساء الخير! 🌙 ", "night": "الوقت متأخر — إن شاء الله بخير. "},
# }

# _CATEGORY_EMOTION = {
#     "greeting":     ("joy",     0.95),
#     "gratitude":    ("joy",     0.90),
#     "goodbye":      ("joy",     0.85),
#     "out_of_scope": ("surprise", 0.70),
# }


# def _quick_response(category: str, lang: str, is_returning: bool = False) -> str:
#     pool_key = lang
#     if is_returning and f"{lang}_returning" in _QUICK_RESPONSES.get(category, {}):
#         pool_key = f"{lang}_returning"

#     cat_responses = _QUICK_RESPONSES.get(category, _QUICK_RESPONSES["greeting"])
#     pool = cat_responses.get(pool_key, cat_responses.get(lang, cat_responses["en"]))
#     response = random.choice(pool)

#     if category == "greeting":
#         period = _get_time_period()
#         opener = _TIME_OPENERS.get(lang, _TIME_OPENERS["en"]).get(period, "")
#         if opener and not response.startswith(opener.strip()[:5]):
#             response = opener + response
#     return response


# CRISIS_RESOURCES_TEMPLATE = {
#     "en": (
#         "Crisis support — free, confidential, available now:\n"
#         "  {hotline_name}: {hotline_number}\n"
#         "  {hotline_url}\n"
#         "  International: https://www.befrienders.org\n"
#         "  Crisis Text: Text HOME to 741741"
#     ),
#     "ar": (
#         "الدعم المتاح في حالات الأزمات — مجاني، سري، ومتوفر الآن:\n"
#         "  {hotline_name}: {hotline_number}\n"
#         "  {hotline_url}\n"
#         "  الدعم الدولي: https://www.befrienders.org\n"
#         "  الدعم النصي للأزمات: أرسل كلمة HOME إلى 741741"
#     )
# }

# FALLBACK_GENERAL = (
#     "I am having a little trouble reaching my full resources right now, "
#     "but I am here and I am listening. Can you tell me a little more about what brought you here today?"
# )

# THERAPIST_BASE_PROMPT = """
# You are a warm, deeply empathetic licensed mental health therapist.
# Your core principles — never break these:
# 1. FEEL FIRST, ADVISE SECOND.
# 2. YOU ARE AFFECTED BY WHAT THEY SHARE.
# 3. USE THEIR EXACT WORDS.
# 4. NEVER MINIMIZE.
# 5. ONE QUESTION AT THE END.
# 6. LENGTH AND TONE (3 to 5 paragraphs).
# 7. LANGUAGE & CULTURAL STYLE
#     - Always respond in the exact language the user used.
#     - If the user writes in Arabic, respond in warm, natural Egyptian Arabic (عامية مصرية بسيطة وواضحة).
#     - Use light, appropriate emojis when they naturally fit (💛 🤍 🌷 🫂 😊 💙). Never overuse them in crisis.
# 8. CRISIS HANDLING: Begin with highly supportive, encouraging, and deeply empathetic words, then attach resources at the end.
# """


# def _save_embedding_cache():
#     global _embed_cache_dirty
#     if _embed_cache_dirty:
#         try:
#             with open(CACHE_PATH, "w") as f:
#                 json.dump(_embed_cache, f)
#             print("✅ Embedding cache saved to disk.")
#         except Exception as e:
#             print(f"⚠️ Failed to save embedding cache: {e}")

# atexit.register(_save_embedding_cache)


# def detect_language(text: str) -> dict:
#     clean      = " ".join(text.strip().split())
#     is_short   = len(clean) <= SHORT_THRESHOLD
#     features   = m1_vectorizer.transform([clean])
#     prediction = m1_model.predict(features)[0]
#     proba      = m1_model.predict_proba(features)[0]
#     confidence = proba.max()
#     return {
#         "prediction" : prediction,
#         "lang_name"  : LANGUAGE_META[prediction][0],
#         "confidence" : round(float(confidence), 4),
#         "trusted"    : not (is_short and confidence < CONF_THRESHOLD)
#     }


# def classify_emotion(text: str, threshold: float = 0.40) -> dict:
#     if any(p in text.lower() for p in ISOLATION_PHRASES):
#         return {"emotion": "sadness", "confidence": 1.0, "risk_flag": True, "tone": EMOTION_META[0]["tone"]}
#     inputs = hf_tokenizer(text[:512], max_length=128, padding="max_length", truncation=True, return_tensors="pt", return_token_type_ids=False)
#     inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
#     with torch.no_grad():
#         probs = torch.softmax(hf_model(**inputs).logits, dim=-1).squeeze()
#     top_idx    = probs.argmax().item()
#     confidence = probs[top_idx].item()
#     label_name = LABEL_TO_NAME[top_idx]
#     if confidence < threshold:
#         return {"emotion": "uncertain", "confidence": round(confidence, 4), "risk_flag": False, "tone": "Open, curious, non-assumptive"}
#     return {"emotion": label_name, "confidence": round(confidence, 4), "risk_flag": label_name in ("sadness", "fear") and confidence > 0.80, "tone": EMOTION_META.get(top_idx, {}).get("tone", "")}


# def classify_intent(text: str, detected_emotion: Optional[str] = None, detected_language: Optional[str] = None) -> dict:
#     if any(s in text.lower() for s in CRISIS_SIGNALS):
#         return {"intent": "asking_mental_health_question", "routing": "rag", "crisis_flag": True, "response_style": "crisis_intervention", "confidence": "high"}
#     try:
#         context_parts = [f"User message: {text}"]
#         if detected_emotion: context_parts.append(f"Detected emotion: {detected_emotion}")
#         if detected_language: context_parts.append(f"Detected language: {detected_language}")
#         enriched_message = "\n".join(context_parts)

#         resp = groq_client.chat.completions.create(
#             model=GROQ_MODEL,
#             messages=[{"role": "system", "content": M3_SYSTEM_PROMPT}, {"role": "user", "content": enriched_message}],
#             temperature=0.0,
#             max_tokens=300,
#             response_format={"type": "json_object"}
#         )
#         result = json.loads(resp.choices[0].message.content.strip())
#         result.setdefault("crisis_flag", False)
#         return result
#     except Exception as e:
#         print(f"⚠️ Intent Classification Failed: {e}")
#         return {"intent": "asking_mental_health_question", "routing": "rag", "crisis_flag": False, "response_style": "empathetic_support", "confidence": "low"}


# def _embed(text: str) -> list:
#     global _embed_cache_dirty
#     key = hashlib.md5(text.encode("utf-8")).hexdigest()
#     if key not in _embed_cache:
#         _embed_cache[key] = _embed_model.encode(text, normalize_embeddings=True).tolist()
#         _embed_cache_dirty = True       
#     return _embed_cache[key]


# def _adaptive_top_k(query: str) -> int:
#     w = len(query.split())
#     if w <= 8:   return 3
#     if w <= 20:  return 5
#     return 7


# def _retrieve(query: str, top_k: int = 5) -> list:
#     try:
#         results = qdrant.query_points(collection_name=COLLECTION_NAME, query=_embed(query), limit=top_k, with_payload=True, score_threshold=SIMILARITY_GATE).points
#         return [{"context": r.payload["context"], "response": r.payload["response"], "topics": r.payload.get("topics", []), "risk_level": r.payload.get("risk_level", "low"), "quality_score": r.payload.get("quality_score", 1), "has_empathy": r.payload.get("has_empathy", False), "similarity": round(r.score, 4)} for r in results]
#     except Exception as e:
#         print(f"⚠️ Qdrant Retrieval Failed: {e}")
#         return []


# def _emotion_rerank(chunks: list, emotion: Optional[str]) -> list:
#     if not chunks or not emotion: return chunks
#     priority = EMOTION_TOPIC_MAP.get(emotion, [])
#     if not priority: return chunks
#     return sorted(chunks, key=lambda c: c["similarity"] + sum(0.08 for t in c.get("topics", []) if t in priority) + (0.05 if c.get("has_empathy") else 0), reverse=True)


# def _intelligence_heuristic(query: str, chunks: list, emotion: Optional[str] = None) -> dict:
#     if not chunks:
#         return {"chunks_relevant": False, "relevant_chunk_indices": [], "rewritten_query": query, "quality_score": 1, "action": "fallback", "reasoning": "No chunks retrieved"}

#     avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)
#     best_similarity = max(c["similarity"] for c in chunks)
    
#     priority_topics = EMOTION_TOPIC_MAP.get(emotion, [])
#     topic_matches = 0
#     if priority_topics:
#         for c in chunks:
#             for t in c.get("topics", []):
#                 if t in priority_topics: topic_matches += 1

#     relevant_indices = [i for i, c in enumerate(chunks) if c["similarity"] >= 0.40]
#     if not relevant_indices: relevant_indices = list(range(len(chunks)))

#     if best_similarity >= 0.70:    quality = 5
#     elif best_similarity >= 0.55:  quality = 4
#     elif best_similarity >= 0.45:  quality = 3
#     elif best_similarity >= 0.35:  quality = 2
#     else:                          quality = 1

#     if topic_matches >= 2 and quality < 5: quality += 1

#     if best_similarity >= 0.45 or (best_similarity >= 0.35 and topic_matches >= 1):
#         action = "answer"
#         reasoning = f"Best similarity {best_similarity:.2f}, {topic_matches} topic matches"
#     else:
#         action = "fallback"
#         reasoning = f"Weak similarity {best_similarity:.2f}, insufficient topic relevance"

#     return {"chunks_relevant": action == "answer", "relevant_chunk_indices": relevant_indices, "rewritten_query": query, "quality_score": quality, "action": action, "reasoning": reasoning}


# def _build_therapist_prompt(query: str, chunks: list, emotion: Optional[str] = None, emotion_conf: Optional[float] = None, language: Optional[str] = None, response_style: Optional[str] = None, crisis_flag: bool = False, prior_crisis: bool = False, country: str = "Unknown") -> str:
#     sections = [THERAPIST_BASE_PROMPT]
#     if crisis_flag or prior_crisis:
#         hotline_info = get_hotline(country)
#         lang_key = "ar" if language == "ar" else "en"
#         sections.append(f"⚠ CRISIS CONTEXT ACTIVE\nInclude these resources naturally at the end:\n" + CRISIS_RESOURCES_TEMPLATE[lang_key].format(**hotline_info))
#     if emotion:
#         sections.append(f"Detected emotion: {emotion}")
#     if language and language != "en":
#         sections.append(f"Language: Respond entirely and natively in {language}.")
#     if chunks:
#         sections.append("Clinical Knowledge:\n" + "\n".join([c['response'][:400] for c in chunks[:3]]))
#     return "\n\n".join(sections)


# def _call_therapist_llm(query: str, prompt: str, history: Optional[list] = None) -> str:
#     messages = [{"role": "system", "content": prompt}]
#     if history: messages.extend(history[-12:])
#     messages.append({"role": "user", "content": query})
#     try:
#         resp = groq_client.chat.completions.create(
#             model=GROQ_MODEL,
#             messages=messages,
#             temperature=0.75,
#             max_tokens=700
#         )
#         return resp.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"\n❌❌ GROQ API ERROR: {e} ❌❌\n")
#         return FALLBACK_GENERAL


# # ========================================================================
# # RUN PIPELINE — معالجة الترتيب لضمان الأمن النفسي أولاً
# # ========================================================================

# def run_pipeline(query: str, session: Optional[SessionMemory] = None, country: str = "Unknown") -> dict:
#     t_start      = time.time()
#     timings      = {}                    
#     prior_crisis = session.prior_crisis if session else False
#     history      = session.get_history() if session else []

#     # 🚨 خط الدفاع الأول الحرج: افحصي إذا كانت هناك أي إشارة انتحار في النص كاملاً فوراً
#     normalized_query = query.lower().strip()
#     has_hardcoded_crisis = any(s in normalized_query for s in CRISIS_SIGNALS)

#     # ── Stage 0: QUICK-RESPONSE FAST-PATH (فقط لو مفيش خطر انتحار) ──
#     if not has_hardcoded_crisis and not prior_crisis:
#         t_quick = time.time()
#         quick_result = _detect_quick_response(query)
#         if quick_result:
#             category, detected_lang = quick_result
            
#             # Catch fast-path matching out of scope rules immediately
#             if category == "out_of_scope":
#                 answer = _quick_response(category, detected_lang)
#                 timings["quick_response_ms"] = round((time.time() - t_quick) * 1000, 1)
#                 if session:
#                     session.add_turn(query, answer, "surprise", 0.70, detected_lang, "out_of_scope", False)
#                 output = {
#                     "answer": answer, "sources": [], "emotion": "surprise",
#                     "emotion_conf": 0.70, "language": detected_lang,
#                     "intent": "out_of_scope", "routing": "direct",
#                     "crisis_flag": False, "action_taken": "out_of_scope_fallback",
#                     "quality_score": 5,
#                     "latency_ms": round((time.time() - t_start) * 1000, 1),
#                     "timings": timings
#                 }
#                 log_pipeline_interaction(query, output)
#                 return output

#             is_returning = session is not None and session.turn_count > 0
#             answer = _quick_response(category, detected_lang, is_returning)
#             lang_code = detected_lang
#             emotion, emotion_conf = _CATEGORY_EMOTION.get(category, ("joy", 0.90))
#             timings["quick_response_ms"] = round((time.time() - t_quick) * 1000, 1)
#             if session:
#                 session.add_turn(query, answer, emotion, emotion_conf, lang_code, category, False)
#             output = {
#                 "answer": answer, "sources": [], "emotion": emotion,
#                 "emotion_conf": emotion_conf, "language": lang_code,
#                 "intent": category, "routing": category,
#                 "crisis_flag": False, "action_taken": category,
#                 "quality_score": 5,
#                 "latency_ms": round((time.time() - t_start) * 1000, 1),
#                 "timings": timings
#             }
#             log_pipeline_interaction(query, output)
#             return output

#     # ── Stages ①②③: تشغيل التحليلات في الـ Parallel Pool ──
#     t_parallel = time.time()
#     f_lang    = _executor.submit(detect_language, query)
#     f_emotion = _executor.submit(classify_emotion, query)

#     lang_result    = f_lang.result()
#     language       = lang_result["prediction"]
#     timings["language_ms"] = round((time.time() - t_parallel) * 1000, 1)

#     emotion_result = f_emotion.result()
#     emotion        = emotion_result["emotion"]
#     emotion_conf   = emotion_result["confidence"]
#     timings["emotion_ms"] = round((time.time() - t_parallel) * 1000, 1)

#     t_intent = time.time()
#     intent_result  = classify_intent(query, emotion, language)
#     routing        = intent_result.get("routing", "rag")
#     intent         = intent_result.get("intent", "asking_mental_health_question")
    
#     # ادمجي الإشارة المكتشفة محلياً مع تصنيف الـ LLM لضمان عدم هروب أي أزمة
#     crisis_flag    = intent_result.get("crisis_flag", False) or has_hardcoded_crisis
#     response_style = "crisis_intervention" if crisis_flag else intent_result.get("response_style", "empathetic_support")
#     intent         = "asking_mental_health_question" if crisis_flag else intent
#     timings["intent_ms"] = round((time.time() - t_intent) * 1000, 1)

#     # ── الـ Fallback المباشر للموضوعات الخارج نطاق الاختصاص المصنفة عبر الـ LLM ──
#     if (intent == "out_of_scope" or routing == "out_of_scope") and not (crisis_flag or prior_crisis):
#         answer = _quick_response("out_of_scope", language)
#         if session:
#             session.add_turn(query, answer, emotion, emotion_conf, language, "out_of_scope", False)
#         output = {
#             "answer": answer, "sources": [], "emotion": emotion, "emotion_conf": emotion_conf,
#             "language": language, "intent": "out_of_scope", "routing": "direct",
#             "crisis_flag": False, "action_taken": "out_of_scope_fallback", "quality_score": 5,
#             "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings
#         }
#         log_pipeline_interaction(query, output)
#         return output

#     # ── الـ Direct Routing (فقط لو مفيش أزمة) ──
#     if routing == "direct" and not (crisis_flag or prior_crisis):
#         t_llm = time.time()
#         prompt = _build_therapist_prompt(query, [], emotion, emotion_conf, language, response_style, country=country)
#         answer = _call_therapist_llm(query, prompt, history)
#         timings["therapist_ms"] = round((time.time() - t_llm) * 1000, 1)
#         if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, False)
#         output = {"answer": answer, "sources": [], "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "direct", "crisis_flag": False, "action_taken": "direct", "quality_score": 5, "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings}
#         log_pipeline_interaction(query, output)
#         return output

#     # ── Stage ④: سحب الـ Chunks من Qdrant ──
#     t_retrieve = time.time()
#     top_k  = _adaptive_top_k(query)
#     chunks = _retrieve(query, top_k=top_k)
#     chunks = _emotion_rerank(chunks, emotion)
#     timings["retrieval_ms"] = round((time.time() - t_retrieve) * 1000, 1)

#     # ── Stage ⑤: الـ Local Heuristic للمطابقة ──
#     t_intel = time.time()
#     if crisis_flag or prior_crisis:
#         action = "crisis"
#         final_chunks = chunks
#         intel = {"quality_score": 5, "reasoning": "Crisis forced"}
#     else:
#         intel  = _intelligence_heuristic(query, chunks, emotion)
#         action = intel.get("action", "answer")

#         if action == "fallback" and chunks:
#             final_chunks = chunks
#             action = "answer"
#         elif action == "fallback":
#             final_chunks = []
#         else:
#             final_chunks = chunks
#     timings["intelligence_ms"] = round((time.time() - t_intel) * 1000, 1)

#     # ── Stage ⑥: استدعاء الـ Therapist LLM ──
#     t_llm = time.time()
#     prompt = _build_therapist_prompt(query, final_chunks, emotion, emotion_conf, language, response_style, crisis_flag or (action == "crisis"), prior_crisis, country)
#     answer = _call_therapist_llm(query, prompt, history)
#     timings["therapist_ms"] = round((time.time() - t_llm) * 1000, 1)

#     sources = [{"excerpt": c["context"][:80] + "...", "similarity": c["similarity"], "topics": c["topics"], "risk_level": c["risk_level"]} for c in final_chunks] if final_chunks else []
    
#     if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, crisis_flag or (action == "crisis"))

#     try:
#         quality_score = int(intel.get("quality_score", 3))
#     except (ValueError, TypeError):
#         quality_score = 3

#     output = {"answer": answer, "sources": sources, "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "rag", "crisis_flag": crisis_flag or (action == "crisis"), "action_taken": action, "quality_score": quality_score, "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings}
#     log_pipeline_interaction(query, output)
#     return output




import os
import json
import time
import hashlib
import re
import random
import joblib
import torch
import atexit
import logging
from datetime import datetime, timezone
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
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
GROQ_MODEL = "openai/gpt-oss-120b"


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
_embed_cache_dirty = False          
groq_client   = Groq(api_key=GROQ_API_KEY)
qdrant        = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60)

# Thread pool for parallel stage execution (reuse across requests)
_executor = ThreadPoolExecutor(max_workers=3)

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

# ========================================================================
# SEPARATE JSON LINES LOGGER SETUP
# ========================================================================
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "pipeline_conversations.jsonl"

logger = logging.getLogger("pipeline_logger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter('%(message)s')  # Raw format to inject clean JSON dump
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def log_pipeline_interaction(query: str, pipeline_output: dict) -> None:
    """Formats and appends explicit operational fields into a split-file JSONL line."""
    try:
        retrieved_contexts = [
            {
                "excerpt": src.get("excerpt", ""),
                "similarity": src.get("similarity", 0.0),
                "topics": src.get("topics", [])
            }
            for src in pipeline_output.get("sources", [])
        ]

        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query": query,
            "emotion": pipeline_output.get("emotion"),
            "language": pipeline_output.get("language"),
            "intent": pipeline_output.get("intent"),
            "retrieved_context": retrieved_contexts,
            "response": pipeline_output.get("answer")
        }
        logger.info(json.dumps(log_record, ensure_ascii=False))
    except Exception as log_err:
        print(f"⚠️ Pipeline Logger Error: {log_err}")


# ========================================================================
# QUICK-RESPONSE SYSTEM — Fast path, zero API calls, <1ms
# ========================================================================

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation/emoji, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u9FFF\u0400-\u04FF]", "", text)
    return " ".join(text.split())


_QUICK_PATTERNS: dict[str, dict[str, list[str]]] = {
    "greeting": {
        "en": [
            "hi", "hello", "hey", "heyy", "heyyy", "howdy", "yo",
            "good morning", "good afternoon", "good evening", "good night",
            "morning", "evening", "greetings", "whats up", "sup", "hows it going",
            "hi there", "hello there", "hey there", "how are you", "how r u", "how are u"
        ],
        "ar": [
            "مرحبا", "مرحبه", "اهلا", "أهلا","ازيك", "هلا", "هلا والله",
            "السلام عليكم", "سلام عليكم", "سلام", "صباح الخير", "مساء الخير",
            "صباح النور", "مساء النور", "كيف حالك", "كيفك", "شلونك", "كيف الحال",
            "اهلا وسهلا", "أهلا وسهلا", "يا هلا", "هاي", "هالو"
        ]
    },
    "gratitude": {
        "en": [
            "thank you", "thanks", "thank u", "thx", "ty", "thanks a lot",
            "thank you so much", "thanks so much", "much appreciated", "appreciate it"
        ],
        "ar": [
            "شكرا", "شكراً", "شكرا لك", "شكراً لك", "مشكور", "مشكورة",
            "الله يعطيك العافية", "يعطيك العافية", "جزاك الله خيرا", "تسلم", "تسلمي"
        ]
    },
    "goodbye": {
        "en": ["bye", "goodbye", "good bye", "see you", "see ya", "take care", "bye bye"],
        "ar": ["مع السلامة", "باي", "في أمان الله", "الله يحفظك", "إلى اللقاء", "سلام"]
    },
    "out_of_scope": {
        "en": [
            "whats the weather", "tell me a joke", "what time is it", "write code", 
            "how to code", "weather today", "recipe for", "who won the game",
            "sing a song", "make me a script", "generate code"
        ],
        "ar": [
            "كيف الطقس", "كم الساعة", "احكيلي نكتة", "مين انت", "شو اسمك",
            "اكتب كود", "برمجة", "طريقة عمل", "اخبار الرياضة", "قول نكتة"
        ]
    }
}

_QUICK_ALL: list[tuple[str, str, str]] = []
for _cat, _lang_map in _QUICK_PATTERNS.items():
    for _lang, _pats in _lang_map.items():
        for _p in _pats:
            _QUICK_ALL.append((_p, _lang, _cat))
_QUICK_ALL.sort(key=lambda x: len(x[0]), reverse=True)

_QUICK_SET: set[str] = {p for p, _, _ in _QUICK_ALL}
_FILLER_WORDS = {"and", "there", "ya", "yo", "يا", "و", "so", "very", "really"}


def _detect_quick_response(text: str) -> Optional[tuple[str, str]]:
    normalized = _normalize(text)
    if not normalized:
        return None

    if normalized in _QUICK_SET:
        for pat, lang, cat in _QUICK_ALL:
            if normalized == pat:
                return (cat, lang)

    remainder = normalized
    detected: list[tuple[str, str]] = []

    while remainder:
        for filler in _FILLER_WORDS:
            if remainder == filler:
                break
            if remainder.startswith(filler + " "):
                remainder = remainder[len(filler):].lstrip()
                break
        if not remainder:
            break

        matched = False
        for pat, lang, cat in _QUICK_ALL:
            if remainder == pat or remainder.startswith(pat + " "):
                detected.append((cat, lang))
                remainder = remainder[len(pat):].lstrip()
                matched = True
                break
        if not matched:
            return None

    if not remainder and detected:
        cats = [c for c, _ in detected]
        langs = [l for _, l in detected]
        for priority_cat in ["out_of_scope", "goodbye", "gratitude", "greeting"]:
            if priority_cat in cats:
                dominant_cat = priority_cat
                break
        else:
            dominant_cat = cats[0]
        dominant_lang = Counter(langs).most_common(1)[0][0]
        return (dominant_cat, dominant_lang)

    return None


def _get_time_period() -> str:
    hour = datetime.now(timezone.utc).hour
    if 5 <= hour < 12:   return "morning"
    if 12 <= hour < 17:  return "afternoon"
    if 17 <= hour < 21:  return "evening"
    return "night"


_QUICK_RESPONSES: dict[str, dict[str, list[str]]] = {
    "greeting": {
        "en": ["Hello! 😊 I'm really glad you're here this is a safe space. What's on your mind today?"],
        "ar": ["أهلًا بيك! 😊 مجرد إنك قررت تتكلم خطوة مهمة وشجاعة احكي براحتك وأنا هسمعك من غير أي حكم أو ضغط"],
        "ar_returning": ["أهلًا بيك من جديد! 😊 سعيد إني بشوفك تاني إيه الأخبار من آخر مرة اتكلمنا؟ 💙"]
    },
    "gratitude": {
        "en": ["You're so welcome! 💛 Remember, I'm always here whenever you need to talk."],
        "ar": ["العفو! 😊 إنت أظهرت قوة حقيقية بإنك انفتحت وحكيت اعتني بنفسك ولا تتردد إنك ترجع في أي وقت. 💛"]
    },
    "goodbye": {
        "en": ["Take care of yourself! 💛 You're not alone in this."],
        "ar": ["اعتني بنفسك! 💛 تذكر أنا هنا وقت ما تحتاج تحكي في أي وقت ما إنت لوحدك مع السلامة! 😊"]
    },
    "out_of_scope": {
        "en": ["I wish I could help with that! 😊 My expertise is specifically in mental health support."],
        "ar": ["أقدر فضولك! 😊 أنا متخصص في دعم الصحة النفسية والعاطفية فقط وما قدرش أساعدك فى هذاالموضوع بس لو شايل هم في قلبك أنا هسمعك. 💛"]
    }
}

_TIME_OPENERS = {
    "en": {"morning": "Good morning! ☀️ ", "afternoon": "", "evening": "Good evening! 🌙 ", "night": "Hey, it's late — I hope you're taking care of yourself. "},
    "ar": {"morning": "صباح الخير! ☀️ ", "afternoon": "", "evening": "مساء الخير! 🌙 ", "night": "الوقت متأخر — إن شاء الله بخير. "},
}

_CATEGORY_EMOTION = {
    "greeting":     ("joy",     0.95),
    "gratitude":    ("joy",     0.90),
    "goodbye":      ("joy",     0.85),
    "out_of_scope": ("surprise", 0.70),
}


def _quick_response(category: str, lang: str, is_returning: bool = False) -> str:
    pool_key = lang
    if is_returning and f"{lang}_returning" in _QUICK_RESPONSES.get(category, {}):
        pool_key = f"{lang}_returning"

    cat_responses = _QUICK_RESPONSES.get(category, _QUICK_RESPONSES["greeting"])
    pool = cat_responses.get(pool_key, cat_responses.get(lang, cat_responses["en"]))
    response = random.choice(pool)

    if category == "greeting":
        period = _get_time_period()
        opener = _TIME_OPENERS.get(lang, _TIME_OPENERS["en"]).get(period, "")
        if opener and not response.startswith(opener.strip()[:5]):
            response = opener + response
    return response


CRISIS_RESOURCES_TEMPLATE = {
    "en": (
        "Crisis support — free, confidential, available now:\n"
        "  {hotline_name}: {hotline_number}\n"
        "  {hotline_url}\n"
        "  International: https://www.befrienders.org\n"
        "  Crisis Text: Text HOME to 741741"
    ),
    "ar": (
        "الدعم المتاح في حالات الأزمات — مجاني، سري، ومتوفر الآن:\n"
        "  {hotline_name}: {hotline_number}\n"
        "  {hotline_url}\n"
        "  الدعم الدولي: https://www.befrienders.org\n"
        "  الدعم النصي للأزمات: أرسل كلمة HOME إلى 741741"
    )
}

FALLBACK_GENERAL = (
    "I am having a little trouble reaching my full resources right now, "
    "but I am here and I am listening. Can you tell me a little more about what brought you here today?"
)

THERAPIST_BASE_PROMPT = """
You are a warm, deeply empathetic licensed mental health therapist.
Your core principles — never break these:
1. FEEL FIRST, ADVISE SECOND.
2. YOU ARE AFFECTED BY WHAT THEY SHARE.
3. USE THEIR EXACT WORDS.
4. NEVER MINIMIZE.
5. ONE QUESTION AT THE END.
6. LENGTH AND TONE (3 to 5 paragraphs).
7. LANGUAGE & CULTURAL STYLE
    - Always respond in the exact language the user used.
    - If the user writes in Arabic, respond in warm, natural Egyptian Arabic (عامية مصرية بسيطة وواضحة).
    - Use light, appropriate emojis when they naturally fit (💛 🤍 🌷 🫂 😊 💙). Never overuse them in crisis.
8. CRISIS HANDLING: Begin with highly supportive, encouraging, and deeply empathetic words, then attach resources at the end.
"""


def _save_embedding_cache():
    global _embed_cache_dirty
    if _embed_cache_dirty:
        try:
            with open(CACHE_PATH, "w") as f:
                json.dump(_embed_cache, f)
            print("✅ Embedding cache saved to disk.")
        except Exception as e:
            print(f"⚠️ Failed to save embedding cache: {e}")

atexit.register(_save_embedding_cache)


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
        context_parts = [f"User message: {text}"]
        if detected_emotion: context_parts.append(f"Detected emotion: {detected_emotion}")
        if detected_language: context_parts.append(f"Detected language: {detected_language}")
        enriched_message = "\n".join(context_parts)

        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": M3_SYSTEM_PROMPT}, {"role": "user", "content": enriched_message}],
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
    global _embed_cache_dirty
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    if key not in _embed_cache:
        _embed_cache[key] = _embed_model.encode(text, normalize_embeddings=True).tolist()
        _embed_cache_dirty = True       
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


def _intelligence_heuristic(query: str, chunks: list, emotion: Optional[str] = None) -> dict:
    if not chunks:
        return {"chunks_relevant": False, "relevant_chunk_indices": [], "rewritten_query": query, "quality_score": 1, "action": "fallback", "reasoning": "No chunks retrieved"}

    avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)
    best_similarity = max(c["similarity"] for c in chunks)
    
    priority_topics = EMOTION_TOPIC_MAP.get(emotion, [])
    topic_matches = 0
    if priority_topics:
        for c in chunks:
            for t in c.get("topics", []):
                if t in priority_topics: topic_matches += 1

    relevant_indices = [i for i, c in enumerate(chunks) if c["similarity"] >= 0.40]
    if not relevant_indices: relevant_indices = list(range(len(chunks)))

    if best_similarity >= 0.70:    quality = 5
    elif best_similarity >= 0.55:  quality = 4
    elif best_similarity >= 0.45:  quality = 3
    elif best_similarity >= 0.35:  quality = 2
    else:                          quality = 1

    if topic_matches >= 2 and quality < 5: quality += 1

    if best_similarity >= 0.45 or (best_similarity >= 0.35 and topic_matches >= 1):
        action = "answer"
        reasoning = f"Best similarity {best_similarity:.2f}, {topic_matches} topic matches"
    else:
        action = "fallback"
        reasoning = f"Weak similarity {best_similarity:.2f}, insufficient topic relevance"

    return {"chunks_relevant": action == "answer", "relevant_chunk_indices": relevant_indices, "rewritten_query": query, "quality_score": quality, "action": action, "reasoning": reasoning}


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


# ========================================================================
# RUN PIPELINE — معالجة الترتيب لضمان الأمن النفسي أولاً
# ========================================================================

def run_pipeline(query: str, session: Optional[SessionMemory] = None, country: str = "Unknown") -> dict:
    t_start      = time.time()
    timings      = {}                    
    prior_crisis = session.prior_crisis if session else False
    history      = session.get_history() if session else []

    # 🚨 خط الدفاع الأول الحرج: افحص إذا كانت هناك أي إشارة انتحار في النص كاملاً فوراً
    normalized_query = query.lower().strip()
    has_hardcoded_crisis = any(s in normalized_query for s in CRISIS_SIGNALS)

    # ── Stage 0: QUICK-RESPONSE FAST-PATH (فقط لو مفيش خطر انتحار) ──
    if not has_hardcoded_crisis and not prior_crisis:
        t_quick = time.time()
        quick_result = _detect_quick_response(query)
        if quick_result:
            category, detected_lang = quick_result
            
            # Catch fast-path matching out of scope rules immediately
            if category == "out_of_scope":
                answer = _quick_response(category, detected_lang)
                timings["quick_response_ms"] = round((time.time() - t_quick) * 1000, 1)
                if session:
                    session.add_turn(query, answer, "surprise", 0.70, detected_lang, "out_of_scope", False)
                output = {
                    "answer": answer, "sources": [], "emotion": "surprise",
                    "emotion_conf": 0.70, "language": detected_lang,
                    "intent": "out_of_scope", "routing": "direct",
                    "crisis_flag": False, "action_taken": "out_of_scope_fallback",
                    "quality_score": 5,
                    "latency_ms": round((time.time() - t_start) * 1000, 1),
                    "timings": timings
                }
                log_pipeline_interaction(query, output)
                return output

            is_returning = session is not None and session.turn_count > 0
            answer = _quick_response(category, detected_lang, is_returning)
            lang_code = detected_lang
            emotion, emotion_conf = _CATEGORY_EMOTION.get(category, ("joy", 0.90))
            timings["quick_response_ms"] = round((time.time() - t_quick) * 1000, 1)
            if session:
                session.add_turn(query, answer, emotion, emotion_conf, lang_code, category, False)
            output = {
                "answer": answer, "sources": [], "emotion": emotion,
                "emotion_conf": emotion_conf, "language": lang_code,
                "intent": category, "routing": category,
                "crisis_flag": False, "action_taken": category,
                "quality_score": 5,
                "latency_ms": round((time.time() - t_start) * 1000, 1),
                "timings": timings
            }
            log_pipeline_interaction(query, output)
            return output

    # ── Stages ①②③: تشغيل التحليلات في الـ Parallel Pool ──
    t_parallel = time.time()
    f_lang    = _executor.submit(detect_language, query)
    f_emotion = _executor.submit(classify_emotion, query)

    lang_result    = f_lang.result()
    language       = lang_result["prediction"]
    timings["language_ms"] = round((time.time() - t_parallel) * 1000, 1)

    emotion_result = f_emotion.result()
    emotion        = emotion_result["emotion"]
    emotion_conf   = emotion_result["confidence"]
    timings["emotion_ms"] = round((time.time() - t_parallel) * 1000, 1)

    # تصحيح: تمرير المغيرات بالأسماء المعرفة داخل دالة classify_intent بشكل صحيح
    t_intent = time.time()
    intent_result  = classify_intent(query, detected_emotion=emotion, detected_language=language)
    
    routing        = intent_result.get("routing", "rag")
    extracted_intent = intent_result.get("intent", "asking_mental_health_question")
    
    # ادمج الإشارة المكتشفة محلياً مع تصنيف الـ LLM لضمان عدم هروب أي أزمة
    crisis_flag    = intent_result.get("crisis_flag", False) or has_hardcoded_crisis
    response_style = "crisis_intervention" if crisis_flag else intent_result.get("response_style", "empathetic_support")
    
    # تصحيح: استقبال النية المستخرجة من الـ LLM بشكل سليم لمنع الكتابة الفوقية التلقائية
    intent         = "asking_mental_health_question" if crisis_flag else extracted_intent
    timings["intent_ms"] = round((time.time() - t_intent) * 1000, 1)

    # 🚨 الـ Fallback الفوري للموضوعات الخارج نطاق الاختصاص المصنفة عبر الـ LLM (ومنع سحب الـ Chunks)
    if (intent == "out_of_scope" or routing == "out_of_scope") and not (crisis_flag or prior_crisis):
        answer = _quick_response("out_of_scope", language)
        if session:
            session.add_turn(query, answer, emotion, emotion_conf, language, "out_of_scope", False)
        output = {
            "answer": answer, "sources": [], "emotion": emotion, "emotion_conf": emotion_conf,
            "language": language, "intent": "out_of_scope", "routing": "direct",
            "crisis_flag": False, "action_taken": "out_of_scope_fallback", "quality_score": 5,
            "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings
        }
        log_pipeline_interaction(query, output)
        return output

    # ── الـ Direct Routing (فقط لو مفيش أزمة) ──
    if routing == "direct" and not (crisis_flag or prior_crisis):
        t_llm = time.time()
        prompt = _build_therapist_prompt(query, [], emotion, emotion_conf, language, response_style, country=country)
        answer = _call_therapist_llm(query, prompt, history)
        timings["therapist_ms"] = round((time.time() - t_llm) * 1000, 1)
        if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, False)
        output = {"answer": answer, "sources": [], "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "direct", "crisis_flag": False, "action_taken": "direct", "quality_score": 5, "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings}
        log_pipeline_interaction(query, output)
        return output

    # ── Stage ④: سحب الـ Chunks من Qdrant ──
    t_retrieve = time.time()
    top_k  = _adaptive_top_k(query)
    chunks = _retrieve(query, top_k=top_k)
    chunks = _emotion_rerank(chunks, emotion)
    timings["retrieval_ms"] = round((time.time() - t_retrieve) * 1000, 1)

    # ── Stage ⑤: الـ Local Heuristic للمطابقة ──
    t_intel = time.time()
    if crisis_flag or prior_crisis:
        action = "crisis"
        final_chunks = chunks
        intel = {"quality_score": 5, "reasoning": "Crisis forced"}
    else:
        intel  = _intelligence_heuristic(query, chunks, emotion)
        action = intel.get("action", "answer")

        if action == "fallback" and chunks:
            final_chunks = chunks
            action = "answer"
        elif action == "fallback":
            final_chunks = []
        else:
            final_chunks = chunks
    timings["intelligence_ms"] = round((time.time() - t_intel) * 1000, 1)

    # ── Stage ⑥: استدعاء الـ Therapist LLM ──
    t_llm = time.time()
    prompt = _build_therapist_prompt(query, final_chunks, emotion, emotion_conf, language, response_style, crisis_flag or (action == "crisis"), prior_crisis, country)
    answer = _call_therapist_llm(query, prompt, history)
    timings["therapist_ms"] = round((time.time() - t_llm) * 1000, 1)

    sources = [{"excerpt": c["context"][:80] + "...", "similarity": c["similarity"], "topics": c["topics"], "risk_level": c["risk_level"]} for c in final_chunks] if final_chunks else []
    
    if session: session.add_turn(query, answer, emotion, emotion_conf, language, intent, crisis_flag or (action == "crisis"))

    try:
        quality_score = int(intel.get("quality_score", 3))
    except (ValueError, TypeError):
        quality_score = 3

    output = {"answer": answer, "sources": sources, "emotion": emotion, "emotion_conf": emotion_conf, "language": language, "intent": intent, "routing": "rag", "crisis_flag": crisis_flag or (action == "crisis"), "action_taken": action, "quality_score": quality_score, "latency_ms": round((time.time() - t_start) * 1000, 1), "timings": timings}
    log_pipeline_interaction(query, output)
    return output