"""Fall detection for the Eldercare Guardian dashboard."""

import math


class FallDetector:
    def __init__(self):
        self.previous_hip_y = None
        self.horizontal_frames = 0
        self.fall_alert_active = False
        self.last_confidence = 0.0

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

        angle = math.degrees(math.atan2(abs(shoulder_y - hip_y), abs(shoulder_x - hip_x)))
        return angle, hip_y

    def detect_fall(self, landmarks, mp_pose, video_fps):
        """Return a fall event when a person becomes horizontal for several frames."""
        body_angle, hip_y = self._body_angle(landmarks, mp_pose)
        hip_drop_speed = 0.0
        if self.previous_hip_y is not None:
            hip_drop_speed = (hip_y - self.previous_hip_y) * video_fps
        self.previous_hip_y = hip_y

        is_horizontal = body_angle < 45
        if is_horizontal:
            self.horizontal_frames += 1
        else:
            self.horizontal_frames = 0

        # The old code required a single exact fast-drop frame. A test video often
        # misses that frame, so sustained horizontal posture also triggers an alert.
        fast_drop = hip_drop_speed > 0.30
        trigger_now = not self.fall_alert_active and is_horizontal and (
            fast_drop or self.horizontal_frames >= 5
        )

        if trigger_now:
            self.fall_alert_active = True
            angle_score = max(0.0, min(1.0, (45 - body_angle) / 45))
            speed_score = max(0.0, min(1.0, hip_drop_speed / 0.60))
            self.last_confidence = round(max(0.75, 0.65 + 0.2 * angle_score + 0.15 * speed_score), 2)

        return {
            "fall_detected": self.fall_alert_active,
            "trigger_now": trigger_now,
            "confidence": self.last_confidence if self.fall_alert_active else 0.0,
            "body_angle": round(body_angle, 1),
            "hip_drop_speed": round(hip_drop_speed, 2),
        }

    def reset(self):
        self.previous_hip_y = None
        self.horizontal_frames = 0
        self.fall_alert_active = False
        self.last_confidence = 0.0
