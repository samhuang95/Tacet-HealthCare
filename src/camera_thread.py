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
_BASE_DIR   = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) \
              else os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_MODEL_DIR  = os.path.join(_BASE_DIR, "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "face_landmarker.task")
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [263, 387, 385, 362, 380, 373]

EAR_THRESHOLD         = 0.25
CONSEC_FRAMES         = 2
NO_BLINK_THRESHOLD    = 5.0        # seconds before blink alert
SIT_BREAK_THRESHOLD   = 30 * 60  # 30 minutes before sit break alert
SIT_RESET_AWAY        = 5   * 60  # 5 minutes without face resets sit timer
SIT_AWAY_DISMISS      = 3.0       # seconds face must be absent to dismiss break alert
RECONNECT_FAIL_LIMIT  = 30
RECONNECT_INTERVAL_MS = 1500


def _ear(landmarks, indices, w, h):
    pts = [(landmarks[i].x * w, landmarks[i].y * h) for i in indices]
    v1 = np.hypot(pts[1][0] - pts[5][0], pts[1][1] - pts[5][1])
    v2 = np.hypot(pts[2][0] - pts[4][0], pts[2][1] - pts[4][1])
    hz = np.hypot(pts[0][0] - pts[3][0], pts[0][1] - pts[3][1])
    return (v1 + v2) / (2.0 * hz + 1e-6)


def _ensure_model(status_cb=None) -> str:
    os.makedirs(_MODEL_DIR, exist_ok=True)
    if not os.path.exists(_MODEL_PATH):
        if status_cb:
            status_cb("Downloading face detection model (~3.7 MB)...")
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    return os.path.abspath(_MODEL_PATH)


class CameraThread(QThread):
    frame_ready      = pyqtSignal(QImage)
    blink_detected   = pyqtSignal(int)   # total blink count
    no_blink_alert   = pyqtSignal()      # fired once when > NO_BLINK_THRESHOLD seconds without blink
    sit_break_alert  = pyqtSignal()      # fired once when sitting > SIT_BREAK_THRESHOLD seconds
    sit_break_away   = pyqtSignal()      # fired when user stands up while break alert is showing
    status_changed   = pyqtSignal(str)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self._camera_index = camera_index
        self._running      = False
        self._blink_frames = 0
        self._blink_total  = 0
        self._reset_sit    = False

    def reset_sit_timer(self):
        self._reset_sit = True

    def run(self):
        self._running = True

        try:
            model_path = _ensure_model(self.status_changed.emit)
        except Exception as e:
            self.status_changed.emit(f"Model download failed: {e}")
            return

        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        with mp_vision.FaceLandmarker.create_from_options(options) as landmarker:
            while self._running:
                cap = cv2.VideoCapture(self._camera_index)
                if not cap.isOpened():
                    self.status_changed.emit(
                        f"Cannot open camera {self._camera_index}, retrying..."
                    )
                    self.msleep(RECONNECT_INTERVAL_MS)
                    continue

                self.status_changed.emit(f"Camera {self._camera_index} connected")

                last_blink_time   = time.monotonic()
                alert_sent        = False
                fail_count        = 0
                sit_start_time    = time.monotonic()
                sit_alert_sent    = False
                sit_reset_pending = False
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

                    # Apply external sit-timer reset (e.g. user dismissed break alert)
                    if self._reset_sit:
                        self._reset_sit = False
                        sit_start_time  = now
                        sit_alert_sent  = False

                    h, w = frame.shape[:2]
                    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    result = landmarker.detect(mp_img)

                    if result.face_landmarks:
                        lm  = result.face_landmarks[0]
                        ear = (_ear(lm, LEFT_EYE, w, h) + _ear(lm, RIGHT_EYE, w, h)) / 2.0

                        if ear < EAR_THRESHOLD:
                            self._blink_frames += 1
                        else:
                            if self._blink_frames >= CONSEC_FRAMES:
                                self._blink_total  += 1
                                last_blink_time     = now
                                alert_sent          = False
                                self.blink_detected.emit(self._blink_total)
                            self._blink_frames = 0

                        # Fire blink alert once when threshold exceeded
                        if not alert_sent and (now - last_blink_time) > NO_BLINK_THRESHOLD:
                            alert_sent = True
                            self.no_blink_alert.emit()

                        # Sit break timer: reset sit clock if returning after standing-up dismiss
                        # or after a long absence
                        if face_away_start is not None:
                            if sit_reset_pending or (now - face_away_start) >= SIT_RESET_AWAY:
                                sit_start_time    = now
                                sit_alert_sent    = False
                                sit_reset_pending = False
                            face_away_start = None

                        # Fire sit break alert once when threshold exceeded
                        if not sit_alert_sent and (now - sit_start_time) >= SIT_BREAK_THRESHOLD:
                            sit_alert_sent = True
                            self.sit_break_alert.emit()

                        overlay = f"EAR: {ear:.3f}  |  Blinks: {self._blink_total}"
                        color   = (0, 200, 80)
                    else:
                        # No face — reset blink timer and start tracking absence
                        last_blink_time = now
                        alert_sent      = False
                        if face_away_start is None:
                            face_away_start = now

                        # Dismiss break alert only after face has been gone long enough
                        # (filters out brief look-aways; only triggers when user truly left)
                        if sit_alert_sent and (now - face_away_start) >= SIT_AWAY_DISMISS:
                            sit_alert_sent    = False
                            sit_reset_pending = True
                            self.sit_break_away.emit()

                        overlay = "No face detected"
                        color   = (60, 60, 255)

                    cv2.putText(rgb, overlay, (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

                    qimg = QImage(rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
                    self.frame_ready.emit(qimg.copy())

                cap.release()

    def stop(self):
        self._running = False
        self.wait()
