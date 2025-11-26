import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------------------------------------
# The ONLY function responsible for multi-vehicle selection
# -----------------------------------------------------------
async def select_vehicle_via_llm(user_message: str, vehicles: list):
    """
    Uses LLM to interpret user intent and select a vehicle.
    Returns:
        { "needClarification": True, "options": [...] }
        OR
        { "vehicleId": "12345" }
    """

    # 1. FAST PATH: Legacy strict ID check (Frontend clickable buttons)
    # Checks if the exact string 'selected_vehicle_id' is present
    if "selected_vehicle_id" in user_message.lower():
        # clean up the string to find the ID numbers
        import re
        # Extract digits after the colon or equals sign
        match = re.search(r'selected_vehicle_id[:=]\s*(\w+)', user_message)
        if match:
            extracted_id = match.group(1)
            # Verify this ID actually exists in our list
            for v in vehicles:
                if str(v["vehicleId"]) == extracted_id:
                    return {"vehicleId": v["vehicleId"]}

    # 2. INTELLIGENT PATH: LLM JSON Selection
    
    # Create a clean JSON structure for the LLM to analyze
    # We strip out irrelevant data to save tokens and reduce confusion
    vehicle_options = []
    for v in vehicles:
        vehicle_options.append({
            "id": str(v["vehicleId"]),
            "description": f"{v['year']} {v['brand']} {v['model']}"
        })

    system_prompt = f"""
    You are an intelligent intent classifier for a car support bot.
    
    TASK:
    Analyze the USER INPUT and match it to one of the AVAILABLE VEHICLES.
    
    AVAILABLE VEHICLES:
    {json.dumps(vehicle_options, indent=2)}
    
    RULES:
    1. Identify which car the user is talking about based on Model, Year, or relative terms (e.g., "the newer one", "the MG").
    2. If the user says "the newer one", compare the years.
    3. If the user says "the first one", look at the list order.
    4. If the input is vague (e.g., "my car") and there are multiple options, return null.
    5. Return JSON format ONLY.
    
    OUTPUT FORMAT:
    {{ "selected_vehicle_id": "THE_ID_HERE" }} 
    OR 
    {{ "selected_vehicle_id": null }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Use GPT-4o or 4o-mini for better logic reasoning
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={ "type": "json_object" }, # FORCE JSON
            temperature=0.0, # Strict logic, no creativity
        )
        
        # Parse the clean JSON
        result_content = response.choices[0].message.content
        result_json = json.loads(result_content)
        
        selected_id = result_json.get("selected_vehicle_id")

        if selected_id:
            # Double check the ID actually exists in our original list
            # (Prevents hallucinated IDs)
            for v in vehicles:
                if str(v["vehicleId"]) == str(selected_id):
                    return {"vehicleId": v["vehicleId"]}
        
        # If null or invalid ID, fall through to clarification
        return {
            "needClarification": True,
            "options": vehicles
        }

    except Exception as e:
        print(f"Error in select_vehicle_via_llm: {e}")
        # Fallback to clarification if AI fails
        return {
            "needClarification": True,
            "options": vehicles
        }