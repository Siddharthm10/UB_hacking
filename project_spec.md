Here is a complete project specification document for "EthiCo," designed to be used as a detailed guide for a code-generation model.

-----

### **Project Spec: "EthiCo" AI Compliance Copilot**

**1. Project Overview**

"EthiCo" is a real-time, desktop-only web application designed to act as an AI-powered copilot for debt collection agents. Its primary purpose is to monitor live calls, provide real-time compliance warnings to prevent legal violations (like FDCPA breaches), and generate post-call analytics for managers.

**2. Core Technology Stack**

  * **Frontend:** React (for desktop-only UI)
  * **Backend:** Flask (Python)
  * **Database:** MongoDB Atlas
  * **AI Services:**
      * **Google Gemini Live API:** For low-latency, bidirectional audio streaming, real-time transcription, and generative AI analysis (live warnings).
      * **ElevenLabs TTS API:** For providing low-latency, text-to-speech audio warnings to the agent.
      * **Google Gemini (Standard API):** For post-call summarization and analysis.[1, 2]
  * **PDF Generation:** ReportLab (Python).

**3. Core Features & Feasibility**

1.  **[F-01] Live Agent Copilot (The Dashboard):**

      * **Live Transcription:** Displays a real-time, color-coded transcript of the conversation (Agent vs. Customer).
      * **Live Warnings:** Displays real-time visual alerts (e.g., "RED ALERT: FDCPA Violation") and speaks audio warnings via ElevenLabs when the agent's language breaches compliance rules.
      * **Feasibility:** Achievable. This is the core "wow" demo and relies on a well-architected WebSocket connection.

2.  **[F-02] Post-Call Summary (PDF):**

      * **Summary:** Automatically generates a PDF report for each call, including a full summary, key topics, and a "Compliance Scorecard" listing all violations.
      * **Feasibility:** 100% Achievable.

3.  **[F-03] Manager Analytics Dashboard (PDF):**

      * **Agent Summary:** A manager-facing dashboard that aggregates data from all calls, showing agent performance, total violations, and trends. Includes a "Download Agent Report" (PDF) feature with charts.
      * **Feasibility:** 100% Achievable.

4.  **[F-04] Conversational Call Search (STRETCH GOAL):**

      * **Chat Interface:** A search bar for managers to ask natural-language questions (e.g., "Show me all calls where a customer threatened to sue").
      * **Feasibility:** This is a **far-fetched** feature for a 24-hour hackathon. It requires a full Retrieval-Augmented Generation (RAG) pipeline, including vector embeddings and search.
      * **Recommendation:** De-scope this from the MVP. Focus 100% on F-01, F-02, and F-03.

**4. System Architecture & Data Flow**

#### **4.1. Database (MongoDB Atlas)**

Set up a free MongoDB Atlas cluster. We will use two collections:

1.  **`agents` Collection:**
      * `{ _id: ObjectId, name: "John Doe", email: "john.doe@company.com" }`
2.  **`call_records` Collection:**
      * `{ _id: ObjectId, agent_id: ObjectId, start_time: ISODate, end_time: ISODate, full_transcript_colored: [{speaker: 'agent'|'customer', text: '...'}], summary: "...", compliance_score: 85, violations: }`

#### **4.2. Backend (Flask)**

The backend will serve both a REST API and a WebSocket server.

  * **Dependencies:** `Flask`, `flask-socketio`, `pymongo`, `google-generativeai`, `elevenlabs`, `reportlab`.
  * **WebSocket (The Live Engine):** Use `flask-socketio`.
      * The backend will manage the stateful WebSocket connection to the **Google Gemini Live API**.[3, 4]
      * **Flow:**
        1.  React client connects to Flask-SocketIO.
        2.  React streams audio chunks (Base64) to a `stream_audio` event.[5]
        3.  Flask backend receives the chunk and immediately forwards it to its open Gemini Live API session.[5]
        4.  Gemini Live API streams back JSON messages.
              * If it's an `inputTranscription` message [5], Flask emits it to React on a `'update_transcript'` event.
              * If it's an AI-generated JSON warning (based on our prompt), Flask emits it to React on a `'new_warning'` event.
              * **[Power-Up]** When a warning is emitted, the backend *also* makes an async call to **ElevenLabs TTS API** with the warning text. It streams the resulting audio back to React on a `'play_warning_audio'` event.
  * **REST API Endpoints:**
      * `POST /call/end`: Receives the full final transcript. Calls the standard Gemini API to generate the summary/violations. Saves the complete document to the `call_records` collection.
      * `GET /call/<call_id>/pdf`: Generates and streams the PDF for a single call (F-02).
      * `GET /dashboard/summary`: Runs a MongoDB Aggregation query on `call_records` to get data for F-03.
      * `GET /dashboard/pdf`: Generates and streams the manager's PDF report (F-03).

