# agent.py
import re
from typing import List, Dict, Any

async def select_vehicle_via_llm(user_message: str, vehicles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic vehicle selector.
    Handles:
      - "the 2026 one", "the 2017 car"
      - "the newer one", "the older one"
      - "the latest", "the previous model"
      - "the Skoda", "the MG", "the Audi"
      - "the first one", "the second one"
      - raw ID: "selected_vehicle_id:60039" or "60039"

    Returns:
        {"vehicleId": "<id>"}       - when confident
        {"needClarification": True} - when ambiguous
    """

    # Normalize the input
    msg = (user_message or "").strip().lower()

    # If user said nothing → ask again
    if not msg:
        return {"needClarification": True, "options": vehicles}

    # Helper to safely get integer year from vehicle data
    def get_year_int(v):
        try:
            return int(v.get("year", 0))
        except:
            return 0

    # ----------------------------------------------------
    # 1) DIRECT selected_vehicle_id:XXXX
    # ----------------------------------------------------
    m = re.search(r"selected_vehicle_id[:=\s]*([a-zA-Z0-9_]+)", msg)
    if m:
        chosen = m.group(1)
        for v in vehicles:
            if str(v["vehicleId"]).lower() == chosen.lower():
                return {"vehicleId": v["vehicleId"]}

    # ----------------------------------------------------
    # 2) Raw vehicle ID in user message
    # ----------------------------------------------------
    for v in vehicles:
        if str(v["vehicleId"]).lower() in msg:
            return {"vehicleId": v["vehicleId"]}

    # ----------------------------------------------------
    # 3) Year-based resolution ("2026 one", "2025 car")
    # ----------------------------------------------------
    years_in_text = re.findall(r"\b(19\d{2}|20\d{2})\b", msg)
    if years_in_text:
        try:
            target_year = int(years_in_text[-1])
            # Compare strictly as integers
            candidates = [v for v in vehicles if get_year_int(v) == target_year]
            
            if len(candidates) == 1:
                return {"vehicleId": candidates[0]["vehicleId"]}
        except:
            pass

    # ----------------------------------------------------
    # 4) NEWER / OLDER logic
    # ----------------------------------------------------
    # Get list of valid years
    valid_years = [get_year_int(v) for v in vehicles if get_year_int(v) > 0]
    
    newest_year = max(valid_years) if valid_years else None
    oldest_year = min(valid_years) if valid_years else None

    newer_terms = [
        "newer", "new one", "latest", "new model", "new car",
        "second one", "the newer car", "the latest car", "the latest one",
        "more recent", "recent model"
    ]
    older_terms = [
        "older", "old one", "previous", "the older car",
        "first one", "the old one", "earlier model", "older model"
    ]

    if any(term in msg for term in newer_terms) and newest_year is not None:
        for v in vehicles:
            if get_year_int(v) == newest_year:
                return {"vehicleId": v["vehicleId"]}

    if any(term in msg for term in older_terms) and oldest_year is not None:
        for v in vehicles:
            if get_year_int(v) == oldest_year:
                return {"vehicleId": v["vehicleId"]}

    # ----------------------------------------------------
    # 5) Brand / model keyword matching
    # ----------------------------------------------------
    brand_candidates = []

    for v in vehicles:
        brand = str(v.get("brand") or "").lower()
        model = str(v.get("model") or "").lower()

        match = False

        # brand match
        if brand and brand in msg:
            match = True

        # token-level model match (“mg7”, “octavia”, “q7”)
        for token in re.findall(r"[a-z0-9]+", model):
            if len(token) > 1 and token in msg:
                match = True
                break

        if match:
            brand_candidates.append(v)

    if len(brand_candidates) == 1:
        return {"vehicleId": brand_candidates[0]["vehicleId"]}

    # ----------------------------------------------------
    # 6) Ordinals ("first car", "second car")
    # ----------------------------------------------------
    if len(vehicles) >= 2:
        if "first" in msg or "1st" in msg:
            return {"vehicleId": vehicles[0]["vehicleId"]}
        if "second" in msg or "2nd" in msg:
            return {"vehicleId": vehicles[1]["vehicleId"]}

    # ----------------------------------------------------
    # 7) If nothing worked → ask them again
    # ----------------------------------------------------
    return {"needClarification": True, "options": vehicles}
