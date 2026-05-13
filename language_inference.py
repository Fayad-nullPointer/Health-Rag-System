import argparse
import joblib
import sys


class LanguagePredictor:
    def __init__(self, model_path="language_detection_pipeline.joblib"):
        """Initializes the language detection model pipeline."""
        self.model_path = model_path
        try:
            # Load the scikit-learn pipeline from the joblib file
            self.pipeline = joblib.load(self.model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}")

    def predict(self, text):
        """Predicts the language of the given text."""
        # Typically, scikit-learn models expect an iterable (like a list) for text input
        if isinstance(text, str):
            text = [text]

        predictions = self.pipeline.predict(text)
        # Return the first (and only) prediction if a single string was provided
        return predictions[0]


def main():
    parser = argparse.ArgumentParser(description="Language Detection Inference")
    parser.add_argument(
        "text",
        type=str,
        nargs="?",
        default="I am learning natural language processing.",
        help="Text to detect language for",
    )
    parser.add_argument(
        "--model_path",
        type=str,
        default="language_detection_pipeline.joblib",
        help="Path to the trained joblib model",
    )

    args = parser.parse_args()

    print(f"Loading model from: {args.model_path} ...")
    try:
        predictor = LanguagePredictor(model_path=args.model_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f'\nInput text: "{args.text}"')
    result = predictor.predict(args.text)

    print(f"Predicted Language: {result}")


if __name__ == "__main__":
    main()