#### **4.3. Frontend (React)**

  * **Dependencies:** `react`, `react-router-dom`, `socket.io-client`, `axios`.
  * **Views (Pages):**
    1.  **`/` (LiveCopilotView):** The main agent dashboard (F-01).
    2.  **`/call/<call_id>` (CallSummaryView):** Displays the post-call report (F-02).
    3.  **`/dashboard` (ManagerDashboardView):** Displays agent analytics (F-03).
  * **Core Component (`LiveCopilot.js`):**
    1.  Uses `navigator.mediaDevices.getUserMedia({ audio: true })` to get mic access.
    2.  Establishes a connection to the Flask-SocketIO server.
    3.  Streams audio data on a set interval (e.g., every 100ms).
    4.  Listens for SocketIO events:
          * `on('update_transcript', (data) =>...)`: Appends `data.text` to the transcript state.
          * `on('new_warning', (data) =>...)`: Appends `data.warning` to the warnings list state.
          * `on('play_warning_audio', (audioChunk) =>...)`: Plays the received audio chunk using a browser `AudioContext`.

**5. Detailed Implementation "How-To"**

#### **5.1. How to Implement Live Voice Analysis (F-01)**

This is controlled by the **System Prompt** sent when opening the Google Gemini Live API session. This prompt is the "brain" of your agent.

**`gemini_system_prompt.txt` (To be loaded by Flask):**

```
You are 'EthiCo,' an AI compliance monitor for debt collection calls. You are listening to a live audio stream. Your *only* goal is to identify compliance violations and customer distress.

You MUST respond *only* in one of two formats:
1.  For simple text, you will just transcribe.
2.  If you detect a violation OR high customer distress, you MUST respond with a single, minified JSON object and *nothing else*.

**JSON Schema:**
{
  "type": "'VIOLATION' | 'SENTIMENT'",
  "level": "'CRITICAL' | 'WARNING' | 'DISTRESS'",
  "rule": "",
  "text": "",
  "suggestion_agent": ""
}

**Rules to Enforce:**
[--- Load rules from `laws_knowledge_base.py` here ---]

**Examples:**
Agent: "If you don't pay, I'll have to take your car."
YOU: {"type":"VIOLATION","level":"CRITICAL","rule":"FDCPA §807","text":"I'll have to take your car","suggestion_agent":"STOP. Do not threaten action that is not intended."}

Customer:
YOU: {"type":"SENTIMENT","level":"DISTRESS","rule":"N/A","text":"[Crying detected]","suggestion_agent":"PAUSE. Customer is highly distressed. Use empathetic language."}
```

#### **5.2. How to Implement Laws Fetching**

Do not build a web scraper. Create a static Python file `laws_knowledge_base.py` in your Flask project. This text will be injected into the Gemini system prompt.

**`laws_knowledge_base.py`:**

```python
# A static knowledge base of key FDCPA and NYS rules
# Sources:

FDCPA_RULES_TEXT = """
# FDCPA Rules (Fair Debt Collection Practices Act)
- **FDCPA §806 (Harassment or Abuse):**
  - Cannot use threats of violence.
  - Cannot use obscene or profane language.
  - Cannot call repeatedly to annoy.
- **FDCPA §807 (False Representation):**
  - Cannot falsely claim to be an attorney or government representative.
  - Cannot misrepresent the character, amount, or legal status of any debt.
  - Cannot threaten to take any action that cannot legally be taken or that is not intended to be taken.
- **FDCPA §808 (Unfair Practices):**
  - Cannot collect any amount (fee, interest) not expressly authorized by the agreement or permitted by law.

# New York State & City Rules
- **NYS Law:**
  - Cannot threaten to collect a fee over and above the debt owed.
  - Cannot communicate the nature of a debt with the debtor's employer prior to obtaining a judgment.
"""
```

#### **5.3. How to Implement Call Summary PDF (F-02)**

Use the **ReportLab** library.

**Flask Endpoint (`app.py`):**

```python
from flask import make_response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

@app.route("/call/<call_id>/pdf")
def generate_call_pdf(call_id):
    # 1. Fetch data from MongoDB
    call_data = db.call_records.find_one({"_id": call_id})
    if not call_data:
        return "Not Found", 404

    # 2. Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # (612, 792)

    # 3. Draw content
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, f"Call Summary: {call_id}")
    
    c.setFont("Helvetica", 12)
    c.drawString(72, height - 108, f"Agent: {call_data['agent_id']}")
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 144, "Violations Found:")
    
    y_position = height - 160
    if not call_data['violations']:
        c.setFont("Helvetica", 12)
        c.drawString(90, y_position, "None")
    else:
        for violation in call_data['violations']:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(90, y_position, f"Rule: {violation['rule']}")
            y_position -= 14
            c.setFont("Helvetica", 10)
            c.drawString(100, y_position, f"Text: {violation['text']}")
            y_position -= 14

    #... (Add summary, transcript, etc.)
    
    c.showPage()
    c.save()

    # 4. Stream PDF back to user
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers = f'attachment; filename={call_id}.pdf'
    return response
```

