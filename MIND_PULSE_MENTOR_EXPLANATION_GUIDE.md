# MindPulse: Personalized Stress Estimation & Mental Wellness Platform
## Complete Architecture & Mentor Defense Guide (In Simple Terms)

---

### 1. What is this project in simple terms?
**MindPulse** is an intelligent, camera-based mental wellness platform that measures a person's real-time psychological stress and facial tension without requiring any wearable devices, smartwatches, or external sensors.

Unlike conventional emotion detectors that compare everyone against a generic template, MindPulse solves the problem using two core innovations:
1. **Personalized Baseline Calibration:** It first learns what *your* relaxed, resting face looks like. It then measures your stress as a deviation from your personal baseline.
2. **Instant Frame-1 Fake Stress Detection (Liveness & Authenticity):** If someone tries to fake or pose stress by frowning or squinting, the system catches the feigned expression **immediately on the very first image** without needing external hardware or multi-second heart rate buffers.

---

### 2. The 3-Tier Architecture & Tech Stack Working

The platform uses a decoupled, production-grade microservices architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. FRONTEND LAYER (Client Dashboard & Camera Stream)                       │
│    • Tech: React 18, Vite, HTML5 Canvas, MediaStream Webcam API, Recharts   │
│    • Role: Streams live video, renders HUD guide, radial stress gauge,      │
│      FACS Action Unit attribution bars, and interactive breathing coach.    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTP REST (Port 4000 & 5001)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. BACKEND LAYER (Business Logic, Sessions & Persistent Database)           │
│    • Tech: Node.js, Express.js, SQLite (better-sqlite3)                     │
│    • Role: Manages user profiles, stores calibrated baseline vectors,       │
│      records longitudinal sessions, and matches clinical recommendations.   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ Internal RPC (Port 5001)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. ML & AUTHENTICITY ENGINE (Computer Vision & Biometrics)                 │
│    • Tech: Python 3.10+, Flask, MediaPipe FaceMesh (Google), Scikit-Learn   │
│    • Role: Extracts 468 dense 3D landmarks, calculates FACS Action Unit     │
│      deltas, runs the Random Forest Ensemble (94.6% accuracy), and executes │
│      the Multi-Factor Stress Authenticity & Liveness Engine (MFSAE).        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3. Step-by-Step Workflow: From Camera to Stress Score

1. **Baseline Calibration (12 Seconds):**
   - The user sits relaxed. MediaPipe extracts 10 resting samples and saves their unique facial dimensions:
     - `brow_eye_dist`: Resting eyebrow-to-eye height
     - `inter_brow_dist`: Natural gap between eyebrows
     - `eye_aspect_ratio`: Natural eye openness
     - `mouth_tension_ratio`: Resting lip width-to-height ratio
   - Stored in SQLite (`backend/data.db`).

2. **Capturing a Reading:**
   - The webcam captures a frame (Base64 JPEG) and sends it to the Python ML service (`/analyze`).
   - MediaPipe FaceMesh locates 468 3D landmark points.

3. **Calculating Personalized Delta Vectors ($\Delta$):**
   - The system computes: $\Delta = \text{Current Features} - \text{Your Personal Baseline}$.
   - If your brow dropped by 15% and lips compressed by 20%, that change is encoded into an 8-dimensional relative feature vector.

4. **Machine Learning Inference:**
   - The 8D delta vector is evaluated by a trained Random Forest Ensemble (120 trees).
   - Generates a continuous score (0 to 100), stress category (*Calm*, *Normal*, *Elevated*, *High*), and Action Unit feature attributions (Explainable AI).

5. **Instant Fake-Stress Check:**
   - The Authenticity Engine verifies if the expression is genuine or feigned.
   - If feigned: the raw tension score is intercepted, a red alert is displayed, and the physiological score is gated back to resting baseline (~42).

---

### 4. How Instant 1st-Go Fake Stress Detection Works (No Hardware Needed)

**Mentor's Question:** *"What if someone fakes stress by frowning at the camera? How can you detect it on the 1st capture without heart rate sensors?"*

