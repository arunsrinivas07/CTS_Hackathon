# ClaimGuard AI
### AI-Powered Healthcare Fraud, Waste, & Abuse (FWA) Detection Platform

ClaimGuard AI is an enterprise-grade healthcare claims fraud detection, behavioral inference, and investigation platform. Designed for insurers, CMS compliance teams, and clinical investigators, ClaimGuard leverages advanced machine learning (Medicare Provider-Level Fraud Detection V2), agentic AI copilots (RAG with ChromaDB & Groq LLM), and real-time behavioral telemetry to identify anomalous billing patterns before reimbursement.

---

## 🌟 Key Features

### 👨‍⚕️ 1. Provider Portal
- **Dynamic Time-Aware Greetings**: Personalized greetings based on local time (*Good Morning, Good Afternoon, Good Evening, Good Night*).
- **Claim Submission & Tracking**: Streamlined claim filing interface with real-time status updates and document attachments.
- **Facility Analytics**: Visual breakdown of total billed amounts, approval rates, and pending review counts.

### 🕵️‍♂️ 2. Investigator Command Center
- **ML Fraud Score & Risk Tiering**: Provider & claim risk scoring calibrated into Low, Medium, and High risk categories.
- **Explainable AI (XAI)**: Detailed model feature weight breakdowns explaining exact drivers behind fraud signals (e.g., duplicate billing, high-cost procedures, PDE anomalies).
- **Agentic AI Copilot**: RAG-driven AI assistant powered by ChromaDB & Groq LLM for asking natural language questions about CMS guidelines and claim history.
- **Agentic Investigation Traces**: Interactive timelines tracking automated evidence gathering, policy verification, and compliance checks.
- **Decision Recorder & Evidence Manager**: Log final adjudication decisions (*Approve*, *Reject*, *Flag for Audit*) with structured justification.

### 📊 3. Executive & Admin Dashboard
- **Provider Risk Matrix**: Multi-dimensional risk matrix mapping provider behavior over time.
- **Workload & Staffing Intelligence**: Case load management and investigator assignment routing.
- **System Alerts & Metrics**: Real-time operational health monitor and FWA savings projections.

---

## 🛠️ Architecture & Tech Stack

```
ClaimGuard AI
├── Frontend (React 18 + Vite + Tailwind CSS)
│   ├── Component-Driven UI & Lucide Icons
│   ├── Interactive Recharts (Bar, Pie, Workload, Risk Meters)
│   └── Context API State & API Client
│
└── Backend (FastAPI + Python 3.10+)
    ├── REST API Router Architecture (/api/v1)
    ├── Machine Learning Inference Pipeline (XGBoost / LightGBM V2)
    ├── Agentic RAG Engine (ChromaDB + Groq LLM + CMS Knowledge Base)
    └── Database & ORM (PostgreSQL + SQLAlchemy)
```

### Stack Breakdown:
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, Lucide React, Axios / Fetch API
- **Backend Framework**: Python 3.10+, FastAPI, Uvicorn, Pydantic
- **Database & Storage**: PostgreSQL, SQLAlchemy ORM, ChromaDB (Vector DB)
- **Machine Learning & AI**: Scikit-Learn, XGBoost, Pandas, NumPy, Groq API (LLM Agent), PyPDF2 / pdfplumber

---

## 📁 Repository Structure

```
ClaimGuard/
├── backend/
│   ├── app/
│   │   ├── config.py             # Application settings & environment variables
│   │   ├── database.py           # Database connection & session setup
│   │   ├── models/               # SQLAlchemy ORM database models
│   │   ├── routers/              # FastAPI endpoints (Claims, ML, Copilot, Users, etc.)
│   │   ├── services/             # ML inference, Agentic RAG, and PDF processing logic
│   │   └── seed.py               # Database initial seeder script
│   ├── main.py                   # FastAPI application entry point & startup lifecycle
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/           # Reusable UI widgets, charts, & investigator tools
│   │   ├── context/              # React Context (Auth, Investigation state)
│   │   ├── pages/                # Role-specific dashboards (Provider, Investigator, Admin)
│   │   └── services/             # Axios API service handlers
│   ├── package.json              # NPM dependencies & scripts
│   └── vite.config.js            # Vite configuration
├── .gitignore                    # Project-level git exclusion rules
└── README.md                     # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher
- **PostgreSQL**: Local or remote instance (e.g., `claimguard_db`)

---

### 2. Backend Setup

1. Navigate to the `backend` directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `backend/.env`:
   ```env
   DATABASE_URL=postgresql://postgres:password@localhost:5432/claimguard_db
   GROQ_API_KEY=your_groq_api_key_here
   SECRET_KEY=your_jwt_secret_key
   ```

5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

6. Open interactive API Documentation:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 3. Frontend Setup

1. Open a new terminal and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install NPM dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables in `frontend/.env`:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```

4. Start the frontend development server:
   ```bash
   npm run dev
   ```

5. Access the application in your web browser:
   - **URL**: [http://localhost:5173](http://localhost:5173)

---

## 🔌 API Key Routes Summary (`/api/v1`)

| Module | Endpoint | Description |
| :--- | :--- | :--- |
| **Authentication** | `POST /api/v1/auth/login` | Authenticate user & receive JWT token |
| **Claims** | `GET /api/v1/claims` | List claims (filtered by provider/status) |
| **Claims** | `POST /api/v1/claims` | Submit new claim with features |
| **ML Inference** | `POST /api/v1/ml/predict` | Single claim ML fraud risk prediction |
| **ML Inference** | `POST /api/v1/ml/predict_batch` | Multi-claim provider-level fraud scoring |
| **Copilot** | `POST /api/v1/copilot/chat` | RAG query against CMS knowledge base |
| **Investigations**| `GET /api/v1/agentic-investigations/{id}`| Fetch automated agentic trace & evidence |

---

## 🔒 Security & Best Practices
- Sensitive configuration files (`.env`), SSL keys (`*.pem`), and log files are excluded from Git via `.gitignore`.
- Database password and API tokens should be managed via environment variables.

---

## 📄 License
This project is licensed under the **MIT License**.
