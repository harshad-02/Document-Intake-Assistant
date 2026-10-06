# Personal Wishes Document Assistant

An AI-powered web application that interactively guides users to create a Personal Wishes Document using Google's Gemini API. The project consists of a React (Vite) frontend and a Python (FastAPI) backend.

## Prerequisites

Before running the project, ensure you have the following installed on your computer:
1. **[Node.js](https://nodejs.org/en/download/)** (v18 or higher)
2. **[Python](https://www.python.org/downloads/)** (v3.10 or higher)
3. **Git**

You will also need a **Google Gemini API Key** to power the AI responses. You can get one for free at [Google AI Studio](https://aistudio.google.com/app/apikey).

---

## Step 1: Clone the Repository

Open your terminal (or Command Prompt / PowerShell) and run:

```bash
git clone <YOUR_GITHUB_REPO_URL_HERE>
cd "wenup project"
```

*(Note: Replace `<YOUR_GITHUB_REPO_URL_HERE>` with the actual link to your repository).*

---

## Step 2: Start the Backend Server (Terminal 1)

You will need to run the backend and frontend in separate terminal windows. In your **first terminal**, follow these steps:

1. **Navigate to the backend folder:**
   ```bash
   cd backend
   ```

2. **Create a Python Virtual Environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the Virtual Environment:**
   * **On Windows:**
     ```bash
     .\.venv\Scripts\activate
     ```
   * **On Mac/Linux:**
     ```bash
     source .venv/bin/activate
     ```

4. **Install Required Packages:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up the Environment Variables:**
   * In the `backend` folder, locate the file named `.env.example`.
   * Rename it to `.env` (or create a new copy named `.env`).
   * Open the `.env` file and add your Gemini API key:
     ```env
     LLM_PROVIDER=gemini
     GEMINI_API_KEY=your_actual_api_key_here
     ```

6. **Run the Backend Server:**
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   *Keep this terminal window open.* The backend is now running at `http://localhost:8000`.

---

## Step 3: Start the Frontend Application (Terminal 2)

Open a **new, second terminal window** and navigate back to the main project folder.

1. **Navigate to the frontend folder:**
   ```bash
   cd frontend
   ```

2. **Install Node Dependencies:**
   ```bash
   npm install
   ```

3. **Run the Development Server:**
   ```bash
   npm run dev
   ```

---

## Step 4: Open the App

Once the frontend server starts, it will output a local URL in the terminal (usually `http://localhost:5173`). 

* Hold `Ctrl` (or `Cmd` on Mac) and click the link in the terminal, or copy and paste it into your web browser.
* You can now interact with the AI assistant, fill out your Personal Wishes Document, and export it directly to PDF!

## Architecture Diagram  
<img width="7739" height="6450" alt="image" src="https://github.com/user-attachments/assets/8d0ccd3d-3953-4051-8773-ed45c2bc5467" />
