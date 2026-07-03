from openai import OpenAI
from config import settings


class LLMClient:
    def __init__(self):
        self._client = OpenAI(
            api_key=settings.zhipu_api_key,
            base_url=settings.zhipu_base_url,
        )
        self._model = settings.llm_model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> dict:
        """Low temperature by default — for RAG we want the model to stick
        closely to the retrieved context, not get creative."""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return {
            "text": response.choices[0].message.content,
            "model": response.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }


_client_instance = None


def get_llm_client() -> LLMClient:
    """Singleton so we don't reconstruct the OpenAI client on every call."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient()
    return _client_instance