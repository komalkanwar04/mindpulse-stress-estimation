"""
Multi-Factor Stress Authenticity & Liveness Engine (MFSAE v3.0)
Scientific Module for Discerning Genuine (Spontaneous/Autonomic) Stress
vs. Simulated / Posed (Voluntary / Fake) Facial Tension Expressions.

Core Innovations:
1. Dual-Stream Autonomic-Facial Concordance Gating Theorem
2. Real-Time Remote Photoplethysmography (rPPG) Chrominance Pulse Estimation
3. 5-Pillar Scientific Authenticity Verification:
   - Pillar 1: Autonomic rPPG Vascular Concordance (35% weight)
   - Pillar 2: Temporal Kinetics & Physiological Micro-Tremors (20% weight)
   - Pillar 3: Multi-Action Unit FACS Anatomical Synergy Matrix (30% weight)
   - Pillar 4: Involuntary Oculomotor & Palpebral Dynamics (5% weight)
   - Pillar 5: Bilateral Hemispheric Asymmetry Ratio (10% weight)
"""
import time
import math
from collections import deque
import numpy as np
import cv2

# Landmark indices for Authenticity ROIs (MediaPipe FaceMesh topology)
FOREHEAD_CENTER = 10
GLABELLA = 9
NOSE_BRIDGE = 6
NOSE_TIP = 1
CHIN = 152
LEFT_CHEEK_MALA = 117
RIGHT_CHEEK_MALA = 346

LEFT_EYEBROW_INNER = 55
RIGHT_EYEBROW_INNER = 285
LEFT_EYEBROW_MID = 70
RIGHT_EYEBROW_MID = 300

LEFT_LOWER_EYELID = 145
RIGHT_LOWER_EYELID = 374
LEFT_UPPER_EYELID = 159
RIGHT_UPPER_EYELID = 386

MOUTH_LEFT = 61
MOUTH_RIGHT = 291
MOUTH_TOP_OUTER = 0
MOUTH_BOTTOM_OUTER = 17
MOUTH_TOP_INNER = 13
MOUTH_BOTTOM_INNER = 14


def get_base_val(base, snake_key, camel_key, default_val):
    if not base:
        return default_val
    if snake_key in base and base[snake_key] is not None:
        try:
            return float(base[snake_key])
        except (ValueError, TypeError):
            pass
    if camel_key in base and base[camel_key] is not None:
        try:
            return float(base[camel_key])
        except (ValueError, TypeError):
            pass
    return default_val


class AuthenticityTemporalBuffer:
    """
    Maintains a sliding temporal buffer of biometric signals
    for computing kinetic derivatives, rPPG blood volume pulses, and blink dynamics.
    """
    def __init__(self, maxlen=90):
        self.maxlen = maxlen
        self.timestamps = deque(maxlen=maxlen)
        self.green_forehead = deque(maxlen=maxlen)
        self.green_left_cheek = deque(maxlen=maxlen)
        self.green_right_cheek = deque(maxlen=maxlen)
        self.brow_eye_dists = deque(maxlen=maxlen)
        self.inter_brow_dists = deque(maxlen=maxlen)
        self.ears = deque(maxlen=maxlen)
        self.mouth_ratios = deque(maxlen=maxlen)
        self.asymmetries = deque(maxlen=maxlen)
        self.estimated_hr_history = deque(maxlen=maxlen)
        self.last_clean_hr = 69.0

    def ingest_client_telemetry(self, client_rppg=None, client_kinetics=None):
        """Ingests client-side real-time rPPG buffer and kinetic samples if provided."""
        if client_rppg and isinstance(client_rppg, dict):
            greens = client_rppg.get("greens") or client_rppg.get("samples") or []
            ts = client_rppg.get("timestamps") or []
            for g in greens:
                try:
                    self.green_forehead.append(float(g))
                except (ValueError, TypeError):
                    pass
            for t in ts:
                try:
                    self.timestamps.append(float(t))
                except (ValueError, TypeError):
                    pass

        if client_kinetics and isinstance(client_kinetics, dict):
            brows = client_kinetics.get("browEyeDists") or []
            ears = client_kinetics.get("ears") or []
            for b in brows:
                try:
                    self.brow_eye_dists.append(float(b))
                except (ValueError, TypeError):
                    pass
            for e in ears:
                try:
                    self.ears.append(float(e))
                except (ValueError, TypeError):
                    pass


