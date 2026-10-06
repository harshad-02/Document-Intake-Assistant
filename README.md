# Document Intake Assistant

## 📖 Project Overview
An AI-powered web application that interactively guides users to create a Personal Wishes Document using Google's Gemini API. The system utilizes a dual-LLM architecture (an Extractor and a Responder) to hold natural conversations while strictly updating structured JSON data in real-time. 

## ✨ Features
- **Conversational Intake:** Collects complex user information naturally through chat.
- **Dual-LLM Architecture:** Uses one AI to talk to the user (Responder) and another to parse strict JSON data (Extractor).
- **Real-Time Live Preview:** Watch the Personal Wishes document generate and update instantly alongside the chat.
- **Direct Editing Panel:** Manually override, fix, or update fields extracted by the AI without typing into chat.
- **PDF Export:** Download the final generated document directly as a PDF on the client side.
- **Deterministic State Machine:** Ensures the AI asks the right questions in the right order without hallucinating flows.

## 🛠️ Tech Stack
- **Frontend:** React 19 (TypeScript), Vite, `html2pdf.js`, Vanilla CSS (Custom Glassmorphism UI)
- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pydantic
- **AI / External APIs:** Google Gemini API (`google-genai` SDK)
- **Deployment:** Vercel (Frontend SPA), Render (Backend Web Service)

## 📐 Architecture Diagram

![Architecture Diagram](./architecture.png) 
*(Note: Upload your architecture diagram image to the repository and update the path above!)*

## 📂 Folder Structure
```text
Document-Intake-Assistant/
├── backend/                  # FastAPI backend server
│   ├── app/
│   │   ├── api/              # REST API Endpoints
│   │   ├── documents/        # Logic to compile state into a Markdown document
│   │   ├── llm/              # Gemini API integrations
│   │   ├── models/           # Pydantic data schemas
│   │   └── services/         # Core business logic (State manager, Extractors)
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variables template
├── frontend/                 # React + Vite frontend application
│   ├── src/
│   │   ├── assets/           # Images and UI icons
│   │   ├── api.ts            # Typed HTTP client for the backend
│   │   ├── App.tsx           # Main Orchestrator, State, and Chat UI
│   │   ├── DocumentTemplate.tsx # Document preview renderer component
│   │   ├── EditPanel.tsx     # Direct edit form component
│   │   └── index.css         # Styling and design system
│   ├── vercel.json           # Vercel SPA routing configuration
│   └── package.json          # Node dependencies and build scripts
└── README.md                 # Project documentation
```

## 🚀 How to Run Locally

### Prerequisites
Before running the project locally, ensure you have the following installed:
1. **[Node.js](https://nodejs.org/en/download/)** (v18 or higher)
2. **[Python](https://www.python.org/downloads/)** (v3.10 or higher)
3. **Google Gemini API Key** (Get a free key at [Google AI Studio](https://aistudio.google.com/app/apikey))

### 1. Clone the Repository
Open your terminal and run:
```bash
git clone https://github.com/harshad-02/Document-Intake-Assistant.git
cd Document-Intake-Assistant
```

### 2. Start the Backend Server (Terminal 1)
You will need to run the backend and frontend in separate terminal windows. In your **first terminal**:

```bash
cd backend
python -m venv .venv
```

Activate the Virtual Environment:
* **On Windows:** `.\.venv\Scripts\activate`
* **On Mac/Linux:** `source .venv/bin/activate`

Install dependencies:
```bash
pip install -r requirements.txt
```

Set up Environment Variables:
Rename `backend/.env.example` to `.env` (or create a new `.env` file) and add your API key:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_actual_api_key_here
CORS_ORIGINS=http://localhost:5173
```

Run the server:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
*The backend is now running at `http://localhost:8000`.*

### 3. Start the Frontend Application (Terminal 2)
Open a **new, second terminal window** and navigate back to the main project folder.

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App
Once the frontend server starts, navigate to `http://localhost:5173` in your web browser. You can now chat with the AI assistant, fill out your document, and export it!
