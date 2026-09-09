# ai/fall_detection.py
# Detect a possible fall from pose landmarks + hip movement speed

import math
import config

class FallDetector:
    def __init__(self):
        self.previous_hip_y = None
        self.fall_alert_active = False

    def _body_angle(self, landmarks, mp_pose):
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

        shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_x = (left_hip.x + right_hip.x) / 2
        hip_y = (left_hip.y + right_hip.y) / 2

        dx = abs(shoulder_x - hip_x)
        dy = abs(shoulder_y - hip_y)
        return math.degrees(math.atan2(dy, dx)), hip_y

    def detect_fall(self, landmarks, mp_pose, video_fps):
        """
        Call once per processed frame.
        Returns:
        {
            "fall_detected": True/False,   # sticky/latched until reset()
            "trigger_now": True/False,     # true only on the exact triggering frame
            "confidence": 0.94,
            "body_angle": 78.0,
            "hip_drop_speed": 0.42
        }
        """
        body_angle, hip_y = self._body_angle(landmarks, mp_pose)

        hip_drop_speed = 0.0
        if self.previous_hip_y is not None:
            hip_drop_speed = (hip_y - self.previous_hip_y) * video_fps
        self.previous_hip_y = hip_y

        is_horizontal = body_angle < config.FALL_ANGLE_THRESHOLD
        is_fast_drop = hip_drop_speed > config.FALL_HIP_SPEED_THRESHOLD
        trigger_now = is_horizontal and is_fast_drop

        if trigger_now:
            self.fall_alert_active = True

        # Simple confidence: how far past threshold, capped at 1.0
        confidence = 0.0
        if trigger_now:
            angle_factor = max(0.0, (config.FALL_ANGLE_THRESHOLD - body_angle) / config.FALL_ANGLE_THRESHOLD)
            speed_factor = min(1.0, hip_drop_speed / (config.FALL_HIP_SPEED_THRESHOLD * 2))
            confidence = round(min(1.0, 0.5 + 0.25 * angle_factor + 0.25 * speed_factor), 2)

        return {
            "fall_detected": self.fall_alert_active,
            "trigger_now": trigger_now,
            "confidence": confidence,
            "body_angle": round(body_angle, 1),
            "hip_drop_speed": round(hip_drop_speed, 2)
        }

    def reset(self):
        """Call when caregiver presses 'acknowledge alert'."""
        self.fall_alert_active = False
        self.previous_hip_y = None