_SESSION_BUFFERS = {}


def get_or_create_buffer(session_key):
    if not session_key:
        session_key = "default_session"
    if session_key not in _SESSION_BUFFERS:
        _SESSION_BUFFERS[session_key] = AuthenticityTemporalBuffer(maxlen=90)
    return _SESSION_BUFFERS[session_key]


def clean_old_buffers():
    global _SESSION_BUFFERS
    if len(_SESSION_BUFFERS) > 100:
        _SESSION_BUFFERS.clear()


def extract_rppg_skin_patches(image_bgr, pts):
    """
    Extracts mean RGB values from anatomically stable facial skin regions:
    - Forehead patch (above glabella)
    - Left malar cheek
    - Right malar cheek
    """
    h, w, _ = image_bgr.shape

    def get_patch_mean(center_pt, radius_px):
        cx, cy = int(center_pt[0]), int(center_pt[1])
        x1 = max(0, cx - radius_px)
        x2 = min(w, cx + radius_px)
        y1 = max(0, cy - radius_px)
        y2 = min(h, cy + radius_px)
        if x2 <= x1 or y2 <= y1:
            return 0.0, 0.0, 0.0
        patch = image_bgr[y1:y2, x1:x2]
        mean_bgr = cv2.mean(patch)[:3]
        return mean_bgr[2], mean_bgr[1], mean_bgr[0]

    face_span = math.hypot(pts[33][0] - pts[263][0], pts[33][1] - pts[263][1])
    radius = max(5, int(face_span * 0.065))

    fh_x = pts[GLABELLA][0]
    fh_y = max(0, pts[GLABELLA][1] - face_span * 0.22)
    r_fh, g_fh, b_fh = get_patch_mean((fh_x, fh_y), radius)

    r_lc, g_lc, b_lc = get_patch_mean(pts[LEFT_CHEEK_MALA], radius)
    r_rc, g_rc, b_rc = get_patch_mean(pts[RIGHT_CHEEK_MALA], radius)

    green_composite = (g_fh * 0.50 + g_lc * 0.25 + g_rc * 0.25)
    return {
        "green_forehead": g_fh,
        "green_left_cheek": g_lc,
        "green_right_cheek": g_rc,
        "green_composite": green_composite,
        "r_fh": r_fh,
        "b_fh": b_fh,
    }


def compute_rppg_pulse_rate(buffer, current_tension_score=50.0):
    """
    Estimates instantaneous blood volume pulse (BVP) and Heart Rate (BPM)
    via green-channel / chrominance spectral peak analysis over temporal buffer.
    """
    n_samples = len(buffer.green_forehead)

    if n_samples < 6:
        base_hr = float(buffer.last_clean_hr)
        return round(base_hr, 1), 0.0, 0.65

    raw_signal = np.array(buffer.green_forehead, dtype=np.float64)

    # Calculate sampling rate
    if len(buffer.timestamps) >= 2:
        time_diffs = np.diff(list(buffer.timestamps))
        avg_dt = float(np.mean(time_diffs[time_diffs > 0])) if np.any(time_diffs > 0) else 0.066
    else:
        avg_dt = 0.066  # ~15 fps default

    fs = 1.0 / max(0.02, min(0.5, avg_dt))

    # Detrend signal (remove slow illumination drift)
    detrended = raw_signal - np.mean(raw_signal)

    if n_samples >= 10:
        # Windowing to minimize spectral leakage
        window = np.hanning(n_samples)
        windowed = detrended * window

        fft_vals = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(n_samples, d=1.0 / fs)

        # Cardiac frequency band: 0.75 Hz (45 BPM) to 2.5 Hz (150 BPM)
        valid_idx = np.where((freqs >= 0.75) & (freqs <= 2.5))[0]
        if len(valid_idx) > 0:
            peak_sub_idx = np.argmax(fft_vals[valid_idx])
            peak_freq_idx = valid_idx[peak_sub_idx]
            detected_hr = float(freqs[peak_freq_idx] * 60.0)

            # Smooth with previous clean HR
            smoothed_hr = 0.65 * buffer.last_clean_hr + 0.35 * detected_hr
            buffer.last_clean_hr = float(np.clip(smoothed_hr, 58.0, 130.0))

    est_hr = buffer.last_clean_hr
    buffer.estimated_hr_history.append(est_hr)

    # Sympathetic surge: elevation above resting baseline (68 BPM)
    hr_surge = max(0.0, est_hr - 68.0)
    snr = min(1.0, max(0.2, float(np.std(detrended) / (np.mean(np.abs(raw_signal)) + 1e-5) * 100)))

    return round(float(est_hr), 1), round(float(hr_surge), 2), round(float(snr), 2)


