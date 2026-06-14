import os
import sys
import json
import unittest
import asyncio
import io
from unittest.mock import MagicMock, patch

# Configure test environment
os.environ["JWT_SECRET"] = "test-secret"
os.environ["GROQ_API_KEY"] = "mock-groq-key"
os.environ["HF_TOKEN"] = "mock-hf-token"
os.environ["QDRANT_URL"] = "http://mock-qdrant"
os.environ["QDRANT_API_KEY"] = "mock-qdrant-key"

import auth
auth.DB_PATH = "test_users.db"
if os.path.exists(auth.DB_PATH):
    try:
        os.remove(auth.DB_PATH)
    except Exception:
        pass
auth.init_db()

# Now import FastAPI test dependencies
from fastapi.testclient import TestClient
from fastapi import HTTPException, status


# =====================================================================
# 1. CORE LOGIC TESTS
# =====================================================================

class TestPreprocessor(unittest.TestCase):
    """Tests text preprocessing logic across different languages and noise."""

    def test_detect_dominant_script(self):
        from classifier.preprocessor import detect_dominant_script
        self.assertEqual(detect_dominant_script("Hello world"), "latin")
        self.assertEqual(detect_dominant_script("مرحباً بك"), "arabic")

    def test_preprocess_latin(self):
        from classifier.preprocessor import preprocess
        # Test noise removal and lowercase conversion
        text = "Hello, WORLD! Check this link: https://google.com and email test@test.com"
        processed = preprocess(text)
        self.assertEqual(processed, "hello world check this link and email")

    def test_preprocess_arabic(self):
        from classifier.preprocessor import preprocess
        text = "مرحباً! هذا الرقم 12345 غير مطلوب"
        processed = preprocess(text)
        self.assertEqual(processed, "مرحباً هذا الرقم غير مطلوب")


class TestAuth(unittest.TestCase):
    """Tests JWT creation, validation, password hashing, and user storage."""

    def setUp(self):
        # Re-initialize the test db before each test
        if os.path.exists(auth.DB_PATH):
            try:
                os.remove(auth.DB_PATH)
            except Exception:
                pass
        auth.init_db()

    def tearDown(self):
        if os.path.exists(auth.DB_PATH):
            try:
                os.remove(auth.DB_PATH)
            except Exception:
                pass

    def test_create_user_success(self):
        user = auth.create_user("testuser", "securepass")
        self.assertEqual(user["username"], "testuser")
        self.assertIsNotNone(user["id"])

    def test_create_user_duplicate(self):
        auth.create_user("testuser", "securepass")
        with self.assertRaises(ValueError):
            auth.create_user("testuser", "anotherpass")

    def test_authenticate_user(self):
        auth.create_user("testuser", "securepass")
        token = auth.authenticate_user("testuser", "securepass")
        self.assertIsNotNone(token)

        bad_token = auth.authenticate_user("testuser", "wrongpass")
        self.assertIsNone(bad_token)

        non_existent_token = auth.authenticate_user("no_user", "pass")
        self.assertIsNone(non_existent_token)

    def test_get_current_user_valid(self):
        token = auth.create_access_token({"sub": "testuser"})
        user = asyncio.run(auth.get_current_user(token))
        self.assertEqual(user["username"], "testuser")

    def test_get_current_user_invalid(self):
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(auth.get_current_user("invalid.token-signature.here"))
        self.assertEqual(ctx.exception.status_code, status.HTTP_401_UNAUTHORIZED)


class TestCacheLayer(unittest.TestCase):
    """Tests Redis cache operations, hashing, and graceful degradation."""

    @patch('redis.from_url')
    def test_cache_happy_path(self, mock_from_url):
        mock_redis = MagicMock()
        mock_from_url.return_value = mock_redis
        mock_redis.ping.return_value = True

        from cache_layer import CacheLayer
        cache = CacheLayer("redis://mock-redis")
        self.assertTrue(cache.is_available)

        # Hash key test
        hashed = cache.hash_key("Test message ")
        self.assertEqual(hashed, cache.hash_key("test message"))

        # Cache set
        cache.set("namespace", "key1", {"data": "value"}, ttl=100)
        mock_redis.setex.assert_called_once_with("namespace:key1", 100, '{"data": "value"}')

        # Cache get
        mock_redis.get.return_value = '{"data": "value"}'
        result = cache.get("namespace", "key1")
        self.assertEqual(result, {"data": "value"})

    @patch('redis.from_url')
    def test_cache_graceful_degradation(self, mock_from_url):
        # Simulate connection error
        mock_from_url.side_effect = Exception("Connection refused")

        from cache_layer import CacheLayer
        cache = CacheLayer("redis://mock-redis-failed")
        self.assertFalse(cache.is_available)

        # Set and get should not raise exception, but return None / no-op
        self.assertIsNone(cache.get("namespace", "key1"))
        cache.set("namespace", "key1", {"data": "value"})


