import os
import sys
import time
import urllib.request
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

# When frozen by PyInstaller, place models/ next to the .exe; otherwise next to project root.
_BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
            else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_MODEL_DIR = os.path.join(_BASE_DIR, "models")

_FACE_MODEL_PATH = os.path.join(_MODEL_DIR, "face_landmarker.task")
_FACE_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)
_HAND_MODEL_PATH = os.path.join(_MODEL_DIR, "hand_landmarker.task")
_HAND_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [263, 387, 385, 362, 380, 373]
MOUTH_INDICES = [13, 14]  # inner upper/lower lip landmarks

EAR_THRESHOLD         = 0.25
CONSEC_FRAMES         = 2
SIT_RESET_AWAY        = 5  * 60   # 5 min without face resets sit timer
SIT_AWAY_DISMISS      = 3.0       # seconds face must be absent to dismiss sit alert
WATER_RESET_AWAY      = 5  * 60   # 5 min without face resets water timer
DRINK_HOLD_SECONDS    = 1.0       # seconds hand must stay near mouth to confirm drink
HAND_MOUTH_RATIO      = 0.65      # proximity threshold: closest fingertip / face width
RECONNECT_FAIL_LIMIT  = 30
RECONNECT_INTERVAL_MS = 1500


def _ear(landmarks, indices, w, h):
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    v1 = np.hypot(pts[1][0] - pts[5][0], pts[1][1] - pts[5][1])
    v2 = np.hypot(pts[2][0] - pts[4][0], pts[2][1] - pts[4][1])
    hz = np.hypot(pts[0][0] - pts[3][0], pts[0][1] - pts[3][1])
    return (v1 + v2) / (2.0 * hz + 1e-6)


def _hand_near_mouth(face_lm, hand_lm_list, w, h) -> bool:
    """Return True if any fingertip is close to the mouth center.

    Tracks all five fingertips (thumb 4, index 8, middle 12, ring 16, pinky 20)
    and triggers when the *closest* one is within HAND_MOUTH_RATIO × face_width.
    This matches real drinking behaviour: fingertips (not knuckles) approach the
    mouth when raising a cup or bottle.
    """
    mouth_pts = [(face_lm[i].x * w, face_lm[i].y * h) for i in MOUTH_INDICES]
    mx = sum(p[0] for p in mouth_pts) / len(mouth_pts)
    my = sum(p[1] for p in mouth_pts) / len(mouth_pts)
    l_eye = (face_lm[33].x * w, face_lm[33].y * h)
    r_eye = (face_lm[263].x * w, face_lm[263].y * h)
    face_w = np.hypot(r_eye[0] - l_eye[0], r_eye[1] - l_eye[1])
    if face_w < 1:
        return False
    for hand in hand_lm_list:
        tip_pts = [(hand[i].x * w, hand[i].y * h) for i in [4, 8, 12, 16, 20]]
        min_dist = min(np.hypot(tx - mx, ty - my) for tx, ty in tip_pts)
        if min_dist / face_w < HAND_MOUTH_RATIO:
            return True
    return False


def _best_hand_dist(face_lm, hand_lm_list, w, h) -> float | None:
    """Return the closest fingertip-to-mouth distance ratio across all hands, or None."""
    if not hand_lm_list:
        return None
    mouth_pts = [(face_lm[i].x * w, face_lm[i].y * h) for i in MOUTH_INDICES]
    mx = sum(p[0] for p in mouth_pts) / len(mouth_pts)
    my = sum(p[1] for p in mouth_pts) / len(mouth_pts)
    l_eye = (face_lm[33].x * w, face_lm[33].y * h)
    r_eye = (face_lm[263].x * w, face_lm[263].y * h)
    face_w = np.hypot(r_eye[0] - l_eye[0], r_eye[1] - l_eye[1])
    if face_w < 1:
        return None
    best = float("inf")
    for hand in hand_lm_list:
        tip_pts = [(hand[i].x * w, hand[i].y * h) for i in [4, 8, 12, 16, 20]]
        min_dist = min(np.hypot(tx - mx, ty - my) for tx, ty in tip_pts)
        best = min(best, min_dist / face_w)
    return best


def _ensure_model(path: str, url: str, label: str, status_cb=None) -> str:
    os.makedirs(_MODEL_DIR, exist_ok=True)
    if not os.path.exists(path):
        if status_cb:
            status_cb(f"Downloading {label}...")
        urllib.request.urlretrieve(url, path)
    return os.path.abspath(path)


def _fmt_sec(s: float) -> str:
    """Format seconds as 'Xs' or 'M:SS'."""
    t = int(s)
    return f"{t}s" if t < 60 else f"{t // 60}:{t % 60:02d}"


def _remaining_color(remaining: float, threshold: float):
    """BGR color that shifts green → yellow → orange → red as time runs out."""
    ratio = remaining / threshold if threshold > 0 else 0.0
    if ratio > 0.5:  return (40,  200,  40)   # green
    if ratio > 0.2:  return ( 0,  200, 200)   # yellow
    if ratio > 0.0:  return ( 0,  130, 255)   # orange
    return                   (50,   50, 220)   # red (exceeded)