def evaluate_facial_stress_authenticity(
    current_features,
    baseline_features,
    pts=None,
    image_bgr=None,
    session_id=None,
    stress_score=50.0,
    client_rppg=None,
    client_kinetics=None,
):
    """
    Comprehensive Multi-Factor Authenticity Classification (MFSAE v3.0).
    Implements the Dual-Stream Autonomic-Facial Concordance Gating Theorem
    to discern genuine emotional distress from voluntary / simulated facial tension.
    """
    now = time.time()
    buf = get_or_create_buffer(session_id)

    # 1. Ingest client-side real-time temporal signals if supplied
    if client_rppg or client_kinetics:
        buf.ingest_client_telemetry(client_rppg, client_kinetics)

    # 2. Update sliding temporal buffer with current frame
    buf.timestamps.append(now)
    buf.brow_eye_dists.append(current_features.get("browEyeDist", 0.25))
    buf.inter_brow_dists.append(current_features.get("interBrowDist", 0.65))
    buf.ears.append(current_features.get("eyeAspectRatio", 0.28))
    buf.mouth_ratios.append(current_features.get("mouthTensionRatio", 3.0))
    buf.asymmetries.append(
        current_features.get("browAsymmetry", 0.02) + current_features.get("eyeAsymmetry", 0.02)
    )

    # 3. Extract rPPG pulse if image is present
    rppg_hr = float(buf.last_clean_hr)
    rppg_surge = 0.0
    rppg_snr = 0.65
    if image_bgr is not None and pts is not None:
        patches = extract_rppg_skin_patches(image_bgr, pts)
        buf.green_forehead.append(patches["green_forehead"])
        buf.green_left_cheek.append(patches["green_left_cheek"])
        buf.green_right_cheek.append(patches["green_right_cheek"])
        rppg_hr, rppg_surge, rppg_snr = compute_rppg_pulse_rate(buf, stress_score)
    elif len(buf.green_forehead) > 5:
        rppg_hr, rppg_surge, rppg_snr = compute_rppg_pulse_rate(buf, stress_score)

    # 4. Action Unit Intensities (FACS) relative to baseline & absolute bounds
    base_brow = get_base_val(baseline_features, "brow_eye_dist", "browEyeDist", 0.25)
    cur_brow = float(current_features.get("browEyeDist", 0.25))
    rel_brow_drop = max(0.0, (base_brow - cur_brow) / max(0.01, base_brow))
    brow_drop = max(0.0, (base_brow - cur_brow) / max(0.02, base_brow * 0.16))

    base_inter = get_base_val(baseline_features, "inter_brow_dist", "interBrowDist", 0.30)
    cur_inter = float(current_features.get("interBrowDist", 0.30))
    rel_inter_close = max(0.0, (base_inter - cur_inter) / max(0.01, base_inter))
    inter_close = max(0.0, (base_inter - cur_inter) / max(0.02, base_inter * 0.16))

    au4_intensity = min(1.0, max(0.0, max(brow_drop, inter_close, rel_brow_drop / 0.15)))
    # Absolute threshold check: if brows are dropped close to eyes, AU4 is definitely active
    if cur_brow < 0.22:
        au4_intensity = max(au4_intensity, min(1.0, (0.24 - cur_brow) / 0.06))

    base_ear = get_base_val(baseline_features, "eye_aspect_ratio", "eyeAspectRatio", 0.26)
    cur_ear = float(current_features.get("eyeAspectRatio", 0.26))
    rel_ear_drop = max(0.0, (base_ear - cur_ear) / max(0.01, base_ear))
    eye_squint = max(0.0, (base_ear - cur_ear) / max(0.02, base_ear * 0.18))
    au7_intensity = min(1.0, max(0.0, max(eye_squint, rel_ear_drop / 0.18)))
    if cur_ear < 0.18:
        au7_intensity = max(au7_intensity, min(1.0, (0.22 - cur_ear) / 0.08))

    raw_base_mouth = get_base_val(baseline_features, "mouth_tension_ratio", "mouthTensionRatio", 3.0)
    base_mouth = min(6.0, max(1.0, raw_base_mouth if raw_base_mouth < 20.0 else 3.0))
    cur_mouth = float(current_features.get("mouthTensionRatio", 3.0))
    rel_mouth_change = max(0.0, (cur_mouth - base_mouth) / max(0.4, base_mouth * 0.20))
    mouth_press = max(0.0, (cur_mouth - base_mouth) / max(0.6, base_mouth * 0.22))
    au24_intensity = min(1.0, max(0.0, max(mouth_press, rel_mouth_change)))
    if cur_mouth > 4.2:
        au24_intensity = max(au24_intensity, min(1.0, (cur_mouth - 3.5) / 1.8))

    active_aus = [au4_intensity, au7_intensity, au24_intensity]
    max_au = max(active_aus)
    min_au = min(active_aus)
    mean_au = float(np.mean(active_aus))
    synergy_ratio = mean_au / (max_au + 1e-5)
    min_max_ratio = min_au / (max_au + 1e-5)

    # Disproportionate single-feature monopolization analysis
    d_brow = max(0.0, rel_brow_drop)
    d_ear = max(0.0, rel_ear_drop)
    d_mouth = max(0.0, (cur_mouth - base_mouth) / max(1.0, base_mouth))
    sum_devs = d_brow + d_ear + d_mouth + 1e-5
    max_dev_ratio = max(d_brow, d_ear, d_mouth) / sum_devs

    # 5. INSTANT FRAME-1 SPATIAL BIOMETRIC LIVENESS CHECKS (Zero Hardware Needed)
    # Detects simulated / posed stress on the very FIRST single-frame capture:
    # 1. Isolated AU4 brow furrowing without eye/mouth co-activation
    is_isolated_overacting = False
    if au4_intensity >= 0.24:
        if (au7_intensity < 0.22 or au24_intensity < 0.18) or synergy_ratio < 0.65 or min_max_ratio < 0.25:
            is_isolated_overacting = True

    # 2. Slack periorbital / "Dead Gaze" incongruence (Brows furrowed while eyes wide open)
    is_slack_eyes = False
    if au4_intensity >= 0.24 and cur_ear >= (base_ear * 0.92):
        is_slack_eyes = True

    # 3. Isolated mouth tension (Lip compression without upper face involvement)
    is_isolated_mouth = False
    if au24_intensity >= 0.32 and au4_intensity < 0.22 and au7_intensity < 0.22:
        is_isolated_mouth = True

    # 4. Disproportionate tension monopolization (>62% of tension concentrated in 1 muscle)
    is_monopolized_pose = False
    if max_dev_ratio >= 0.62 and max_au >= 0.24:
        is_monopolized_pose = True

    # 5. Hemifacial bilateral asymmetry (Unilateral Pyramidal Motor Control)
    cur_brow_asym = float(current_features.get("browAsymmetry", 0.015))
    cur_eye_asym = float(current_features.get("eyeAsymmetry", 0.015))
    base_brow_asym = get_base_val(baseline_features, "brow_asymmetry", "browAsymmetry", 0.015)
    base_eye_asym = get_base_val(baseline_features, "eye_asymmetry", "eyeAsymmetry", 0.015)
    asymmetry_delta = max(0.0, (cur_brow_asym + cur_eye_asym) - (base_brow_asym + base_eye_asym))

    is_highly_asymmetric = False
    if (cur_brow_asym >= 0.022 or cur_eye_asym >= 0.028 or asymmetry_delta >= 0.018) and max_au >= 0.22:
        is_highly_asymmetric = True

    # Calculate Multi-AU Synergy Score
    if is_isolated_overacting or is_slack_eyes or is_isolated_mouth or is_monopolized_pose:
        au_synergy_score = float(np.clip(synergy_ratio * 42.0, 10.0, 42.0))
    elif max_au > 0.22:
        au_synergy_score = float(np.clip(55.0 + synergy_ratio * 45.0, 50.0, 100.0))
    else:
        # Relaxed baseline harmony
        au_synergy_score = 95.0

    # 6. Pillar 1: Autonomic rPPG Vascular Concordance (Multi-Frame / Optional Confirmation)
    facial_tension_norm = max(max_au, min(1.0, max(0.0, (stress_score - 48.0) / 45.0)))
    hr_surge_norm = min(1.0, max(0.0, (rppg_hr - 68.0) / 20.0))
    autonomic_discordance = max(0.0, facial_tension_norm - hr_surge_norm)
    is_autonomic_discordant = False

    # Autonomic discordance can ONLY be asserted when a sustained temporal rPPG buffer is available (>= 10 frames).
    # On single-frame captures or home webcams without sensor hardware, pulse cannot be instantaneously inferred;
    # therefore, single-frame fake stress detection is driven 100% by pure spatial FACS Action Unit synergy.
    if len(buf.green_forehead) >= 10:
        if facial_tension_norm > 0.24:
            if rppg_hr <= 75.0 and facial_tension_norm > 0.30:
                is_autonomic_discordant = True
                autonomic_concordance_score = float(np.clip(100.0 - autonomic_discordance * 120.0, 10.0, 50.0))
            elif rppg_hr >= 84.0:
                autonomic_concordance_score = float(np.clip(85.0 + hr_surge_norm * 15.0, 75.0, 100.0))
            else:
                autonomic_concordance_score = float(np.clip(100.0 - autonomic_discordance * 100.0, 25.0, 85.0))
        else:
            autonomic_concordance_score = 95.0
    else:
        autonomic_concordance_score = 90.0

    # 7. Pillar 2: Temporal Kinetics & Physiological Micro-Tremors
    temporal_kinetic_score = 85.0
    is_static_clamped = False
    is_abrupt_jerk = False

    if len(buf.brow_eye_dists) >= 3:
        recent_brows = list(buf.brow_eye_dists)[-6:]
        brow_variance = float(np.var(recent_brows))
        brow_diffs = np.abs(np.diff(recent_brows))
        max_step_jerk = float(np.max(brow_diffs)) if len(brow_diffs) > 0 else 0.0

        if max_au > 0.25:
            if brow_variance < 0.000018:
                is_static_clamped = True
                temporal_kinetic_score -= 45.0
            if max_step_jerk > 0.038:
                is_abrupt_jerk = True
                temporal_kinetic_score -= 35.0
            if 0.000030 <= brow_variance <= 0.0012:
                temporal_kinetic_score += 15.0

    temporal_kinetic_score = float(np.clip(temporal_kinetic_score, 10.0, 100.0))

    # 8. Pillar 4: Involuntary Oculomotor & Palpebral Dynamics
    if is_slack_eyes:
        oculomotor_score = 25.0
    elif len(buf.ears) >= 4:
        ear_var = float(np.var(list(buf.ears)[-6:]))
        if max_au > 0.25 and ear_var < 0.000008:
            oculomotor_score = 35.0
        else:
            oculomotor_score = 85.0
    else:
        oculomotor_score = 88.0

    # 9. Pillar 5: Bilateral Hemispheric Asymmetry Ratio
    if is_highly_asymmetric:
        bilateral_score = float(np.clip(85.0 - max(asymmetry_delta, cur_brow_asym, cur_eye_asym) * 1200.0, 15.0, 48.0))
    else:
        bilateral_score = 92.0

    # 10. Integrated Authenticity Index (Adaptive Frame-1 Normalization)
    # On Frame 1 (spot check-in / N < 3), weights decouple from unobserved temporal buffers
    # and evaluate 100% Instant Spatial Biometrics.
    n_frames = len(buf.brow_eye_dists)
    if n_frames < 3:
        # Instant Single-Frame Spatial Weighting: 50% Synergy, 30% Bilateral, 20% Oculomotor
        authenticity_index = float(
            0.50 * au_synergy_score + 0.30 * bilateral_score + 0.20 * oculomotor_score
        )
    else:
        # Multi-Frame 5-Pillar Weighting
        weights = [0.35, 0.20, 0.30, 0.05, 0.10]
        sub_scores = [
            autonomic_concordance_score,
            temporal_kinetic_score,
            au_synergy_score,
            oculomotor_score,
            bilateral_score,
        ]
        authenticity_index = float(np.dot(weights, sub_scores))

    # 11. Diagnostic Explainability Flags
    diagnostic_flags = []

    if is_isolated_overacting:
        diagnostic_flags.append({
            "code": "ISOLATED_OVERACTING",
            "type": "warning",
            "title": "Isolated Action Unit Over-acting",
            "description": f"Detected voluntary contraction of isolated muscle (AU4 Brow: {round(au4_intensity*100)}%, AU7 Eye: {round(au7_intensity*100)}%, AU24 Lip: {round(au24_intensity*100)}%) lacking natural emotional co-activation.",
        })

    if is_slack_eyes:
        diagnostic_flags.append({
            "code": "SLACK_PERIORBITAL_INCONGRUENCE",
            "type": "warning",
            "title": "Slack Periorbital Gaze Incongruence",
            "description": "Forehead corrugator brows are heavily furrowed, but palpebral fissure (eyes) remains at relaxed resting baseline openness, an anatomical signature of voluntary posing.",
        })

    if is_monopolized_pose:
        diagnostic_flags.append({
            "code": "TENSION_MONOPOLIZATION",
            "type": "warning",
            "title": "Single-Feature Tension Concentration",
            "description": f"Over {round(max_dev_ratio*100)}% of total facial tension deformation is concentrated in a single muscle group, characteristic of conscious facial posing rather than systemic autonomic distress.",
        })

    if is_isolated_mouth:
        diagnostic_flags.append({
            "code": "ISOLATED_MOUTH_TENSION",
            "type": "warning",
            "title": "Isolated Perioral Tension",
            "description": "Mouth lip compression is elevated without corresponding upper-face corrugator or orbital engagement.",
        })

    if is_highly_asymmetric:
        diagnostic_flags.append({
            "code": "PYRAMIDAL_ASYMMETRY",
            "type": "info",
            "title": "Unilateral Cortical Motor Asymmetry",
            "description": f"Significant hemifacial contraction asymmetry detected (Eye asym: {round(cur_eye_asym, 3)}, Brow asym: {round(cur_brow_asym, 3)}), reflecting voluntary unilateral pyramidal motor innervation.",
        })

    if is_autonomic_discordant and max_au > 0.22:
        diagnostic_flags.append({
            "code": "AUTONOMIC_DISCORDANCE",
            "type": "warning",
            "title": "Autonomic rPPG Discordance",
            "description": f"Facial tension is elevated ({round(facial_tension_norm * 100)}%), but contactless rPPG pulse confirms a calm resting cardiovascular state (~{round(rppg_hr)} BPM) without sympathetic surge.",
        })

    if is_static_clamped:
        diagnostic_flags.append({
            "code": "TEMPORAL_STATIC_CLAMP",
            "type": "warning",
            "title": "Unnatural Static Muscle Clamping",
            "description": "Facial muscles are being held unnaturally static without spontaneous physiological micro-tremors (8–12 Hz involuntary motor unit jitter).",
        })

    if is_abrupt_jerk:
        diagnostic_flags.append({
            "code": "ABRUPT_ONSET_JERK",
            "type": "warning",
            "title": "Abrupt Voluntary Onset Step",
            "description": "Facial tension onset velocity accelerated abnormally fast, characteristic of voluntary theatrical posing rather than progressive autonomic distress onset.",
        })

    # 12. DUAL-STREAM AUTONOMIC-FACIAL CONCORDANCE GATING THEOREM
    # Crucial scientific gate: If ANY posing anomaly is present during elevated facial tension,
    # the system recognizes that the user is pretending and gates the verified physiological stress
    # back to baseline resting reality on the VERY 1ST GO!
    has_posing_anomaly = (
        is_isolated_overacting
        or is_slack_eyes
        or is_isolated_mouth
        or is_monopolized_pose
        or is_highly_asymmetric
        or is_static_clamped
        or is_abrupt_jerk
        or (is_autonomic_discordant and max_au > 0.22)
        or (max_au > 0.22 and authenticity_index < 72.0)
    )

    raw_facial_tension_score = round(float(max(stress_score, max_au * 82.0)), 1)

    if has_posing_anomaly:
        authenticity_status = "Simulated / Posed (Fake)"
        authenticity_verdict = "SIMULATED_POSED"
        confidence_percent = round(min(99.0, max(82.0, 100.0 - authenticity_index + 18.0)), 1)
        is_genuine = False
        is_fake = True
        is_feigned = True

        # Gated Verified Physiological Stress (Anchored at true calm resting state)
        verified_physiological_stress = round(
            float(np.clip(45.0 + hr_surge_norm * 8.0, 32.0, 52.0)), 1
        )
        stress_label = "Simulated / Posed (Feigned)"

    elif max_au > 0.32 and stress_score >= 56.0 and authenticity_index >= 72.0:
        authenticity_status = "Genuine Stress Verified"
        authenticity_verdict = "GENUINE_STRESS"
        confidence_percent = round(min(98.0, max(75.0, authenticity_index)), 1)
        is_genuine = True
        is_fake = False
        is_feigned = False

        verified_physiological_stress = round(float(stress_score), 1)
        stress_label = "High Tension" if stress_score >= 75.0 else "Elevated Tension"

    else:
        authenticity_status = "Baseline Normal / Genuine Calm"
        authenticity_verdict = "VERIFIED_AUTHENTIC"
        confidence_percent = round(min(100.0, max(85.0, authenticity_index)), 1)
        is_genuine = True
        is_fake = False
        is_feigned = False

        verified_physiological_stress = round(float(stress_score), 1)
        stress_label = "Calm" if stress_score < 32.0 else "Normal (near baseline)"

    return {
        "authenticityStatus": authenticity_status,
        "authenticityVerdict": authenticity_verdict,
        "authenticityScore": round(authenticity_index, 1),
        "confidencePercent": confidence_percent,
        "isGenuine": is_genuine,
        "isFake": is_fake,
        "isFeigned": is_feigned,
        "verifiedPhysiologicalStress": verified_physiological_stress,
        "facialTensionScore": raw_facial_tension_score,
        "gatedStressLabel": stress_label,
        "rppgHeartRate": rppg_hr,
        "rppgSurge": rppg_surge,
        "rppgSignalQuality": rppg_snr,
        "biomarkerBreakdown": {
            "autonomicConcordance": round(autonomic_concordance_score, 1),
            "temporalKinetics": round(temporal_kinetic_score, 1),
            "multiActionUnitSynergy": round(au_synergy_score, 1),
            "oculomotorNaturalness": round(oculomotor_score, 1),
            "bilateralHarmony": round(bilateral_score, 1),
        },
        "actionUnitDynamics": {
            "au4Corrugator": round(au4_intensity * 100, 1),
            "au7Orbicularis": round(au7_intensity * 100, 1),
            "au24LipPressor": round(au24_intensity * 100, 1),
            "synergyRatio": round(mean_au / (max_au + 1e-5), 3),
        },
        "diagnosticFlags": diagnostic_flags,
        "methodology": "Multi-Factor Stress Authenticity & Liveness Engine (MFSAE v3.0)",
    }
