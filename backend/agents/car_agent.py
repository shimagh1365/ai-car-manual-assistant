import os
from openai import OpenAI
from rag.manual_search import search_manual

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Root path for manuals
MANUAL_ROOT = os.path.join("backend", "manuals", "ali-and-sons")

# ---------------------------------------------------------
# COST SAVING: Chit-Chat Detection
# ---------------------------------------------------------
CHIT_CHAT_PHRASES = [
    "hi", "hello", "hey", "greetings", "salaam", 
    "thanks", "thank you", "ok", "okay", "cool", 
    "bye", "goodbye", "start", "restart"
]

def find_best_manual_key(brand: str, model: str, year: int | str | None):
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


# =====================================================================
# MAIN AGENT
# =====================================================================
async def run_car_agent_rag(
    message: str,
    vehicle_data: dict,
    image_base64: str | None = None,
    language: str = "en",
    first_name: str = "Customer",
    session_id: str = "",
    chat_history: list = [],
    prevent_greeting: bool = False,
    promo_code: str = "VIP-GUEST",
    **kwargs,
) -> str:

    # 1. Setup Vehicle Info
    brand = vehicle_data.get("brand", "Unknown")
    model = vehicle_data.get("model", "Unknown")
    year = vehicle_data.get("year", "")
    full_vehicle_name = f"{year} {brand} {model}".strip()

    # 2. Define Search Query
    search_query = message 
    if not search_query and image_base64:
        search_query = "Identify this car part, warning light, or issue."

    # 3. Cost Optimization
    should_search = True
    clean_msg = message.strip().lower()
    if len(clean_msg) < 15 and clean_msg in CHIT_CHAT_PHRASES:
        should_search = False

    # 4. Perform RAG Search
    manual_chunks = []
    vehicle_key = find_best_manual_key(brand, model, year)

    if should_search and vehicle_key and len(search_query) > 2:
        try:
            manual_chunks = search_manual(
                brand=str(brand).lower(),
                vehicle_key=vehicle_key,
                question=search_query,
                top_k=5, 
            )
        except:
            manual_chunks = []

    if manual_chunks:
        rag_context = "\n\n".join(f"[Page {ch.get('page', '?')}] {ch.get('text', '')}" for ch in manual_chunks)
    else:
        rag_context = f"No specific manual section found. Use general knowledge about {brand} vehicles."

    # 5. Format Chat History
    formatted_history = ""
    if chat_history:
        recent = chat_history[-6:]
        formatted_history = "HISTORY:\n" + "\n".join(f"{msg['role']}: {msg['content']}" for msg in recent)

    # 6. Greeting Instruction Logic
    if chat_history:
        greeting_rule = "Do NOT greet. Do NOT mention the car name again. Go straight to the answer/next step."
    elif prevent_greeting:
        greeting_rule = f"Do NOT say 'Hello'. Start by confirming: 'Okay, regarding the {full_vehicle_name}, let's check that...'"
    else:
        greeting_rule = f"Start by explicitly welcoming {first_name} and mentioning their {full_vehicle_name}."

    # 7. System Prompt - SMART TRIAGE & PREVENTATIVE UPSELL
    system_prompt = f"""
You are an expert **Certified {brand} Service Advisor** at Ali & Sons.
You are NOT a generic AI. You are a specialist for the **{full_vehicle_name}**.

**YOUR SUPERPOWER:**
You possess a detailed mental map of the **{full_vehicle_name}**'s interior cockpit. 
When guiding the user, do not just list steps. **Visualize the driver's seat** and guide their hand to the exact location of the buttons.
{rag_context}

{formatted_history}

=========================================
PHASE 1: INTELLIGENT TRIAGE (CLASSIFY FIRST)
=========================================
Before answering, determine the severity:

1. **LEVEL 1 (Settings & Simple Consumables):** 
   - Examples: Bluetooth, Phone pairing, Wipers, Audio settings, Mirror folding, Tire pressure refill.
   - *Strategy:* Be patient. Guide them through **up to 5 steps**.

2. **LEVEL 2 (Moderate Mechanical):** 
   - Examples: AC blowing warm, Battery dead, Squeaky brakes, Vibrations, Fuse replacement.
   - *Strategy:* Be cautious. Suggest **MAXIMUM 3 basic checks** (e.g. Fuses, Fluid levels).
   - If those 3 checks fail, **STOP immediately** and push for booking.

3. **LEVEL 3 (Critical/Dangerous):** 
   - Examples: Smoke, Burning smell, Transmission slipping, Major leaks, Flashing Engine Light, Airbags.
   - *Strategy:* **IMMEDIATE STOP.** Do not offer DIY fixes. Explain the danger (Safety First) and demand a booking.

=========================================
PHASE 2: THE "GIVE UP" LOGIC
=========================================
- Look at the chat history. Have you reached the step limit for the Severity Level above?
- If YES (or if user replied "no" multiple times):
  - Stop guessing.
  - **SAY:** "We have checked the basics. Since the issue persists, this indicates a complex internal fault with the {full_vehicle_name} that requires specialized diagnostics."
  - **OFFER:** "To help, I've generated a Priority Voucher **{promo_code}** for getting a preferential rates diagnostics at Ali & Sons."
  - **TRIGGER:** Append [ACTION:BOOK]

=========================================
PHASE 3: THE "PREVENTATIVE" UPSELL (If Solved)
=========================================
- If the user says "It worked", "Fixed", or "Thanks":
  - **Do NOT just say goodbye.**
  - **SAY:** "Great job! However, since this issue occurred, it might be a symptom of a larger wear-and-tear issue. To ensure your {brand} stays in peak condition, I recommend a quick health check at Ali & Sons."
  - **TRIGGER:** Append [ACTION:BOOK] (This is optional but recommended).

=========================================
GENERAL RULES
=========================================
- **Brand Authority:** Always mention "Ali & Sons specialized {brand} tools" if the issue is complex.
- **Booking Protocol:** Never ask for dates/times. Just say "Please use the button below." and append [ACTION:BOOK].
- **Style:** One step at a time. Ask "Did that work?".

5. **Greeting Rule**: {greeting_rule}

User Query: "{search_query}"
"""

    # 8. Model Selection
    if image_base64:
        selected_model = "gpt-4o"
        user_content = [
            {"type": "text", "text": message or "Analyze this image."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
        ]
    else:
        selected_model = "gpt-4o-mini"
        user_content = message

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    response = client.chat.completions.create(
        model=selected_model,
        messages=messages,
        max_tokens=450,
        temperature=0.3,
    )

    return response.choices[0].message.content
