# Mental Health Support Chatbot Pipeline

## Overview
This project is an advanced, multimodal NLP pipeline designed to act as a compassionate, professional mental health assistant. It integrates multiple custom classifiers (Intent, Language, Emotion) and a Retrieval-Augmented Generation (RAG) system to provide safe, empathetic, and contextually aware support. 

## Key Features
* 🧠 **Intent Classification**: Uses Groq LLMs to accurately classify user intents (e.g., mental health queries, self-harm risks, unsafe queries).
* 🛡️ **Safety Guardrails**: Automatically routes self-harm or unsafe requests to predefined safe responses in the user's language.
* 🌐 **Multilingual Support**: Custom Language Detection (Naive Bayes) and multilingual localization for default responses.
* 🎭 **Emotion Detection**: Fine-tuned BERT model running locally to detect the emotional tone of the user's message.
* 📚 **RAG Pipeline**: Retrieves relevant counseling context from a Qdrant Vector Database (using `BAAI/bge-small-en-v1.5` embeddings) and leverages Llama-3 models via Langchain for generating responses.

## Tech Stack
* **Backend Framework**: FastAPI
* **LLM & Orchestration**: Langchain, Groq
* **Vector Database**: Qdrant
* **Embeddings**: HuggingFace (`BAAI/bge-small-en-v1.5`)
* **Custom Models**: Joblib (Scikit-Learn), HuggingFace Transformers

## Prerequisites
* Python 3.9+ 
* API Keys (set in a `.env` file):
  * `GROQ_API_KEY`: For Intent Classification and Chat Completion
  * `QDRANT_URL`: URL to your Qdrant cluster
  * `QDRANT_API_KEY`: API Key for Qdrant

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "NLP Final Project"
   ```

2. **Set up a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install Dependencies:**
   Ensure you install the necessary packages:
   ```bash
   pip install fastapi uvicorn langchain langchain-groq langchain-qdrant qdrant-client sentence-transformers groq transformers joblib python-dotenv pydantic
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   QDRANT_URL=your_qdrant_url_here
   QDRANT_API_KEY=your_qdrant_api_key_here
   ```

## Usage

### 1. Running Locally
Start the FastAPI server using Uvicorn. Models and embeddings will be initialized on startup:
```bash
python api.py
# Or using uvicorn directly:
# uvicorn api:app --host 0.0.0.0 --port 8000
```
Once running, visit `http://localhost:8000` to access the frontend HTML interface or `http://localhost:8000/docs` to see the interactive Swagger UI.

### 2. Using Docker
You can also run the application via Docker:
```bash
docker build -t nlp-mental-health-api .
docker run -p 8000:8000 --env-file .env nlp-mental-health-api
```

### 3. API Endpoints
**POST `/chat`**
Accepts a JSON payload with a `user_message` and returns the chatbot's response, along with detected emotion, language, and intent.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"user_message": "I have been feeling really stressed and overwhelmed lately."}'
```

**Example Response:**
```json
{
  "original_message": "I have been feeling really stressed and overwhelmed lately.",
  "detected_language": "en",
  "detected_emotion": "sadness",
  "detected_intent": "asking_mental_health_question",
  "response": "It sounds like you're carrying a heavy burden right now...",
  "source": "RAG Model"
}
```

## Project Structure
* `api.py`: Main FastAPI application, setup of RAG pipeline, and endpoint routing.
* `classifier/`: Contains the logic for the custom classification models.
  * `intent_classifier.py`: LLM-based intent categorization and routing.
  * `language_inference.py`: Custom language detection pipeline using Naive Bayes.
  * `emotion_inference.py`: Custom emotion classifier using HuggingFace Transformers.
* `emotion-bert-final/`: Local directory housing the fine-tuned BERT emotion model.
* `locales/`: JSON files containing static, translated bot responses for non-RAG intents (greetings, out of scope, self-harm guardrails, etc.).
