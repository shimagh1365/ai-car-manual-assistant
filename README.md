# Ali & Sons AI Car Service Assistant (Backend)

## Overview
This is a **FastAPI-based Microservice** designed to act as an intelligent Virtual Service Advisor. It integrates with the **Quantum API** to authenticate customers, retrieve their vehicle details, and provide context-aware troubleshooting using **RAG (Retrieval-Augmented Generation)** on official car manuals.

The system is designed for **high efficiency and low cost**, utilizing a hybrid AI approach (Text vs. Vision).

## Key Features

*   **🔌 Quantum API Integration:** Securely authenticates and fetches customer/vehicle data using `customerId` (Auto-pads IDs, e.g., `11983` -> `0000011983`).
*   **🧠 Cost-Optimized Hybrid AI:**
    *   Uses **GPT-4o-mini** for standard text queries (Low cost, high speed).
    *   Automatically switches to **GPT-4o (Vision)** only when an image is uploaded.
    *   Bypasses expensive RAG searches for chit-chat ("Hello", "Thanks").
*   **📚 RAG (Retrieval-Augmented Generation):** Searches specific PDF car manuals to provide accurate, manufacturer-approved troubleshooting steps.
*   **🗣️ Multi-Language Support:** Automatically detects and answers in **English** or **Arabic**.
*   **🔄 Session State Management:** Handles context for:
    *   Multi-car owners (asks for clarification).
    *   Conversation history (remembers previous questions).
    *   Automatic session reset when the Customer ID changes.

---

## 🛠️ Tech Stack
*   **Framework:** Python 3.11 + FastAPI
*   **AI Engine:** OpenAI (GPT-4o / GPT-4o-mini)
*   **Vector Search:** Local FAISS/NumPy-based embedding search
*   **PDF Processing:** `pypdf`
*   **HTTP Client:** `httpx` (Async)

---

## 🚀 Setup & Installation

### 1. Prerequisites
*   Python 3.10 or higher
*   An OpenAI API Key
*   Access credentials for the Quantum API

### 2. Local Installation
1.  **Unzip the package** and navigate to the folder:
    ```bash
    cd ai-car-assistant
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration:**
    *   Rename `.env.example` to `.env`.
    *   Add your API keys inside `.env`:
    ```ini
    OPENAI_API_KEY=sk-proj-xxxx...
    AUTH_USER=system_user@ali-sons.com
    AUTH_PASS=your_password
    ```

4.  **Add Manuals:**
    *   Ensure PDF manuals are placed in: `backend/manuals/ali-and-sons/`
    *   *Note: The system matches folder names (e.g., 'mg', 'skoda') to the vehicle brand.*

5.  **Run the Server:**
    ```bash
    uvicorn backend.main:app --reload
    ```
    The API will start at: `http://127.0.0.1:8000`

---

## 🐳 Docker Deployment
To run this as a microservice container:

1.  **Build the Image:**
    ```bash
    docker build -t ai-car-assistant .
    ```

2.  **Run the Container:**
    ```bash
    docker run -d -p 8000:8000 --env-file .env ai-car-assistant
    ```

---

## 🔌 API Documentation

Once the server is running, full Swagger UI documentation is available at:
**URL:** `http://127.0.0.1:8000/docs`

### Main Endpoint: `POST /detect`

**Parameters (Form-Data):**

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `customerId` | String | Yes | The user's ID (e.g., "11983"). System auto-pads zeros. |
| `message` | String | Yes | The user's question (e.g., "Check engine light is on"). |
| `session_id` | String | Yes | A unique UUID to track conversation history. |
| `image` | File | No | Optional image upload for visual diagnosis. |
| `language` | String | No | 'en' or 'ar' (Default: 'en'). |

**Sample Response:**
```json
{
  "answer": "Hello Ahmed, I see the check engine light is on...",
  "vehicle_info": {
    "year": 2017,
    "brand": "Skoda",
    "model": "Octavia"
  },
  "customerName": "Ahmed Ismail",
  "customerId": "0000011983",
  "vehicles": [...]
}

Project Structure
/
├── backend/
│   ├── agents/           # AI Logic (Hybrid Text/Vision)
│   ├── manuals/          # PDF Storage
│   ├── rag/              # Manual Search Logic
│   └── main.py           # API Entry Point & Session Logic
├── frontend/             # Demo HTML Client
├── requirements.txt      # Python Dependencies
├── Dockerfile            # Container Configuration
└── TESTING_GUIDE.md      # QA Scenarios

🧪 Testing
Please refer to TESTING_GUIDE.md for specific Customer IDs and scenarios to verify (Single Car, Multi-Car, Image Upload, etc.).

