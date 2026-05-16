import argparse
import joblib
import sys

try:
    from . import preprocessor
except ImportError:
    import preprocessor
# --- Model Predictor ---


class LanguagePredictor:
    def __init__(
        self, model_path="classifier/language_detection_pipeline_naive_bayes.joblib"
    ):
        """Initializes the language detection model pipeline."""
        self.model_path = model_path
        try:
            self.pipeline = joblib.load(self.model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}")

    def predict(self, text):
        """Predicts the language of the given text."""
        # Ensure we always pass an iterable (list) to the pipeline
        if isinstance(text, str):
            text = preprocessor.preprocess(text)
            input_text = [text]
        elif isinstance(text, list):
            input_text = [preprocessor.preprocess(t) for t in text]
        else:
            raise ValueError("Input must be a string or a list of strings")

        predictions = self.pipeline.predict(input_text)

        if isinstance(text, str):
            return predictions[0]
        return predictions


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
        default="classifier/language_detection_pipeline_naive_bayes.joblib",
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
