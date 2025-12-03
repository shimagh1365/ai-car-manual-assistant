from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from agents.car_agent import run_car_agent_rag
from agent import select_vehicle_via_llm
from dotenv import load_dotenv
import httpx
import json
import base64
import os
import uuid
import time
import traceback
from typing import Optional, Dict, List

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------------
# SESSION MEMORY
# ------------------------------------------------------------------------------------
SESSION_DATA: Dict[str, Dict] = {}
SESSION_TTL_SECONDS = 600

def get_session(session_id: Optional[str]):
    now = time.time()
    if not session_id or session_id == "" or session_id == "null":
        session_id = str(uuid.uuid4())

    session = SESSION_DATA.get(session_id)

    if not session:
        SESSION_DATA[session_id] = {
            "created_at": now,
            "vehicle": None,
            "history": [],
            "customerId": None,
            "first_greeting_sent": False,
            "pending_query": None,
            "pending_image": None
        }
        return session_id, SESSION_DATA[session_id]

    if now - session["created_at"] > SESSION_TTL_SECONDS:
        SESSION_DATA[session_id] = {
            "created_at": now,
            "vehicle": None,
            "history": [],
            "customerId": None,
            "first_greeting_sent": False,
            "pending_query": None,
            "pending_image": None
        }

    return session_id, SESSION_DATA[session_id]

# ------------------------------------------------------------------------------------
# AUTH & DATA
# ------------------------------------------------------------------------------------
API_BASE = os.getenv("CUSTOMER_API_BASE")
if API_BASE.endswith("/"):
    API_BASE = API_BASE[:-1]

AUTH_URL = f"{API_BASE}/api/auth/login"
CUSTOMER_URL = f"{API_BASE}/api/Quantum/customervehicles"

async def fetch_auth_token():
    def clean(val):
        return str(val).strip().replace('"', '').replace("'", "")

    payload = {
        "strDomain": clean(os.getenv("AUTH_DOMAIN")),
        "strUsername": clean(os.getenv("AUTH_USER")),
        "strPassword": clean(os.getenv("AUTH_PASS")),
    }
    
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        r = await client.post(AUTH_URL, json=payload)
        r.raise_for_status()
        return r.json()["accessToken"]

async def get_customer_data(customerId: str):
    token = await fetch_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    customerId = customerId.zfill(10)

    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        r = await client.get(CUSTOMER_URL, headers=headers, params={"customerId": customerId})
        r.raise_for_status()
        data = r.json()

    vehicles = []
    for idx, v in enumerate(data.get("vehicles", [])):
        raw_year = v.get("Vehicle_Model_Year", "")
        if raw_year and str(raw_year).strip().lower() != "null":
            year_val = str(raw_year).strip()
        else:
            year_val = "" 

        vehicles.append({
            "vehicleId": v.get("Vehicle_ID") or f"TMP_{idx}",
            "brand": v.get("Vehicle_Brand", ""),
            "model": v.get("Vehicle_Model_Description", ""),
            "year": year_val,
            "vin": v.get("Vehicle_Chassis_Number", "")
        })

    return {
        "customerId": data.get("customerId"),
        "customerName": data.get("customerName"),
        "vehicles": vehicles
    }

def first_name(name: str):
    if not name: return "there"
    return name.split(" ")[0].strip()

