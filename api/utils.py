# api/utils.py
import os
import json
import google.generativeai as genai
# import google.generativeai as genai# Correct package import!
from django.conf import settings
from rest_framework.renderers import JSONRenderer

# --- Data: Replacing calorie_Database.json ---
# NOTE: Assumes 'calorie_Database.json' is in your project root
try:
    with open(os.path.join(settings.BASE_DIR, 'calorie_Database.json'), 'r') as f:
        # Load the data map once and use lowercased keys for robust lookup
        CALORIE_MAP = {item['name'].lower(): item for item in json.load(f)}
except FileNotFoundError:
    CALORIE_MAP = {}
    print("Warning: calorie_Database.json not found. API functions relying on it will fail.")


# --- AI Service ---

# 1. Initialize Gemini Client
# Assumes GEMINI_API_KEY is defined in your .env (settings.py should load this)
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key = API_KEY)

model = genai.GenerativeModel("models/gemini-2.5-flash")
# model.generate_content()
# 2. Define JSON Schemas for Gemini (replicated from Node.js logic)
CALORIE_TARGET_SCHEMA = {
    "type": "object",
    "properties": {
        "dailyCalories": {"type": "number"},
        "explanation": {"type": "string"},
        "macros": {
            "type": "object",
            "properties": {
                "protein": {"type": "number"},
                "carbs": {"type": "number"},
                "fats": {"type": "number"}
            }
        },
        "weeklyAdjustment": {"type": "string"}
    }
}

HEALTH_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "dailyCaloriesTarget": {"type": "number"},
        "macronutrientTarget": {
            "type": "object",
            "properties": {
                "protein": {"type": "number"},
                "carbs": {"type": "number"},
                "fats": {"type": "number"}
            }
        },
        "overallAssessment": {"type": "string"},
        "observations": {"type": "string"},
        "recommendations": {"type": "string"},
        "weeklyAdvice": {"type": "string"},
        "lifestyleTips": {"type": "string"},
        "motivationalNote": {"type": "string"}
    }
}

def process_image_with_yolo(image_path):
    """
    Placeholder for YOLO functionality required by addMeal.
    In a real project, this would use the Ultralytics Python library.
    For now, we return a predictable array of detected food names for testing.
    """
    # In a real environment, you'd load and predict here.
    # from ultralytics import YOLO
    # yolo_model = YOLO('best.pt')
    # results = yolo_model.predict(source=image_path, ...)
    
    # Placeholder data matching the expected format {name: string}
    return [{'name': 'veg briyani'}]


def generate_gemini_response(prompt, json_schema=None):
    """Generic function to call Gemini API and parse JSON output."""
    print("prompt before call")
    # model = GEMINI_CLIENT(model="gemini-2.5-flash")
    # model : 
    # print("model")
    
    config = {}
    if json_schema:
        # Use the schema to force a structured JSON output
        config["response_mime_type"] = "application/json"
        config["response_schema"] = json_schema
    result = model.generate_content(prompt, generation_config = config)
    print("result after call",result)
    
    try:
        # Clean the response text (removes markdown blocks like ```json)
        cleaned_text = result.text.strip().replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_text)
    except Exception as e:
        # Return error details if parsing fails
        return {"error": "Failed to parse AI response", "detail": str(e), "raw_text": result.text}