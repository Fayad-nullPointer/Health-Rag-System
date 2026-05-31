import os
from dotenv import load_dotenv
from deepeval.models.base_model import DeepEvalBaseLLM
from langchain_groq import ChatGroq

load_dotenv()


class GroqLLM(DeepEvalBaseLLM):

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY not found!")

        self.model = None

    # REQUIRED BY DEEPEVAL
    def load_model(self):
        self.model = ChatGroq(
            api_key=self.api_key,
            model="llama-3.3-70b-versatile"
        )
        return self.model

    # REQUIRED
    def generate(self, prompt: str) -> str:
        if self.model is None:
            self.load_model()

        return self.model.invoke(prompt).content

    # REQUIRED (async version)
    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    # REQUIRED
    def get_model_name(self):
        return "groq-llama3"