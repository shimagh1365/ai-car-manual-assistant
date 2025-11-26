import os
from openai import OpenAI
from rag.manual_search import search_manual

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MANUAL_ROOT = os.path.join("backend", "manuals", "ali-and-sons")

# ---------------------------------------------------------
# CONSTANTS FOR COST SAVING
# ---------------------------------------------------------
# If user says these, DO NOT search the manual.
CHIT_CHAT_PHRASES = [
    "hi", "hello", "hey", "hola", "greetings", 
    "thanks", "thank you", "thx", "ok", "okay", 
    "bye", "goodbye", "cool", "great"
]

def find_best_manual_key(brand: str, model: str, year: int | str | None):
    # (Keep this function exactly the same as before)
    if not brand: return None
    brand_clean = str(brand).lower().strip()
    model_clean = str(model or "").lower().strip()
    year_str = str(year or "").strip()
    
    if not os.path.exists(MANUAL_ROOT): return None
    
    found_brand_folder = None
    for folder_name in os.listdir(MANUAL_ROOT):
        if folder_name.lower() == brand_clean:
            found_brand_folder = os.path.join(MANUAL_ROOT, folder_name)
            break
    if not found_brand_folder: return None

    pdf_files = [f.replace(".pdf", "") for f in os.listdir(found_brand_folder) if f.lower().endswith(".pdf")]
    best_match = None
    best_score = 0

    for key in pdf_files:
        key_l = key.lower()
        score = 0
        if model_clean and model_clean in key_l: score += 5
        if year_str and year_str in key_l: score += 3
        if model_clean.replace(" ", "") in key_l.replace(" ", ""): score += 2
        if score > best_score:
            best_score = score
            best_match = key
    return best_match if best_score > 0 else None


async def run_car_agent_rag(
    message: str,
    vehicle_data: dict,
    image_base64: str | None = None,
    language: str = "en",
    first_name: str = "Customer",
    session_id: str = "default",
    chat_history: list = [],
    prevent_greeting: bool = False, 
    **kwargs,
) -> str:

    # 1. Setup Data
    brand = vehicle_data.get("brand", "Unknown Brand")
    model = vehicle_data.get("model", "Unknown Model")
    year = vehicle_data.get("year", "Unknown Year")
    full_vehicle_name = f"{year} {brand} {model}"

    # ---------------------------------------------------------
    # COST OPTIMIZATION 1: SKIP MANUAL ON CHIT-CHAT
    # ---------------------------------------------------------
    should_search_manual = True
    clean_msg = message.strip().lower()
    
    # If message is short and in chit-chat list, skip manual
    if len(clean_msg) < 15 and clean_msg in CHIT_CHAT_PHRASES:
        should_search_manual = False
    
    # If searching about ownership
    if "which car" in clean_msg or "what car" in clean_msg:
        should_search_manual = False

    # 2. Search Manual (Only if needed)
    vehicle_key = find_best_manual_key(brand, model, year)
    search_query = message 
    if not search_query and image_base64:
        search_query = "Identify this car part and maintenance"

    manual_chunks = []
    rag_context = ""

    if should_search_manual and vehicle_key and search_query and len(search_query) > 2:
        try:
            manual_chunks = search_manual(
                brand=str(brand).lower(),
                vehicle_key=vehicle_key,
                question=search_query,
                top_k=4, 
            )
        except:
            manual_chunks = []

    if manual_chunks:
        rag_context = "\n\n".join(f"[Page {ch.get('page', '?')}] {ch.get('text', '')}" for ch in manual_chunks)
    else:
        # If we skipped search, explicitly leave context empty
        rag_context = ""

    # 3. History
    formatted_history = ""
    if chat_history:
        recent_history = chat_history[-6:] 
        formatted_history = "PREVIOUS CHAT:\n" + "\n".join(f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history)

    # 4. Greeting Logic
    if not chat_history and not prevent_greeting:
        greeting_instruction = f"Start explicitly by welcoming {first_name} and mentioning their vehicle ({full_vehicle_name})."
    elif prevent_greeting:
        greeting_instruction = f"Do NOT say 'Hello'. Start by simply confirming the car: 'Okay, regarding the {full_vehicle_name}, let's check that...'"
    else:
        greeting_instruction = "Do NOT greet the user again. Go straight to the answer."

    # ---------------------------------------------------------
    # COST OPTIMIZATION 2: MODEL SELECTION
    # ---------------------------------------------------------
    # Use GPT-4o ONLY if there is an image (Vision required).
    # Use GPT-4o-mini for text (30x Cheaper).
    selected_model = "gpt-4o-mini" 
    if image_base64:
        selected_model = "gpt-4o"

    # System Prompt
    system_prompt = f"""
You are an expert Car Service Advisor for Ali & Sons.

CURRENT USER VEHICLE: {full_vehicle_name}
Language: {language}
Context from Manual: {rag_context}

{formatted_history}

CRITICAL RULES:
1. **Greeting**: {greeting_instruction}
2. **Interactive Mode**: Give ONLY the first logical troubleshooting step.
3. **Simple Language**: Explain like you are talking to a non-expert.
4. **Safety**: If context is empty, give general safe advice.
5. **Context**: If 'Context from Manual' is empty, answer using your general automotive knowledge.

User Query: "{search_query}"
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if image_base64:
        user_content = [
            {"type": "text", "text": message or "Analyze this image."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=selected_model,
        messages=messages,
        temperature=0.3, 
        max_tokens=300, 
    )

    return response.choices[0].message.content