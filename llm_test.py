

from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()  

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")


client = OpenAI(
    api_key= ZHIPU_API_KEY,
    base_url="https://open.bigmodel.cn/api/paas/v4/",  
)

MODEL = "glm-4.5-flash"

def main():
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello and tell me one fun fact about yourself in one sentence."},
        ],
        temperature=0.7,
    )
    print("Model:", response.model)
    print("Reply:", response.choices[0].message.content)
    print("Usage:", response.usage)


def streaming_example():
    """Optional: streaming response example."""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Count from 1 to 5."}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
    streaming_example()  # uncomment to try streaming