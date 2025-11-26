# QA / Testing Guide - Ali & Sons AI Car Assistant

This document outlines the specific scenarios to verify the functionality of the AI Backend, including API integration, multi-car logic, image recognition, and session management.

## 1. Quick Setup
1.  **Dependencies:** Ensure `pip install -r requirements.txt` is run.
2.  **Environment:** Rename `.env.example` to `.env` and enter your OpenAI Key and Quantum API credentials.
3.  **Manuals:** Ensure the PDF manuals are present in `backend/manuals/ali-and-sons/`.
4.  **Run Server:** `uvicorn backend.main:app --reload`
5.  **Interface:** Open `frontend/index.html` in your browser.

---

## 2. Test Scenarios

### ✅ Scenario A: Standard User (Single Car)
*Objective: Verify API connection, Zero-padding logic, and RAG search.*

1.  **Customer ID:** Enter `11983` (System will auto-convert to `0000011983`).
2.  **Message:** "My engine light is on".
3.  **Expected Result:**
    *   **Greeting:** "Hello [Customer Name], I see you are driving a [Car Model]..."
    *   **Data:** The "Customer & Vehicle" panel on the right should populate automatically.
    *   **Answer:** A specific troubleshooting step derived from the manual.

---

### ✅ Scenario B: Multi-Car User (Ambiguity Resolution)
*Objective: Verify the bot detects multiple cars and asks for clarification.*

1.  **Customer ID:** Enter `0018073857` (This ID owns multiple vehicles).
2.  **Message:** "I hear a noise when braking".
3.  **Expected Result:**
    *   **Bot Response:** "Welcome [Name]. I see multiple vehicles (MG, Skoda...). Which one is this about?"
    *   **Context:** The bot should *not* give troubleshooting advice yet.
4.  **Follow-up:**
    *   **Message:** "The 2017 one" (or "The Skoda").
    *   **Expected Result:** Bot confirms selection and *then* provides the answer for brake noise.

---

### ✅ Scenario C: Visual Diagnosis (Image Upload)
*Objective: Verify the "Hybrid AI" logic (Switching to Vision Model).*

1.  **Customer ID:** `0000011983`.
2.  **Action:** Click the **Camera Icon** 📷 or **Attach Icon** 📎 and upload a photo of a dashboard warning light.
3.  **Message:** "What is this problem?"
4.  **Expected Result:**
    *   Bot identifies the specific warning light (e.g., "Front Assist", "Battery", "TPMS") visually.
    *   Bot provides specific steps to fix it.
    *   *Note: This confirms GPT-4o (Vision) was triggered.*

---

### ✅ Scenario D: Arabic Language Support
*Objective: Verify multi-language handling.*

1.  **Customer ID:** `0000011983`.
2.  **Settings:** Change Language dropdown to **"العربية"**.
3.  **Message:** "المكيف ما يبرد" (The AC is not cooling).
4.  **Expected Result:**
    *   Bot replies entirely in Arabic.
    *   Technical terms (Engine, AC) are correctly translated or used in context.

---

### ✅ Scenario E: Session Reset (User Switching)
*Objective: Verify that changing the ID clears the previous session.*

1.  **Step 1:** valid ID `0000011983` -> Ask a question -> Bot remembers the car.
2.  **Step 2:** Change the Customer ID input to `0018073857` -> Ask "Hi".
3.  **Expected Result:**
    *   Bot should say **"Welcome [New Name]"**.
    *   Bot should **forget** the previous car and load the new list of vehicles.

---

### ✅ Scenario F: Cost Optimization (Chit-Chat)
*Objective: Verify the system saves money on non-technical queries.*

1.  **Message:** "Hello" or "Thank you".
2.  **Expected Result:**
    *   Response should be instant (low latency).
    *   The logs should show that the **Manual Search (RAG)** was skipped to save tokens.

---

## 3. Troubleshooting

*   **Error: "Vehicles not found"**
    *   Check if the Quantum API credentials in `.env` are correct.
    *   Ensure the Customer ID is valid.
*   **Error: "I couldn't find this in the manual"**
    *   Ensure the PDF files are in `backend/manuals/ali-and-sons/[brand_name]`.
    *   Folder names must match the brand (e.g., folder `mg` for MG cars).