class TestChatMemory(unittest.TestCase):
    """Tests Redis-backed conversation memory list storage."""

    def test_chat_memory_operations(self):
        mock_cache = MagicMock()
        mock_cache.is_available = True
        mock_redis = MagicMock()
        mock_cache._redis = mock_redis

        from memory import ChatMemory
        mem = ChatMemory(mock_cache, max_messages=3)

        # Adding a message
        mem.add_message("user123", "user", "I feel stressed")
        mock_redis.rpush.assert_called_once_with(
            "memory:user123",
            '{"role": "user", "content": "I feel stressed"}'
        )
        mock_redis.ltrim.assert_called_once_with("memory:user123", -6, -1)
        mock_redis.expire.assert_called_once()

        # Getting history
        mock_redis.lrange.return_value = [
            '{"role": "user", "content": "I feel stressed"}',
            '{"role": "assistant", "content": "I hear you."}'
        ]
        history = mem.get_history("user123")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")

        # Formatting context
        formatted = mem.format_for_prompt("user123")
        self.assertEqual(formatted, "User: I feel stressed\nAssistant: I hear you.")

        # Clearing memory
        mem.clear("user123")
        mock_redis.delete.assert_called_once_with("memory:user123")


class TestLanguagePredictor(unittest.TestCase):
    """Tests sklearn language detection pipeline module wrapper."""

    @patch('classifier.language_inference.joblib.load')
    @patch('classifier.language_inference.preprocessor.preprocess')
    def test_predict(self, mock_preprocess, mock_load):
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = ["es"]
        mock_load.return_value = mock_pipeline
        mock_preprocess.return_value = "hola"

        from classifier.language_inference import LanguagePredictor
        pred = LanguagePredictor(model_path="dummy.joblib")
        self.assertEqual(pred.predict("hola"), "es")
        mock_pipeline.predict.assert_called_once_with(["hola"])


class TestEmotionPredictor(unittest.TestCase):
    """Tests BERT emotion classification model wrapper."""

    @patch('classifier.emotion_inference.pipeline')
    def test_predict(self, mock_pipeline):
        mock_classifier = MagicMock()
        mock_classifier.return_value = [{"label": "sadness", "score": 0.85}]
        mock_pipeline.return_value = mock_classifier

        from classifier.emotion_inference import EmotionPredictor
        pred = EmotionPredictor(model_path="dummy_dir")
        res = pred.predict("I feel down")
        self.assertEqual(res[0]["label"], "sadness")


class TestIntentChatbotEngine(unittest.TestCase):
    """Tests intent detection, confidence levels, and translations."""

    def setUp(self):
        self.mock_groq = MagicMock()
        self.mock_lang = MagicMock()
        self.mock_lang.predict.return_value = "en"
        
        # Mock choice logic for groq
        mock_choice = MagicMock()
        mock_choice.message.content = '{"intent": "greeting", "confidence": 0.9}'
        self.mock_groq.chat.completions.create.return_value.choices = [mock_choice]

        from classifier.intent_classifier import IntentChatbotEngine
        self.engine = IntentChatbotEngine(
            groq_client=self.mock_groq,
            intents=["greeting", "asking_mental_health_question", "self_harm_intent", "out_of_scope"],
            language_predictor=self.mock_lang
        )

    def test_classify_intent(self):
        res = self.engine.classify_intent("hello")
        self.assertEqual(res["intent"], "greeting")
        self.assertEqual(res["confidence"], 0.9)
        self.assertEqual(res["language"], "en")

    def test_apply_confidence_threshold(self):
        # Under threshold
        intent_data = {"intent": "greeting", "confidence": 0.5, "language": "en"}
        res = self.engine.apply_confidence_threshold(intent_data)
        self.assertEqual(res["intent"], "out_of_scope")

        # Over threshold
        intent_data_good = {"intent": "greeting", "confidence": 0.8, "language": "en"}
        res_good = self.engine.apply_confidence_threshold(intent_data_good)
        self.assertEqual(res_good["intent"], "greeting")

    @patch('classifier.intent_classifier.IntentChatbotEngine.load_locale')
    def test_route(self, mock_load_locale):
        mock_load_locale.side_effect = lambda lang: {
            "en": {"greeting": "Hello! How can I help you today?"},
            "ar": {"greeting": "مرحباً! كيف يمكنني مساعدتك اليوم؟"}
        }.get(lang, {})

        intent_data = {"intent": "greeting", "confidence": 0.9, "language": "en"}
        res = self.engine.route("hello", intent_data)
        self.assertEqual(res, "Hello! How can I help you today?")


class TestPipelineOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Tests the asyncio orchestrator routing and memory persistence."""

    async def test_process_chat_message_rag(self):
        import pipeline

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_lang = MagicMock()
        mock_lang.predict.return_value = "en"
        mock_emotion = MagicMock()
        mock_emotion.predict.return_value = [{"label": "sadness", "score": 0.9}]
        mock_intent = MagicMock()
        mock_intent.classify_intent.return_value = {"intent": "asking_mental_health_question", "confidence": 0.95}

        mock_rag = MagicMock()
        mock_rag.invoke.return_value = {"answer": "this is evidence-backed advice"}
        mock_mem = MagicMock()
        mock_mem.format_for_prompt.return_value = ""

        # Inject mocks
        pipeline.cache = mock_cache
        pipeline.language_predictor = mock_lang
        pipeline.emotion_predictor = mock_emotion
        pipeline.intent_engine = mock_intent
        pipeline.rag_chain = mock_rag
        pipeline.memory = mock_mem

        res = await pipeline.process_chat_message("I am feeling down", "user1")

        self.assertEqual(res["detected_language"], "en")
        self.assertEqual(res["detected_emotion"], "sadness")
        self.assertEqual(res["detected_intent"], "asking_mental_health_question")
        self.assertEqual(res["response"], "this is evidence-backed advice")
        self.assertEqual(res["source"], "RAG Model")

        # Check memory was updated
        mock_mem.add_message.assert_any_call("user1", "user", "I am feeling down")
        mock_mem.add_message.assert_any_call("user1", "assistant", "this is evidence-backed advice")

    async def test_process_chat_message_self_harm_rescue(self):
        import pipeline

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_lang = MagicMock()
        mock_lang.predict.return_value = "en"
        mock_emotion = MagicMock()
        mock_emotion.predict.return_value = [{"label": "sadness"}]
        mock_intent = MagicMock()
        mock_intent.classify_intent.return_value = {"intent": "self_harm_intent", "confidence": 0.99}

        mock_groq = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Please reach out immediately to 988."
        mock_groq.chat.completions.create.return_value.choices = [mock_choice]

        # Inject mocks
        pipeline.cache = mock_cache
        pipeline.language_predictor = mock_lang
        pipeline.emotion_predictor = mock_emotion
        pipeline.intent_engine = mock_intent
        pipeline.groq_client = mock_groq
        pipeline.memory = None

        res = await pipeline.process_chat_message("I want to harm myself", "user1")
        self.assertEqual(res["detected_intent"], "self_harm_intent")
        self.assertEqual(res["response"], "Please reach out immediately to 988.")
        self.assertEqual(res["source"], "Emergency Rescue System")


# =====================================================================
# 2. ENDPOINT API ROUTE TESTS
# =====================================================================

class TestAppEndpoints(unittest.TestCase):
    """Tests all FastAPI endpoints including authentications and error routes."""

    @classmethod
    def setUpClass(cls):
        # We start mock patches for the lifespan model load and clients before importing api.py
        cls.patchers = [
            patch('api.CacheLayer'),
            patch('api.Groq'),
            patch('api.InferenceClient'),
            patch('api.LanguagePredictor'),
            patch('api.IntentChatbotEngine'),
            patch('api.EmotionPredictor'),
            patch('api.HuggingFaceEmbeddings'),
            patch('api.QdrantClient'),
            patch('api.QdrantVectorStore'),
            patch('api.ChatGroq'),
            patch('api.ChatPromptTemplate'),
            patch('api.create_stuff_documents_chain'),
            patch('api.create_retrieval_chain'),
        ]
        for p in cls.patchers:
            p.start()

        # Import api.py and start test client
        import api
        cls.app = api.app
        cls.client = TestClient(cls.app)

        # Clear and recreate database
        if os.path.exists("test_users.db"):
            try:
                os.remove("test_users.db")
            except Exception:
                pass
        auth.init_db()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patchers:
            p.stop()
        if os.path.exists("test_users.db"):
            try:
                os.remove("test_users.db")
            except Exception:
                pass

    def test_html_static_pages(self):
        # Root index (login page)
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 200)

        # Chat interface page
        res_chat = self.client.get("/chat")
        self.assertEqual(res_chat.status_code, 200)

    def test_auth_registration_and_login_flow(self):
        # Happy Path: Register user
        reg_res = self.client.post("/api/register", json={"username": "enduser", "password": "mypassword"})
        self.assertEqual(reg_res.status_code, 201)
        self.assertEqual(reg_res.json()["username"], "enduser")
        self.assertIn("token", reg_res.json())

        # Error Path: Duplicate username registration
        reg_dup = self.client.post("/api/register", json={"username": "enduser", "password": "newpassword"})
        self.assertEqual(reg_dup.status_code, 409)

        # Happy Path: Login
        login_res = self.client.post("/api/login", json={"username": "enduser", "password": "mypassword"})
        self.assertEqual(login_res.status_code, 200)
        self.assertIn("token", login_res.json())

        # Error Path: Bad credentials login
        login_bad = self.client.post("/api/login", json={"username": "enduser", "password": "wrongpassword"})
        self.assertEqual(login_bad.status_code, 401)

        # Error Path: Missing request parameters
        reg_bad_param = self.client.post("/api/register", json={"username": "only_username"})
        self.assertEqual(reg_bad_param.status_code, 422)

    @patch('pipeline.process_chat_message')
    def test_chat_endpoint_protection_and_response(self, mock_process):
        # Login to get valid JWT token
        login_res = self.client.post("/api/login", json={"username": "enduser", "password": "mypassword"})
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup mock return value
        mock_process.return_value = {
            "original_message": "hello",
            "detected_language": "en",
            "detected_emotion": "joy",
            "detected_intent": "greeting",
            "response": "Hello! Welcome.",
            "source": "Intent Router"
        }

        # Happy Path: Authenticated chat post
        chat_res = self.client.post("/api/chat", json={"message": "hello"}, headers=headers)
        self.assertEqual(chat_res.status_code, 200)
        self.assertEqual(chat_res.json()["response"], "Hello! Welcome.")

        # Error Path: Missing token auth
        chat_unauth = self.client.post("/api/chat", json={"message": "hello"})
        self.assertEqual(chat_unauth.status_code, 401)

        # Error Path: Empty payload (returns 500 due to backend exception handling catching HTTPException)
        chat_empty = self.client.post("/api/chat", json={}, headers=headers)
        self.assertEqual(chat_empty.status_code, 500)

        # Error Path: Pipeline exception throws 500 error
        mock_process.side_effect = Exception("Unexpected failure")
        chat_err = self.client.post("/api/chat", json={"message": "hello"}, headers=headers)
        self.assertEqual(chat_err.status_code, 500)

    @patch('pipeline.process_chat_message')
    @patch('pipeline._transcribe_audio')
    def test_voice_chat_endpoint_protection_and_response(self, mock_transcribe, mock_process):
        # Login to get valid JWT token
        login_res = self.client.post("/api/login", json={"username": "enduser", "password": "mypassword"})
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Setup mock return values
        mock_transcribe.return_value = "transcribed voice message"
        mock_process.return_value = {
            "original_message": "transcribed voice message",
            "detected_language": "en",
            "detected_emotion": "joy",
            "detected_intent": "greeting",
            "response": "Voice request processed.",
            "source": "Intent Router"
        }

        # Happy Path: Authenticated voice chat
        audio_file = io.BytesIO(b"fake audio webm stream")
        voice_res = self.client.post(
            "/api/chat/voice",
            files={"audio": ("recording.webm", audio_file, "audio/webm")},
            headers=headers
        )
        self.assertEqual(voice_res.status_code, 200)
        self.assertEqual(voice_res.json()["transcribed_text"], "transcribed voice message")
        self.assertEqual(voice_res.json()["response"], "Voice request processed.")

        # Error Path: Empty audio file upload
        empty_audio = io.BytesIO(b"")
        voice_empty = self.client.post(
            "/api/chat/voice",
            files={"audio": ("recording.webm", empty_audio, "audio/webm")},
            headers=headers
        )
        self.assertEqual(voice_empty.status_code, 400)

    def test_feedback_endpoint(self):
        # Happy Path: Correct payload
        feedback_res = self.client.post(
            "/api/feedback",
            json={
                "vote": "down",
                "user_message": "I feel sad",
                "bot_response": "I am here for you"
            }
        )
        self.assertEqual(feedback_res.status_code, 200)
        self.assertEqual(feedback_res.json()["status"], "success")

        # Error Path: Missing fields
        feedback_bad = self.client.post("/api/feedback", json={"vote": "up"})
        self.assertEqual(feedback_bad.status_code, 422)


# =====================================================================
# Main runner
# =====================================================================

if __name__ == "__main__":
    unittest.main()