def _draw_stats_panel(rgb, settings, ear: float, blink_total: int,
                      blink_elapsed: float, sit_elapsed: float,
                      water_elapsed: float,
                      hand_dist_ratio: float | None,
                      drink_hold_elapsed: float) -> None:
    """Render a semi-transparent panel with only the enabled monitoring rows."""
    rows: list[tuple[str, tuple]] = []

    if settings.blink_enabled:
        rows.append((f"EAR {ear:.3f}   Blinks {blink_total}", (190, 190, 190)))
        bt    = settings.blink_threshold
        b_rem = max(0.0, bt - blink_elapsed)
        b_txt = "BLINK NOW" if blink_elapsed >= bt else f"in {_fmt_sec(b_rem)}"
        rows.append((f"Blink    {b_txt}", _remaining_color(b_rem, bt)))

    if settings.sit_enabled:
        st    = settings.sit_threshold_sec
        s_rem = max(0.0, st - sit_elapsed)
        s_txt = "TAKE BREAK" if sit_elapsed >= st else f"in {_fmt_sec(s_rem)}"
        rows.append((f"Sit      {s_txt}", _remaining_color(s_rem, st)))

    if settings.water_enabled:
        wt    = settings.water_threshold_sec
        w_rem = max(0.0, wt - water_elapsed)
        w_txt = "DRINK WATER" if water_elapsed >= wt else f"in {_fmt_sec(w_rem)}"
        rows.append((f"Water    {w_txt}", _remaining_color(w_rem, wt)))
        if hand_dist_ratio is None:
            rows.append(("Hand: not detected", (120, 120, 120)))
        elif hand_dist_ratio < HAND_MOUTH_RATIO:
            pct = int(min(drink_hold_elapsed / DRINK_HOLD_SECONDS, 1.0) * 100)
            rows.append((f"Drink gesture: {pct}%", (40, 200, 40)))
        else:
            rows.append((f"Hand dist: {hand_dist_ratio:.2f}x  (need <{HAND_MOUTH_RATIO:.2f}x)",
                         (120, 120, 120)))

    if not rows:
        return

    pad    = 10
    line_h = 26
    pw     = 310
    ph     = pad + line_h * len(rows) + pad - 4

    bg = rgb.copy()
    cv2.rectangle(bg, (6, 6), (6 + pw, 6 + ph), (10, 10, 10), -1)
    cv2.addWeighted(bg, 0.60, rgb, 0.40, 0, rgb)

    font = cv2.FONT_HERSHEY_SIMPLEX
    sc   = 0.52
    th   = 1
    x    = 14
    y0   = pad + 22

    for i, (text, color) in enumerate(rows):
        cv2.putText(rgb, text, (x, y0 + line_h * i), font, sc, color, th, cv2.LINE_AA)


