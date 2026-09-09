import math
import time
from collections import deque


class ActivityDetector:
    def __init__(self):
        self.previous_points = None
        self.last_movement_time = time.monotonic()
        self.motion_history = deque(maxlen=4)

    @staticmethod
    def _body_angle(landmarks, mp_pose):
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
        shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_x = (left_hip.x + right_hip.x) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        return math.degrees(math.atan2(abs(shoulder_y - hip_y), abs(shoulder_x - hip_x)))

    @staticmethod
    def _core_points(landmarks, mp_pose):
        keys = (
            mp_pose.PoseLandmark.LEFT_SHOULDER,
            mp_pose.PoseLandmark.RIGHT_SHOULDER,
            mp_pose.PoseLandmark.LEFT_HIP,
            mp_pose.PoseLandmark.RIGHT_HIP,
            mp_pose.PoseLandmark.LEFT_ANKLE,
            mp_pose.PoseLandmark.RIGHT_ANKLE,
        )
        return [(landmarks[key].x, landmarks[key].y) for key in keys]

    def detect_activity(self, landmarks, mp_pose):
        now = time.monotonic()
        body_angle = self._body_angle(landmarks, mp_pose)
        points = self._core_points(landmarks, mp_pose)

        motion = 0.0
        if self.previous_points is not None:
            motion = sum(math.hypot(x - px, y - py) for (x, y), (px, py) in zip(points, self.previous_points)) / len(points)
        self.previous_points = points
        self.motion_history.append(motion)

        average_motion = sum(self.motion_history) / len(self.motion_history)
        is_moving = average_motion > 0.012
        if is_moving:
            self.last_movement_time = now
        inactivity_duration = now - self.last_movement_time

        if body_angle < 45:
            activity, confidence = "LYING", 0.90
        elif body_angle < 65:
            activity, confidence = "SITTING", 0.78
        elif average_motion > 0.020:
            activity, confidence = "WALKING", 0.76
        elif inactivity_duration > 8:
            activity, confidence = "NO_MOVEMENT", 0.82
        else:
            activity, confidence = "STANDING", 0.82

        return {
            "activity": activity,
            "confidence": confidence,
            "movement": is_moving,
            "inactivity_duration": round(inactivity_duration, 1),
        }
