from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
import json

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

import json as json_module
firebase_key_json = json_module.loads(os.getenv("FIREBASE_KEY", "{}"))
cred = credentials.Certificate(firebase_key_json)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ZoneData(BaseModel):
    zone_name: str
    weather_score: int
    employment_stress: int
    hospital_trend: int
    sentiment_score: int

CACHE = {
    "Whitefield": {"risk_level":"HIGH","risk_type":"economic distress","timeframe":"within 10 days","volunteers_needed":85,"volunteer_type":"food distribution","summary":"Whitefield shows compounding economic and weather stress. Immediate volunteer pre-positioning recommended.","confidence":81},
    "KR Puram": {"risk_level":"HIGH","risk_type":"food insecurity","timeframe":"within 8 days","volunteers_needed":95,"volunteer_type":"food distribution, financial aid","summary":"KR Puram is experiencing severe employment loss triggering food insecurity. Urgent deployment needed.","confidence":85},
    "Dharavi": {"risk_level":"HIGH","risk_type":"healthcare surge","timeframe":"within 7 days","volunteers_needed":110,"volunteer_type":"medical volunteers","summary":"Hospital admissions spiking in Dharavi. Medical volunteer surge required immediately.","confidence":88},
    "Hebbal": {"risk_level":"MEDIUM","risk_type":"shelter need","timeframe":"within 15 days","volunteers_needed":50,"volunteer_type":"shelter setup","summary":"Hebbal shows moderate combined stress. Precautionary volunteer staging advised.","confidence":74},
    "Yelahanka": {"risk_level":"HIGH","risk_type":"food insecurity","timeframe":"within 9 days","volunteers_needed":90,"volunteer_type":"food distribution","summary":"Yelahanka facing extreme weather and employment stress. High probability food crisis incoming.","confidence":86},
    "Jayanagar": {"risk_level":"LOW","risk_type":"economic distress","timeframe":"within 30 days","volunteers_needed":20,"volunteer_type":"general support","summary":"Jayanagar shows mild stress signals with no immediate crisis likely. Monitoring recommended.","confidence":72},
}

@app.get("/health")
def health():
    return {"status": "alive"}

@app.post("/explain")
async def explain_zone(data: ZoneData):
    try:
        response = model.generate_content(f"""
        You are a humanitarian crisis prediction AI.
        Analyze signals from {data.zone_name}, Bengaluru:
        Weather={data.weather_score}, Employment={data.employment_stress},
        Hospital={data.hospital_trend}, Sentiment={data.sentiment_score}
        Return ONLY raw JSON, no markdown, no backticks:
        {{"risk_level":"HIGH or MEDIUM or LOW","risk_type":"food insecurity or healthcare surge or shelter need or economic distress","timeframe":"within X days","volunteers_needed":80,"volunteer_type":"type here","summary":"2 sentences here","confidence":82}}
        """)
        result = json.loads(response.text.strip())
    except Exception:
        result = CACHE.get(data.zone_name, CACHE["Whitefield"])

    try:
        db.collection("flagged_zones").document(data.zone_name).set({
            **result,
            "zone": data.zone_name,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Firestore error: {e}")

    return result

@app.post("/brief")
async def generate_brief(data: ZoneData):
    try:
        response = model.generate_content(f"""
        Write a 3-line NGO action brief for {data.zone_name}, Bengaluru.
        Signals: weather={data.weather_score}, jobs={data.employment_stress}, hospital={data.hospital_trend}
        Format EXACTLY like this:
        ALERT: [one line crisis summary]
        ACTION: [specific volunteer task]
        DEPLOY: [number] volunteers by [timeframe]
        """)
        brief_text = response.text.strip()
    except Exception:
        volunteers = CACHE.get(data.zone_name, CACHE["Whitefield"])["volunteers_needed"]
        brief_text = f"ALERT: {data.zone_name} showing critical stress signals.\nACTION: Deploy food distribution and community support volunteers immediately.\nDEPLOY: {volunteers} volunteers within 48 hours."

    try:
        db.collection("briefs").document(data.zone_name).set({"brief": brief_text})
    except Exception as e:
        print(f"Firestore error: {e}")

    return {"brief": brief_text}

@app.get("/signals/{zone_name}")
def get_signals(zone_name: str):
    zones = {
        "Whitefield": {"weather": 78, "employment": 65, "hospital": 55, "sentiment": 70},
        "KR Puram": {"weather": 45, "employment": 80, "hospital": 60, "sentiment": 75},
        "Dharavi": {"weather": 85, "employment": 90, "hospital": 75, "sentiment": 40},
        "Hebbal": {"weather": 50, "employment": 55, "hospital": 60, "sentiment": 70},
        "Yelahanka": {"weather": 45, "employment": 50, "hospital": 55, "sentiment": 75},
        "Jayanagar": {"weather": 40, "employment": 45, "hospital": 50, "sentiment": 80},
    }
    return zones.get(zone_name, {"weather": 50, "employment": 50, "hospital": 50, "sentiment": 50})

@app.get("/history")
def get_history():
    return [
        {"event": "Bengaluru Floods 2023", "date": "October 2023", "zone": "Whitefield", "what_happened": "Heavy rainfall caused severe waterlogging affecting 50,000 residents", "signals_before": {"wea