class CameraThread(QThread):
    frame_ready       = pyqtSignal(QImage)
    blink_detected    = pyqtSignal(int)   # total blink count
    no_blink_alert    = pyqtSignal()      # fired once when > NO_BLINK_THRESHOLD without blink
    sit_break_alert   = pyqtSignal()      # fired once when sitting > SIT_BREAK_THRESHOLD
    sit_break_away    = pyqtSignal()      # fired when user stands up while sit alert is showing
    water_break_alert = pyqtSignal()      # fired once when no drink for > WATER_BREAK_THRESHOLD
    water_dismissed   = pyqtSignal()      # fired when drink confirmed or user stands up while water alert showing
    status_changed    = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, settings=None):
        super().__init__()
        from .settings import AppSettings
        self._camera_index = camera_index
        self._settings     = settings or AppSettings()
        self._running      = False
        self._blink_frames = 0
        self._blink_total  = 0
        self._reset_sit    = False
        self._reset_water  = False

    def reset_sit_timer(self):
        self._reset_sit = True

    def reset_water_timer(self):
        self._reset_water = True

    def run(self):
        self._running = True

        try:
            face_model = _ensure_model(
                _FACE_MODEL_PATH, _FACE_MODEL_URL,
                "face detection model (~3.7 MB)", self.status_changed.emit,
            )
            hand_model = _ensure_model(
                _HAND_MODEL_PATH, _HAND_MODEL_URL,
                "hand detection model (~8.3 MB)", self.status_changed.emit,
            )
        except Exception as e:
            self.status_changed.emit(f"Model download failed: {e}")
            return

        face_options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=face_model),
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        hand_options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=hand_model),
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        with mp_vision.FaceLandmarker.create_from_options(face_options) as face_lmk:
            with mp_vision.HandLandmarker.create_from_options(hand_options) as hand_lmk:
                while self._running:
                    cap = cv2.VideoCapture(self._camera_index)
                    if not cap.isOpened():
                        self.status_changed.emit(
                            f"Cannot open camera {self._camera_index}, retrying..."
                        )
                        self.msleep(RECONNECT_INTERVAL_MS)
                        continue

                    self.status_changed.emit(f"Camera {self._camera_index} connected")

                    last_blink_time    = time.monotonic()
                    alert_sent         = False
                    fail_count         = 0
                    sit_start_time    = time.monotonic()
                    sit_alert_sent    = False
                    sit_reset_pending = False
                    water_start_time  = time.monotonic()
                    water_alert_sent  = False
                    drink_near_start  = None
                    face_away_start   = None

                    while self._running:
                        ret, frame = cap.read()
                        if ret:
                            frame = cv2.flip(frame, 1)
                        if not ret:
                            fail_count += 1
                            if fail_count >= RECONNECT_FAIL_LIMIT:
                                self.status_changed.emit(
                                    f"Camera {self._camera_index} disconnected, reconnecting..."
                                )
                                break
                            continue

                        fail_count = 0
                        now = time.monotonic()

                        # Apply external timer resets
                        if self._reset_sit:
                            self._reset_sit = False
                            sit_start_time  = now
                            sit_alert_sent  = False
                        if self._reset_water:
                            self._reset_water = False
                            water_start_time  = now
                            water_alert_sent  = False

                        h, w   = frame.shape[:2]
                        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                        face_result = face_lmk.detect(mp_img)
                        hand_result = hand_lmk.detect(mp_img)

                        if face_result.face_landmarks:
                            lm  = face_result.face_landmarks[0]
                            ear = (_ear(lm, LEFT_EYE, w, h) + _ear(lm, RIGHT_EYE, w, h)) / 2.0

                            # ── Blink detection ─────────────────────────────
                            # Register the blink on the CLOSING edge (eyelid coming
                            # down), not on reopening.  This way any eye closure —
                            # quick blink or prolonged rest — resets the timer.
                            if ear < EAR_THRESHOLD:
                                self._blink_frames += 1
                                if self._blink_frames == CONSEC_FRAMES:
                                    self._blink_total += 1
                                    last_blink_time    = now
                                    alert_sent         = False
                                    self.blink_detected.emit(self._blink_total)
                            else:
                                self._blink_frames = 0

                            if (self._settings.blink_enabled and not alert_sent
                                    and (now - last_blink_time) > self._settings.blink_threshold):
                                alert_sent = True
                                self.no_blink_alert.emit()

                            # ── Drink detection ──────────────────────────────
                            hand_dist_ratio = _best_hand_dist(
                                lm, hand_result.hand_landmarks, w, h,
                            ) if hand_result.hand_landmarks else None

                            if hand_dist_ratio is not None and \
                                    _hand_near_mouth(lm, hand_result.hand_landmarks, w, h):
                                if drink_near_start is None:
                                    drink_near_start = now
                                elif now - drink_near_start >= DRINK_HOLD_SECONDS:
                                    water_start_time  = now
                                    water_alert_sent  = False
                                    drink_near_start  = None
                                    self.water_dismissed.emit()
                            else:
                                drink_near_start = None

                            # ── Face-return: reset clocks based on absence duration ──
                            if face_away_start is not None:
                                away = now - face_away_start
                                if sit_reset_pending or away >= SIT_RESET_AWAY:
                                    sit_start_time    = now
                                    sit_alert_sent    = False
                                    sit_reset_pending = False
                                # Water timer resets only after a long absence (5 min);
                                # a brief stand-up does NOT count as having had water
                                if away >= WATER_RESET_AWAY:
                                    water_start_time = now
                                    if water_alert_sent:
                                        water_alert_sent = False
                                        self.water_dismissed.emit()
                                face_away_start = None

                            # ── Sit break alert ──────────────────────────────
                            if (self._settings.sit_enabled and not sit_alert_sent
                                    and (now - sit_start_time) >= self._settings.sit_threshold_sec):
                                sit_alert_sent = True
                                self.sit_break_alert.emit()

                            # ── Water break alert ────────────────────────────
                            if (self._settings.water_enabled and not water_alert_sent
                                    and (now - water_start_time) >= self._settings.water_threshold_sec):
                                water_alert_sent = True
                                self.water_break_alert.emit()

                            _draw_stats_panel(
                                rgb, self._settings, ear, self._blink_total,
                                now - last_blink_time,
                                now - sit_start_time,
                                now - water_start_time,
                                hand_dist_ratio,
                                now - drink_near_start if drink_near_start else 0.0,
                            )

                        else:
                            # No face detected
                            last_blink_time  = now
                            alert_sent       = False
                            drink_near_start = None
                            if face_away_start is None:
                                face_away_start = now

                            # Dismiss sit alert when user stands up (face absent 3+ sec)
                            if sit_alert_sent and (now - face_away_start) >= SIT_AWAY_DISMISS:
                                sit_alert_sent    = False
                                sit_reset_pending = True
                                self.sit_break_away.emit()
                            # Water alert stays until: drink gesture, click, or 5-min absence

                            cv2.putText(rgb, "No face detected", (14, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (50, 50, 220), 2, cv2.LINE_AA)

                        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
                        self.frame_ready.emit(qimg.copy())

                    cap.release()

    def stop(self):
        self._running = False
        self.wait()
