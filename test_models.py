import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
KEY = "AIzaSyAwdqYCLpSOxiJnphTm3fjk36FRsPkV_UU"
genai.configure(api_key=KEY)

print("Available Models:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error fetching models: {e}")
