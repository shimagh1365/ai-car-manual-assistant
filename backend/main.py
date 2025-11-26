from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from agents.car_agent import run_car_agent_rag
from agent import select_vehicle_via_llm
from dotenv import load_dotenv
from typing import Any, List, Dict, Optional
import json
import base64
import os
import httpx

# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------
load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# SESSION STORAGE
# ---------------------------------------------------------
SESSION_SELECTED_VEHICLE = {}
SESSION_HISTORY: Dict[str, List[Dict[str, str]]] = {}
SESSION_PENDING_QUERY = {} 
SESSION_CUSTOMER_MAP = {}

# ---------------------------------------------------------
# AUTH & DATA FETCHING
# ---------------------------------------------------------
API_BASE = "https://quantum.ali-sons.com/api"
AUTH_URL = f"{API_BASE}/api/auth/login"
CUSTOMER_URL = f"{API_BASE}/api/Quantum/customervehicles"

async def fetch_auth_token():
    payload = {
        "strDomain": os.getenv("AUTH_DOMAIN", "standarduser"),
        "strUsername": os.getenv("AUTH_USER", "system_user@ali-sons.com"),
        "strPassword": os.getenv("AUTH_PASS", "a33dn@hghda3"),
    }
    
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        resp = await client.post(AUTH_URL, json=payload)
        resp.raise_for_status()
        return resp.json()["accessToken"]

async def get_customer_data(customerId: str):
    # DUMMY MODE
    if customerId == "DUMMY":
        try:
            return json.load(open("dummy_data.json", "r", encoding="utf-8"))
        except FileNotFoundError:
            return {"vehicles": [], "customerName": "Test User"}

    try:
        token = await fetch_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        clean_id = customerId.strip()
        if clean_id.isdigit() and len(clean_id) < 10:
            clean_id = clean_id.zfill(10)
            
        params = {"customerId": clean_id}

        async with httpx.AsyncClient(timeout=15, verify=False) as client:
            resp = await client.get(CUSTOMER_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            
    except Exception as e:
        print(f"API Error: {e}")
        return {"vehicles": [], "customerName": "Error fetching data"}

    vehicles = []
    for index, v in enumerate(data.get("vehicles", [])):
        v_id = v.get("Vehicle_ID", "")
        if not v_id: v_id = f"TEMP_ID_{index}" 
            
        year_val = v.get("Vehicle_Model_Year", "").strip()
        try:
            year_val = int(year_val)
        except:
            year_val = ""

        vehicles.append({
            "vehicleId": v_id,
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

def extract_first_name(full_name: str) -> str:
    if not full_name: return "there"
    return full_name.split(" ")[0].strip()

# ---------------------------------------------------------
# MAIN ENDPOINT
# ---------------------------------------------------------
@app.post("/detect")
async def detect_issue(
    customerId: str = Form(...),
    message: str = Form(""),
    image: Optional[UploadFile] = File(None),
    language: str = Form("en"),
    session_id: str = Form("default")
):
    # 1. Check & Reset Session if ID changed
    clean_incoming_id = customerId.strip()
    if clean_incoming_id.isdigit() and len(clean_incoming_id) < 10:
        clean_incoming_id = clean_incoming_id.zfill(10)

    previous_customer_id = SESSION_CUSTOMER_MAP.get(session_id)
    if previous_customer_id and previous_customer_id != clean_incoming_id:
        if session_id in SESSION_SELECTED_VEHICLE: del SESSION_SELECTED_VEHICLE[session_id]
        if session_id in SESSION_HISTORY: del SESSION_HISTORY[session_id]
        if session_id in SESSION_PENDING_QUERY: del SESSION_PENDING_QUERY[session_id]

    SESSION_CUSTOMER_MAP[session_id] = clean_incoming_id

    # 2. Fetch Data
    customer_data = await get_customer_data(clean_incoming_id)
    vehicles = customer_data.get("vehicles", [])
    first_name = extract_first_name(customer_data.get("customerName", ""))

    if not vehicles:
        return {"answer": f"Welcome {first_name}. I couldn't find any vehicles linked to ID {clean_incoming_id}."}

    vehicle = None
    just_selected_now = False 

    # 3. Car Selection Logic
    if session_id in SESSION_SELECTED_VEHICLE:
        if "switch car" in message.lower() or "change car" in message.lower():
            del SESSION_SELECTED_VEHICLE[session_id]
            vehicle = None 
        else:
            vehicle = SESSION_SELECTED_VEHICLE[session_id]
    
    elif len(vehicles) == 1:
        vehicle = vehicles[0]
        SESSION_SELECTED_VEHICLE[session_id] = vehicle
    
    else:
        selection = await select_vehicle_via_llm(message, vehicles)
        
        if selection.get("needClarification", False):
            if len(message) > 5 and "202" not in message and "switch" not in message: 
                SESSION_PENDING_QUERY[session_id] = message

            car_list_text = "\n".join([f"- {v['year']} {v['brand']} {v['model']}" for v in vehicles])
            return {
                "answer": (
                    f"Welcome back, {first_name}. I see multiple vehicles. Which one is this about?\n\n"
                    f"{car_list_text}\n\n"
                    "You can say 'the Skoda' or 'the 2017 one'."
                )
            }

        selected_id = selection.get("vehicleId")
        vehicle = next((v for v in vehicles if str(v["vehicleId"]) == str(selected_id)), None)
        
        if vehicle:
            SESSION_SELECTED_VEHICLE[session_id] = vehicle
            just_selected_now = True
        else:
            car_list_text = "\n".join([f"- {v['year']} {v['brand']} {v['model']}" for v in vehicles])
            return {"answer": f"I didn't catch that. Please select one:\n\n{car_list_text}"}

    # 4. Restore Pending Query
    image_base64 = None
    if image and image.filename:
        file_bytes = await image.read()
        image_base64 = base64.b64encode(file_bytes).decode("utf-8")

    final_message_to_process = message
    if just_selected_now and not image_base64:
        pending = SESSION_PENDING_QUERY.get(session_id)
        if pending:
            final_message_to_process = pending
            del SESSION_PENDING_QUERY[session_id]
        else:
            return {
                "answer": f"Okay, I've selected the {vehicle['year']} {vehicle['model']}. What issue are you facing?",
                "vehicle_info": vehicle
            }

    # 5. Run Agent with PREVENT_GREETING flag
    chat_history = SESSION_HISTORY.get(session_id, [])

    answer = await run_car_agent_rag(
        message=final_message_to_process,
        vehicle_data=vehicle,
        image_base64=image_base64,
        language=language,
        first_name=first_name,
        session_id=session_id,
        chat_history=chat_history,
        prevent_greeting=just_selected_now # <--- CRITICAL FIX: Pass True if we just selected the car
    )

    # Save History
    user_msg_content = "Image uploaded" if image_base64 else final_message_to_process
    chat_history.append({"role": "user", "content": user_msg_content})
    chat_history.append({"role": "assistant", "content": answer})
    
    if len(chat_history) > 20: chat_history = chat_history[-20:]
    SESSION_HISTORY[session_id] = chat_history

    # ---------------------------------------------------------
    # FINAL RETURN: Include all Context for the Frontend
    # ---------------------------------------------------------
    return {
        "answer": answer,
        "vehicle_info": vehicle,               # The specific car selected
        "customerName": customer_data.get("customerName"), # <--- ADDED
        "customerId": customer_data.get("customerId"),     # <--- ADDED
        "vehicles": vehicles                               # <--- ADDED (The full list)
    }