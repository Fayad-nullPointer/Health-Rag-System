from transformers import pipeline


class EmotionClassifier:

    def __init__(
        self,
        model_path="HagarGhazi/emotion-classifier-mental-health"
    ):

        self.classifier = pipeline(
            task="text-classification",
            model=model_path,
            tokenizer=model_path
        )

    def predict(self, text):

        result = self.classifier(text)[0]

        return {
            "emotion": result["label"],
            "score": float(result["score"])
        }