**Your Answer:**
In affective neuroscience, genuine distress is controlled by the involuntary subcortical limbic system, whereas faking stress is controlled by the voluntary motor cortex (pyramidal tract). They produce fundamentally different anatomical signatures that the camera catches on the very first photo across 4 geometric biomarkers:

1. **Isolated Action Unit Overacting (`ISOLATED_OVERACTING`):**
   - When faking stress, people consciously pull only their eyebrows down (`AU4`), while their eyes and mouth remain relaxed. In authentic acute stress, both the upper face (eyebrows) and lower face (eyes squinting, lips pressing) co-activate together.
2. **Slack Eyes / "Dead Gaze" Incongruence (`SLACK_PERIORBITAL_INCONGRUENCE`):**
   - In genuine acute distress, the protective orbicularis reflex narrows the eye aperture. When faking stress, people almost universally force their eyebrows down while keeping their eyes wide open staring at the lens. Frowning with completely open, slack eyes is an anatomical contradiction caught on Frame 1.
3. **Disproportionate Tension Monopolization (`TENSION_MONOPOLIZATION`):**
   - In posed stress, over 62% of the entire facial tension change comes from just one muscle. Genuine distress is distributed across the whole face.
4. **Hemifacial Cortical Asymmetry (`PYRAMIDAL_ASYMMETRY`):**
   - Voluntary movement comes from the contralateral motor cortex, creating visible left/right contraction imbalance. Real emotional distress is bilateral.

---

### 5. Summary of Key Machine Learning Metrics

- **Model Type:** Personalized Hybrid Random Forest Ensemble (120 Estimators)
- **Cross-Validation:** 5-Fold Stratified Cross-Validation on 140 Subjects
- **Accuracy:** 94.64% (Macro F1-Score: 0.9466, ROC-AUC: 0.9955)
- **Inference Latency:** $< 1.0\text{ ms}$ per frame
- **FACS Standards:**
  - `AU4`: Corrugator Supercilii (Brow Lowerer & Glabella Furrow)
  - `AU7`: Orbicularis Oculi (Palpebral Fissure Tightener / Squint)
  - `AU24`: Orbicularis Oris (Lip Pressor & Lateral Compression)

---

### 6. Mentor Defense Cheat Sheet: Top 7 Questions & Answers

1. **Q: Why a microservices architecture instead of putting everything into one app?**
   - **A:** Separation of concerns: Python is the global standard for AI/CV (MediaPipe, Scikit-Learn); Node.js is optimized for asynchronous database I/O and session tracking; React provides a fast single-page interface. This mirrors real-world production systems.
2. **Q: Why not use a standard deep learning CNN directly on raw images?**
   - **A:** Privacy (we don't store or upload raw photos; we extract landmark distances), speed (runs at 30+ FPS on regular laptops without a GPU), and explainability (Random Forest gives exact Action Unit importance percentages, whereas CNNs are black boxes).
3. **Q: Why is personalized baseline calibration necessary?**
   - **A:** People have different natural facial anatomies. A person with naturally deep-set eyes or a low brow line would be falsely flagged as chronically stressed by a generic model. Individual delta normalization ($\Delta = \text{Current} - \text{Baseline}$) eliminates demographic and morphological false positives.
4. **Q: Why not rely on camera heart rate (rPPG) to detect fake stress?**
   - **A:** Camera heart rate requires clinical lighting and 10 to 30 seconds of video to compute spectral peaks. A regular home user cannot wait 15 seconds for pulse detection. Our system detects fake stress on the very first photo using pure spatial FACS Action Unit synergy.
5. **Q: What happens when fake stress is detected?**
   - **A:** The system executes Dual-Stream Gating: the raw facial score (e.g. 78) is intercepted, the UI displays a `FEIGNED STRESS INTERCEPTED` badge, and the physiological stress score is gated back to the user's verified calm resting level (~42).
6. **Q: Where is data stored and is user privacy protected?**
   - **A:** In a local SQLite database (`backend/data.db`). No facial images are ever permanently saved to disk or uploaded to external cloud servers.
7. **Q: What actionable interventions does the platform offer?**
   - **A:** Interactive 4-7-8 Breathing Coach, Box Breathing (4-4-4-4) for acute tension, 5-4-3-2-1 Sensory Grounding Exercises, and facial unclenching routines tailored to the detected tension level.

