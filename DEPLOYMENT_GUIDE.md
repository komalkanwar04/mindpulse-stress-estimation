# MindPulse: Production Deployment Guide

This guide covers the best, tested deployment strategies for the **MindPulse Stress Estimation & Wellness Platform**:
1. **Option 1 (Recommended for All-in-One):** Docker & Docker Compose (Zero Configuration)
2. **Option 2 (Best for Free Cloud Deployment):** Render Blueprint (Auto-deploys ML Service, Backend & Frontend)
3. **Option 3 (Best Split Cloud Setup):** Vercel (Frontend) + Render / Railway (Backend & ML Service)

---

## Architecture Overview for Deployment

MindPulse is composed of three interconnected microservices:
- **ML & Liveness Microservice (`/ml-service`):** Python 3.10 Flask API running MediaPipe FaceMesh & Scikit-Learn Random Forest (Port `5001`).
- **Backend API (`/backend`):** Node.js Express server managing SQLite database (`backend/data.db`) & sessions (Port `4000`).
- **Frontend Client (`/frontend`):** React 18 / Vite single-page application (Port `5173` locally, Port `80` in Docker).

---

## Option 1: 1-Click Docker Compose (Local or VPS / AWS EC2 / DigitalOcean)

The fastest way to deploy all 3 tiers with a single command.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/) installed.

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/komalkanwar04/stress-estimation-platform.git
   cd stress-estimation-platform
   ```
2. Build and launch all containers in detached mode:
   ```bash
   docker compose up --build -d
   ```
3. Verify running containers:
   ```bash
   docker compose ps
   ```
4. Access the platform:
   - **Frontend UI:** `http://localhost:5173`
   - **Backend API:** `http://localhost:4000`
   - **ML Service:** `http://localhost:5001`

To stop the containers:
```bash
docker compose down
```

---

## Option 2: Render Blueprint (1-Click Cloud Hosting)

Render supports multi-tier applications using the included `render.yaml` blueprint.

### Steps
1. Push your latest code to your GitHub repository:
   ```bash
   git push origin main
   ```
2. Log into [Render](https://render.com/).
3. In the Render Dashboard, click **New +** $\to$ **Blueprint**.
4. Connect your GitHub repository: `komalkanwar04/stress-estimation-platform`.
5. Render will automatically read `render.yaml` and provision:
   - `mindpulse-ml-service` (Docker Web Service)
   - `mindpulse-backend` (Node Web Service with a 1GB persistent disk for SQLite)
   - `mindpulse-frontend` (Static Site with SPA rewrite rules)
6. Click **Apply**. Render will build and deploy all three services with public HTTPS URLs!

---

## Option 3: Split Cloud (Vercel + Render / Railway)

If you prefer Vercel's global edge CDN for the frontend:

### 1. Deploy ML Service & Backend on Render or Railway
1. **ML Service:**
   - Deploy `ml-service/` as a Docker web service.
   - Note the assigned URL: `https://mindpulse-ml-service.onrender.com`.
2. **Backend:**
   - Deploy `backend/` as a Node web service.
   - Set environment variable: `ML_SERVICE_URL=https://mindpulse-ml-service.onrender.com`.
   - Note the assigned URL: `https://mindpulse-backend.onrender.com`.

### 2. Deploy Frontend on Vercel
1. Log into [Vercel](https://vercel.com/) and click **Add New Project**.
2. Select your repository `stress-estimation-platform`.
3. Set **Root Directory** to `frontend`.
4. In **Environment Variables**, add:
   - `VITE_BACKEND_URL`: `https://mindpulse-backend.onrender.com`
   - `VITE_ML_SERVICE_URL`: `https://mindpulse-ml-service.onrender.com`
5. Click **Deploy**. Vercel will build and serve your frontend globally!

---

## Production Security & Best Practices

- **Camera Permissions (HTTPS Required):** Modern browsers block webcam access over unencrypted HTTP (except `localhost`). When deploying to production on the cloud, ensure all domains use HTTPS so the browser can access the user's camera.
- **SQLite Persistence:** The Docker and Render configurations mount a persistent volume (`/app/data`) so user baselines and session histories survive container restarts.
- **CORS Configured:** Both the Node backend and Python Flask microservice have CORS headers pre-configured to allow cross-origin requests from your frontend domain.
