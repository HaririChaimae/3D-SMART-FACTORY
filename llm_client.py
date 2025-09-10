from openai import OpenAI
import os

print("DEBUG: OPENROUTER_API_KEY =", os.getenv("OPENROUTER_API_KEY"))


api_key = os.getenv("OPENROUTER_API_KEY")  # <-- ici le nom de la variable
if not api_key:
    raise ValueError("⚠️ La variable OPENROUTER_API_KEY n'est pas définie !")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

def ask_model(prompt: str, system_prompt: str = "") -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    completion = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=messages,
        extra_headers={
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "CV Parsing App",
        }
    )
    return completion.choices[0].message.content