# ------------------------------------------------------------------------------------
# MAIN ENDPOINT
# ------------------------------------------------------------------------------------
@app.post("/detect")
async def detect_issue(
    customerId: str = Form(...),
    message: str = Form(""),
    image: Optional[UploadFile] = File(None),
    language: str = Form("en"),
    session_id: Optional[str] = Form(None)
):
    session_id, session = get_session(session_id)
    
    try:
        data = await get_customer_data(customerId)
    except Exception as e:
        print("\n\n!!!!!!!!!! API CONNECTION FAILED !!!!!!!!!!")
        print(f"Error: {str(e)}")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n")
        return {"answer": f"System Error: Could not fetch customer data. ({str(e)})", "session_id": session_id}

    vehicles = data["vehicles"]
    fname = first_name(data["customerName"])

    if session["customerId"] != data["customerId"]:
        session["created_at"] = time.time()
        session["vehicle"] = None
        session["history"] = []
        session["first_greeting_sent"] = False
        session["pending_query"] = None
        session["pending_image"] = None
        session["customerId"] = data["customerId"]

    image_base64 = None
    if image is not None and image.filename:
        image_bytes = await image.read()
        if image_bytes:
            image_base64 = base64.b64encode(image_bytes).decode()

    # -------------------------------------------------------------------------------
    # VEHICLE SELECTION
    # -------------------------------------------------------------------------------
    if len(vehicles) == 0:
        return {"answer": f"Hello {fname}. No vehicles found for ID {customerId}.", "session_id": session_id}

    if len(vehicles) == 1:
        session["vehicle"] = vehicles[0]

    elif session["vehicle"] is None:
        selection = await select_vehicle_via_llm(message, vehicles)

        if selection.get("needClarification"):
            # 1. Define Chit-Chat Greetings
            greetings = ["hi", "hello", "hey", "hola", "salam", "good morning", "good evening"]
            user_input_lower = message.strip().lower()
            
            # 2. Build Choices
            choices = "\n".join([f"- {v['year']} {v['brand']} {v['model']}" for v in vehicles])

            # 3. Save Context
            if len(message.strip()) > 1 and user_input_lower not in greetings and "202" not in message:
                session["pending_query"] = message
            
            if image_base64:
                session["pending_image"] = image_base64

            # 4. Dynamic Response (Greeting vs Issue)
            if user_input_lower in greetings:
                # --- UPDATED: REMOVED "WELCOME BACK" ---
                final_answer = (
                    f"Hello {fname}. I see you have a few vehicles with us. Which one can I assist you with today?\n\n{choices}"
                )
            else:
                final_answer = (
                    f"I can certainly help you with that, {fname}. "
                    f"To give you the correct advice, could you confirm which vehicle is experiencing this issue?\n\n{choices}"
                )

            return {
                "answer": final_answer,
                "session_id": session_id,
                "customerName": data["customerName"], 
                "customerId": data["customerId"],
                "vehicles": vehicles
            }

        selected_id = selection["vehicleId"]
        session["vehicle"] = next(v for v in vehicles if str(v["vehicleId"]) == str(selected_id))

        if session.get("pending_query"):
            message = session["pending_query"]
            session["pending_query"] = None
        
        if session.get("pending_image") and image_base64 is None:
            image_base64 = session["pending_image"]
            session["pending_image"] = None
        
        session["first_greeting_sent"] = True

    vehicle = session["vehicle"]
    
    prevent_greeting = session["first_greeting_sent"]
    session["first_greeting_sent"] = True

    # -------------------------------------------------------------------------------
    # GENERATE PROMO
    # -------------------------------------------------------------------------------
    cid_str = str(data["customerId"])
    short_id = cid_str[-5:] if len(cid_str) > 5 else cid_str
    promo_code = f"AS-{short_id}-VIP"

    # -------------------------------------------------------------------------------
    # RUN AGENT
    # -------------------------------------------------------------------------------
    answer = await run_car_agent_rag(
        message=message,
        vehicle_data=vehicle,
        image_base64=image_base64,
        language=language,
        first_name=fname,
        session_id=session_id,
        chat_history=session["history"],
        prevent_greeting=prevent_greeting,
        promo_code=promo_code
    )

    session["history"].append({"role": "user", "content": message})
    session["history"].append({"role": "assistant", "content": answer})
    session["history"] = session["history"][-20:]

    show_booking_btn = False
    if "[ACTION:BOOK]" in answer:
        show_booking_btn = True
        answer = answer.replace("[ACTION:BOOK]", "").strip()

    return {
        "answer": answer,
        "vehicle_info": vehicle,
        "customerName": data["customerName"], 
        "customerId": data["customerId"],
        "vehicles": vehicles,
        "session_id": session_id,
        "show_booking_button": show_booking_btn
    }
