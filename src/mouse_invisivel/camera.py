"""Local preview in a worker thread, one latest frame slot, no raw recording."""
from dataclasses import dataclass
from pathlib import Path
import threading
import time
import numpy as np
from .features import Frame


@dataclass
class Packet:
    sequence: int
    timestamp: float
    rgb: np.ndarray | None
    landmark: Frame | None
    detail: str


class Camera:
    def __init__(self, index, model_path, hand):
        self.index, self.model_path, self.hand = index, str(model_path), hand
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.packet = None
        self.thread = threading.Thread(target=self._run, name="LocalCamera", daemon=True)

    def start(self):
        if not Path(self.model_path).is_file():
            raise ValueError("Select a licensed MediaPipe Hand Landmarker .task file first")
        self.thread.start()

    def latest(self):
        with self.lock:
            return self.packet

    def _set(self, packet):
        with self.lock:
            self.packet = packet

    def _run(self):
        cap, landmarker = None, None
        seq = 0
        try:
            import cv2
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
            options = HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=self.model_path),
                                            running_mode=RunningMode.VIDEO, num_hands=2,
                                            min_hand_detection_confidence=.6, min_hand_presence_confidence=.6,
                                            min_tracking_confidence=.6)
            landmarker = HandLandmarker.create_from_options(options)
            cap = cv2.VideoCapture(self.index)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not cap.isOpened():
                raise RuntimeError("Camera unavailable/permission denied. Check privacy settings and camera index.")
            last_ms = -1
            while not self.stop_event.is_set():
                started = time.monotonic()  # Include capture and inference delay in the stale-frame budget.
                ok, bgr = cap.read()
                if not ok or bgr is None:
                    raise RuntimeError("Camera read failed: disconnected, permission revoked or in use. Restart preview.")
                rgb = cv2.cvtColor(cv2.flip(bgr, 1), cv2.COLOR_BGR2RGB)
                timestamp_ms = max(last_ms + 1, int(started * 1000))
                last_ms = timestamp_ms
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                                                     timestamp_ms)
                candidates = [p for p, h in zip(result.hand_landmarks, result.handedness)
                              if h and h[0].category_name == self.hand and h[0].score >= .7]
                frame = None
                if len(candidates) == 1:
                    points = np.array([[p.x, p.y, p.z] for p in candidates[0]])
                    frame = Frame(started, points, self.hand)
                    for x, y, _ in points:
                        cv2.circle(rgb, (int(x*rgb.shape[1]), int(y*rgb.shape[0])), 3, (40, 240, 130), -1)
                seq += 1
                self._set(Packet(seq, started, rgb, frame,
                                 "Tracking " + self.hand if frame else "No selected hand / ambiguous tracking"))
        except Exception as e:
            seq += 1
            self._set(Packet(seq, time.monotonic(), None, None, str(e)))
        finally:
            if cap:
                cap.release()
            if landmarker:
                landmarker.close()

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=2)
        return not self.thread.is_alive()
