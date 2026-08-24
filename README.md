# ClaimGuard AI
### AI-Powered Healthcare Fraud, Waste, & Abuse (FWA) Detection Platform

ClaimGuard AI is an enterprise-grade healthcare claims fraud detection, behavioral inference, and investigation platform. Designed for insurers, CMS compliance teams, and clinical investigators, ClaimGuard leverages advanced machine learning (Medicare Provider-Level Fraud Detection V2), agentic AI copilots (RAG with ChromaDB & Groq LLM), and real-time behavioral telemetry to identify anomalous billing patterns before reimbursement.

---

🌐 **Live Application Deployment**: [http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com](http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com)

---

## 🎥 Video Prototype & Demo

[![Watch Prototype Video](https://img.youtube.com/vi/sSnHwhqKP6k/maxresdefault.jpg)](https://youtu.be/sSnHwhqKP6k?si=w7dbHq5-FdvQ_oHf)

📺 **YouTube Video Prototype**: [https://youtu.be/sSnHwhqKP6k?si=w7dbHq5-FdvQ_oHf](https://youtu.be/sSnHwhqKP6k?si=w7dbHq5-FdvQ_oHf)

---

## 🏗️ System Architecture

![Overall Architecture](images/architecture.jpeg)

*Figure 1: ClaimGuard AI Overall System Architecture & Data Flow*

---

## 💻 Tech Stack

![Tech Stack](images/techstack.png)

*Figure 2: Component Breakdown & Technology Stack*

### Tech Stack Details:
- **Frontend**: React 18, Vite, Tailwind CSS, Recharts, Lucide Icons, Axios
- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic, SQLAlchemy ORM
- **Database & Vector Store**: PostgreSQL, ChromaDB (RAG Embeddings)
- **AI & Machine Learning**: Scikit-Learn, XGBoost, LightGBM, Groq LLM API, PyPDF2 / pdfplumber
- **Cloud Deployment**: AWS EC2 Deployment (`http://15.207.248.42`)

---

## 📸 Application Screenshots

<div align="center">
  <img src="images/1.png" alt="Provider Dashboard" width="48%" />
  <img src="images/2.png" alt="Investigator Command Center" width="48%" />
</div>

<br/>

<div align="center">
  <img src="images/3.png" alt="AI Copilot & Investigation Workspace" width="48%" />
  <img src="images/4.png" alt="Executive Analytics & Risk Matrix" width="48%" />
</div>

---

## 🌟 Key Features

### 👨‍⚕️ 1. Provider Portal
- **Time-Aware Dynamic Greetings**: Personalized greetings matching local time (*Good Morning, Good Afternoon, Good Evening, Good Night*).
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

## 🌐 Environment Configuration

### Frontend Configuration (`frontend/.env`)
Configured to point to the AWS EC2 production backend endpoint:
```env
VITE_API_URL=http://15.207.248.42
```

### Backend Configuration (`backend/.env`)
Configured to run locally on your development machine:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/claimguard
SECRET_KEY=claimguard_super_secret_jwt_key_2026_production
GROQ_API_KEY=your_groq_api_key
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: 18.x or higher
- **PostgreSQL**: Local or remote database instance

---

### 2. Backend Setup (Localhost)

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

4. Run the local FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. Open interactive API Documentation:
   - **Local Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **AWS Backend Swagger UI**: [http://15.207.248.42/docs](http://15.207.248.42/docs)

---

### 3. Frontend Setup

1. Navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```

2. Install NPM dependencies:
   ```bash
   npm install
   ```

3. Start the frontend development server:
   ```bash
   npm run dev
   ```

4. Access the application in your web browser:
   - **Live Deployed Application**: [http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com](http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com)
   - **Local Development URL**: [http://localhost:5173](http://localhost:5173)

---

## 🔌 API Core Routes Summary (`/api/v1`)

| Module | Endpoint | Description |
| :--- | :--- | :--- |
| **Authentication** | `POST /api/v1/auth/login` | Authenticate user & receive JWT token |
| **Claims** | `GET /api/v1/claims` | List claims (filtered by provider/status) |
| **Claims** | `POST /api/v1/claims` | Submit new claim with features |
| **ML Inference** | `POST /api/v1/ml/predict` | Single claim ML fraud risk prediction |
| **ML Inference** | `POST /api/v1/ml/predict_batch` | Multi-claim provider-level fraud scoring |
| **Copilot** | `POST /api/v1/copilot/chat` | RAG query against CMS knowledge base |
---

## ☁️ AWS Cloud Infrastructure & Deployment

ClaimGuard AI is fully deployed on Amazon Web Services (AWS) using a high-availability microservices architecture:

- **Frontend Application**: Built with React/Vite and static website hosting deployed on **AWS S3 + CloudFront** ([http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com](http://claimguard-frontend-prod.s3-website.ap-south-1.amazonaws.com)).
- **Backend API Service**: High-performance FastAPI application deployed on an **AWS EC2** instance ([http://15.207.248.42](http://15.207.248.42)).
- **Machine Learning Microservice**: Dockerized ML inference pipeline containerized and deployed on **AWS ECS (Elastic Container Service)** for scalable provider risk inference.
- **Managed Database**: Production-grade **PostgreSQL** hosted on **AWS RDS** (`claimguard-db.cjiuk0qk4zkc.ap-south-1.rds.amazonaws.com:5432`).
