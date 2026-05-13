import argparse
from transformers import pipeline
import sys


class EmotionPredictor:
    def __init__(self, model_path="./emotion-bert-final"):
        """Initializes the emotion classifier pipeline."""
        self.model_path = model_path
        try:
            self.classifier = pipeline(
                "text-classification", model=self.model_path, tokenizer=self.model_path
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}")

    def predict(self, text):
        """Predicts the emotion of the given text."""
        return self.classifier(text)


def main():
    parser = argparse.ArgumentParser(description="Emotion Classifier Inference")
    parser.add_argument(
        "text",
        type=str,
        nargs="?",
        default="I can't believe how happy I am today!",
        help="Text to classify",
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default="./emotion-bert-final",
        help="Path to the trained model directory",
    )

    args = parser.parse_args()

    print(f"Loading model from: {args.model_path} ...")
    try:
        predictor = EmotionPredictor(model_path=args.model_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f'\nInput text: "{args.text}"')
    result = predictor.predict(args.text)

    # Check output and display
    for r in result:
        print(f"Predicted Emotion: {r['label']} (Confidence Score: {r['score']:.4f})")


if __name__ == "__main__":
    main()
