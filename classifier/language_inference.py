import argparse
import joblib
import sys
import os


class LanguagePredictor:
    def __init__(self, model_path="language_detection_pipeline.joblib"):
        """Initializes the language detection model pipeline."""
        # Directory of THIS python file
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Absolute path to model
        model_full_path = os.path.join(base_dir, model_path)

        try:
            self.pipeline = joblib.load(model_full_path)

        except Exception as e:
            raise RuntimeError(
                f"Failed to load model from {model_full_path}: {e}"
            )
        

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
        default="Hello",
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