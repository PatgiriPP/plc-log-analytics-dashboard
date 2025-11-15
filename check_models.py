import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load the .env file to get the key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file.")
    exit()

try:
    genai.configure(api_key=api_key)

    print("--- Finding models you can use ---")
    
    # List all models
    for model in genai.list_models():
        # Check if the model supports the 'generateContent' method
        if 'generateContent' in model.supported_generation_methods:
            print(f"Found usable model: {model.name}")

    print("------------------------------------")
    print("Use one of the 'Found usable model' names in your app.py file.")

except Exception as e:
    print(f"An error occurred: {e}")
    print("This could be due to an invalid API key or a network issue.")