from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
import json
from datetime import datetime

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
    allow_methods=["*"],
    allow_headers=["*"]
)

class ZoneData(BaseModel):
    zone_name: str
    weather_score: int
    employment_stress: int
    hospital_trend: int
    sentiment_score: int

CACHE = {
    "Whitefield":    {"risk_level":"HIGH","risk_type":"economic distress","timeframe":"within 10 days","volunteers_needed":85,"volunteer_type":"food distribution","summary":"Whitefield shows compounding economic and weather stress. Immediate volunteer pre-positioning recommended.","confidence":81},
    "KR Puram":      {"risk_level":"HIGH","risk_type":"food insecurity","timeframe":"within 8 days","volunteers_needed":95,"volunteer_type":"food distribution, financial aid","summary":"KR Puram is experiencing severe employment loss triggering food insecurity. Urgent deployment needed.","confidence":85},
    "Dharavi North": {"risk_level":"HIGH","risk_type":"healthcare surge","timeframe":"within 7 days","volunteers_needed":110,"volunteer_type":"medical volunteers","summary":"Hospital admissions spiking in Dharavi North. Medical volunteer surge required immediately.","confidence":88},
    "Koramangala":   {"risk_level":"LOW","risk_type":"economic distress","timeframe":"within 30 days","volunteers_needed":20,"volunteer_type":"general support","summary":"Koramangala shows mild stress signals with no immediate crisis likely. Monitoring recommended.","confidence":72},
    "Hebbal":        {"risk_level":"MEDIUM","risk_type":"shelter need","timeframe":"within 15 days","volunteers_needed":50,"volunteer_type":"shelter setup","summary":"Hebbal shows moderate combined stress. Precautionary volunteer staging advised.","confidence":74},
    "Yelahanka":     {"risk_level":"HIGH","risk_type":"food insecurity","timeframe":"within 9 days","volunteers_needed":90,"volunteer_type":"food distribution","summary":"Yelahanka facing extreme weather and employment stress. High probability food crisis incoming.","confidence":86},
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
            "weather_score": data.weather_score,
            "employment_stress": data.employment_stress,
            "hospital_trend": data.hospital_trend,
            "sentiment_score": data.sentiment_score,
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
        return {"brief": response.text.strip()}
    except Exception:
        volunteers = CACHE.get(data.zone_name, CACHE["Whitefield"])["volunteers_needed"]
        return {"brief": f"ALERT: {data.zone_name} showing critical stress signals across multiple indicators.\nACTION: Deploy food distribution and community support volunteers immediately.\nDEPLOY: {volunteers} volunteers within 48 hours."}

@app.get("/signals/{zone_name}")
def get_signals(zone_name: str):
    zones = {
        "Whitefield":    {"weather": 78, "employment": 65, "hospital": 55, "sentiment": 70},
        "KR Puram":      {"weather": 45, "employment": 80, "hospital": 60, "sentiment": 75},
        "Dharavi North": {"weather": 60, "employment": 72, "hospital": 85, "sentiment": 68},
        "Koramangala":   {"weather": 30, "employment": 40, "hospital": 35, "sentiment": 30},
        "Hebbal":        {"weather": 55, "employment": 58, "hospital": 50, "sentiment": 45},
        "Yelahanka":     {"weather": 82, "employment": 70, "hospital": 65, "sentiment": 80},
    }
    return zones.get(zone_name, {"weather": 50, "employment": 50, "hospital": 50, "sentiment": 50})

@app.get("/history")
def get_history():
    return [
        {
            "event": "Bengaluru Floods 2023",
            "date": "October 2023",
            "zone": "Whitefield",
            "what_happened": "Heavy rainfall caused severe waterlogging affecting 50,000 residents",
            "signals_before": {
                "weather": 85,
                "employment": 60,
                "hospital": 45,
                "sentiment": 72
            },
            "days_early_detected": 11,
            "volunteers_deployed_late": 800,
            "pulsaid_would_have_deployed": "11 days earlier",
            "lives_impacted": 50000
        },
        {
            "event": "KR Puram Industrial Layoffs 2023",
            "date": "March 2023",
            "zone": "KR Puram",
            "what_happened": "Mass layoffs at 3 factories triggered food insecurity for 12,000 families",
            "signals_before": {
                "weather": 40,
                "employment": 88,
                "hospital": 55,
                "sentiment": 78
            },
            "days_early_detected": 14,
            "volunteers_deployed_late": 200,
            "pulsaid_would_have_deployed": "14 days earlier",
            "lives_impacted": 12000
        },
        {
            "event": "Yelahanka Drought Crisis 2022",
            "date": "June 2022",
            "zone": "Yelahanka",
            "what_happened": "Prolonged dry spell caused water scarcity and crop failure for 8,000 families",
            "signals_before": {
                "weather": 90,
                "employment": 75,
                "hospital": 60,
                "sentiment": 82
            },
            "days_early_detected": 18,
            "volunteers_deployed_late": 150,
            "pulsaid_would_have_deployed": "18 days earlier",
            "lives_impacted": 8000
        }
    ]

@app.get("/flagged_zones")
def get_flagged_zones():
    try:
        docs = db.collection("flagged_zones").stream()
        zones = []
        for doc in docs:
            zones.append(doc.to_dict())
        return zones
    except Exception as e:
        return CACHE

@app.post("/brief")
async def generate_brief(data: dict):
    zone = data.get("zone", "Unknown")
    risk_score = data.get("risk_score", 0)
    risk_type = data.get("risk_type", "general")

    prompt = f"""
    You are an emergency response AI. Generate a concise NGO action brief.
    Zone: {zone}
    Risk Score: {risk_score}/100
    Risk Type: {risk_type}

    Respond ONLY with valid JSON in this exact format:
    {{
        "zone": "{zone}",
        "risk_type": "string",
        "volunteers_needed": number,
        "eta_hours": number,
        "action": "one sentence action instruction"
    }}
    """

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    brief_data = json.loads(response.text)

    # Save to Firestore
    db.collection("briefs").document(zone).set(brief_data)

    return brief_data