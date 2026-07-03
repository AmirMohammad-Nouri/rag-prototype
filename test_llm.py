from llm_client import get_llm_client

client = get_llm_client()
result = client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Say hello and tell me one fun fact about yourself in one sentence.",
)

print("Model:", result["model"])
print("Reply:", result["text"])
print("Usage:", result["usage"])