#### **5.4. How to Implement Agent Summary PDF (F-03)**

This extends F-02 by adding charts using ReportLab Graphics.

**Flask Endpoint (`app.py`):**

```python
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

@app.route("/dashboard/pdf")
def generate_dashboard_pdf():
    # 1. Fetch aggregate data from MongoDB
    # (Run an aggregation query to get violations per agent)
    # Example data:
    agent_data =

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Agent Compliance Dashboard")

    # 2. Add a Bar Chart
    drawing = Drawing(400, 200)
    data = [tuple(item['violations'] for item in agent_data)]
    
    bar_chart = VerticalBarChart()
    bar_chart.x = 50
    bar_chart.y = 50
    bar_chart.height = 125
    bar_chart.width = 300
    bar_chart.data = data
    bar_chart.categoryAxis.categoryNames = [item['name'] for item in agent_data]
    
    drawing.add(bar_chart)
    drawing.drawOn(c, 72, height - 300) # Draw chart onto the canvas
    
    c.showPage()
    c.save()
    
    # 3. Stream PDF
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.mimetype = 'application/pdf'
    response.headers = 'attachment; filename=AgentSummary.pdf'
    return response
```

### **6. Implementation Checklist (Task List)**

**Phase 1: Setup (Hours 1-2)**

  * [x] Setup React frontend (`create-react-app`).
  * [x] Setup Flask backend (`pip install flask flask-socketio...`).
  * [x] Setup MongoDB Atlas cluster and get connection string.
  * [x] Get API keys for Google Gemini and ElevenLabs.
  * [x] Define MongoDB schemas in a `models.py` file.

**Phase 2: The Live Engine (Hours 3-12)**

  * [x] **(React)** Build `LiveCopilot.js` component (basic structure).
  * [x] **(React)** Implement `navigator.mediaDevices.getUserMedia()` to capture mic audio.
  * [x] **(React)** Implement `socket.io-client` to connect to Flask (basic connection).
  * [x] **(React)** Write logic to stream audio chunks to the `'stream_audio'` socket event.
  * [x] **(Flask)** Create `flask-socketio` server (basic setup).
  * [x] **(Flask)** Create the `laws_knowledge_base.py` file with FDCPA rules.
  * [x] **(Flask)** Create the `gemini_system_prompt.txt` file.
  * [ ] **(Flask)** Write the SocketIO backend logic:
      * [ ] On client connect, open a stateful session with **Gemini Live API**.
      * [ ] On `'stream_audio'` event, forward audio to Gemini.
      * [ ] On message from Gemini, parse it.
      * [ ] `emit('update_transcript',...)` if transcription.
      * [ ] `emit('new_warning',...)` if JSON warning.
  * [x] **(React)** Build the UI to display the live transcript and warnings (basic display).

**Phase 3: The "Power-Up" (Hours 13-15)**

  * [ ] **(Flask)** In the warning-handler logic, add an async call to **ElevenLabs TTS API**.
  * [ ] **(Flask)** `emit('play_warning_audio',...)` with the resulting audio data.
  * [ ] **(React)** Write `AudioContext` logic to play the received audio stream.

**Phase 4: Post-Call & PDF Reports (Hours 16-22)**

  * [x] **(Flask)** Create `POST /call/end` endpoint (placeholder logic).
  * [ ] **(Flask)** Write the Gemini (standard API) summarization logic.
  * [x] **(Flask)** Write the `call_records.insert_one(...)` logic.
  * [x] **(React)** Add "End Call" button to `LiveCopilot.js` that hits the endpoint.
  * [x] **(Flask)** Build the `GET /call/<call_id>/pdf` endpoint using ReportLab (placeholder data).
  * [x] **(React)** Build the `CallSummaryView` page with a "Download PDF" link (basic display).
  * [x] **(Flask)** Build the `GET /dashboard/summary` endpoint (with MongoDB Aggregation, placeholder data).
  * [x] **(Flask)** Build the `GET /dashboard/pdf` endpoint (with ReportLab charts, placeholder data).
  * [x] **(React)** Build the `ManagerDashboardView` page (basic display).

**Phase 5: Polish (Hours 23-24)**

  * [ ] Style the React components for a clean desktop layout.
  * [ ] Final end-to-end testing.
