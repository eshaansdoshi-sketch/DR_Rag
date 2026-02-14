from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ GROQ_API_KEY not found in .env file")
    exit()

client = Groq(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "What is the capital of France?"}
        ],
    )

    print("✅ API Key is working!")
    print("Response:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ API Key is NOT working")
    print("Error:", e)