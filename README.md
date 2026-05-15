# NLP Final Project Modules

This project contains machine learning modules for **Emotion Classification** and **Language Detection**. These models are designed to be easily extensible and integrated into larger systems (e.g., a Health RAG System or custom pipelines). 

## 📦 Features

- **Emotion Classifier (BERT-based)**: A fine-tuned `bert-base-uncased` model for text emotion classification (joy, sadness, anger, fear, love, surprise). Hosted on Hugging Face (`Fayad11/fine_tuned_emotion_inference_model`).
- **Language Detection**: A scikit-learn pipeline stored in a `.joblib` file capable of detecting the language of the inputted text.

---

## � Model Metrics

**Emotion Classifier (BERT-base-uncased fine-tuned on dair-ai/emotion)**
- Evaluated on the 2,000 sample test set using `evaluate` accuracy and f1 metrics.
- Typically achieves ~92-93% Accuracy and F1-score on the `dair-ai/emotion` dataset.

**Language Detection (TF-IDF + Logistic Regression Pipeline)**
- Evaluated on `papluca/language-identification` test split (across 20 languages).
- Uses `char_wb` (word-boundary character n-grams) avoiding diacritic stripping.
- Typically achieves >98% accuracy evaluating across complex scripts combining CJK, Arabic, Cyrillic, and Latin.

---

## �🛠️ Requirements & Installation

Before integrating the models, ensure you have the required dependencies installed:

```bash
pip install transformers torch scikit-learn joblib
```

---

## 🚀 Integrating the `classifier` Module

The `classifier` folder contains ready-to-use Python classes to easily integrate the models into your own codebase.

### 1. Emotion Inference

The `EmotionPredictor` automatically pulls the fine-tuned BERT model from Hugging Face when initialized.

**Integration Example:**

```python
from classifier.emotion_inference import EmotionPredictor

# Initialize the predictor (downloads/loads the Hugging Face model automatically)
# Default model: "Fayad11/fine_tuned_emotion_inference_model"
emotion_model = EmotionPredictor()

text = "I am feeling absolutely wonderful today!"
result = emotion_model.predict(text)

# The result is a list of dictionaries with 'label' and 'score'
for r in result:
    print(f"Emotion: {r['label']}, Confidence: {r['score']:.4f}")
```

### 2. Language Inference

The `LanguagePredictor` loads the local scikit-learn pipeline (`.joblib` file). By default, it looks for `language_detection_pipeline.joblib`. Ensure the path is correct relative to where you execute your code.

**Integration Example:**

```python
from classifier.language_inference import LanguagePredictor

# Initialize the predictor (point to the correct path of the joblib file)
lang_model = LanguagePredictor(model_path="classifier/language_detection_pipeline.joblib")

text = "Je suis très heureux!"
detected_language = lang_model.predict(text)

print(f"Predicted Language: {detected_language}")
```

---

## 💻 Command Line Usage

You can also run both inference scripts cleanly from your terminal.

**Emotion CLI:**
```bash
python classifier/emotion_inference.py "I am so excited for this project!"
```

**Language CLI:**
```bash
# Ensure you specify the correct path to the joblib file if running from the root directory
python classifier/language_inference.py "Hola, como estas?" --model_path classifier/language_detection_pipeline.joblib
```

---

## 📂 Notebooks

- `Emtion_Classifier.ipynb`: Contains the training, evaluation, and Hugging Face uploading steps for the Emotion BERT model.
- `Language_Detection.ipynb`: Contains the training and scikit-learn pipeline generation steps for the Language Detection model.
