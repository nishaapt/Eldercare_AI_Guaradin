# ai/activity_detection.py

import math
import time
import config

class ActivityDetector:
    def __init__(self):
        self.previous_landmarks = None
        self.last_movement_time = time.time()
        self.timeline = []

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
        return math.degrees(math.atan2(dy, dx))

    def _knee_bend_ratio(self, landmarks, mp_pose):
        left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
        left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
        left_ankle = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE]

        hip_knee = abs(left_knee.y - left_hip.y)
        knee_ankle = abs(left_ankle.y - left_knee.y)

        if knee_ankle == 0:
            return 1.0
        return hip_knee / knee_ankle

    def _movement_amount(self, landmarks):
        if self.previous_landmarks is None:
            return 0.0
        total_movement = 0.0
        for i, lm in enumerate(landmarks):
            prev = self.previous_landmarks[i]
            total_movement += math.hypot(lm.x - prev.x, lm.y - prev.y)
        return total_movement / len(landmarks)

    def detect_activity(self, landmarks, mp_pose):
        now = time.time()
        body_angle = self._body_angle(landmarks, mp_pose)
        movement = self._movement_amount(landmarks)
        is_moving = movement > config.MOVEMENT_THRESHOLD

        if is_moving:
            self.last_movement_time = now
        inactivity_duration = now - self.last_movement_time

        activity = "STANDING"
        confidence = 0.6

        if body_angle < config.FALL_ANGLE_THRESHOLD:
            activity = "LYING"
            confidence = 0.9
        elif inactivity_duration > config.NO_MOVEMENT_SECONDS:
            activity = "NO_MOVEMENT"
            confidence = 0.85
        elif is_moving and body_angle > config.STANDING_ANGLE_MIN:
            activity = "WALKING"
            confidence = 0.8
        elif body_angle >= config.STANDING_ANGLE_MIN:
            knee_ratio = self._knee_bend_ratio(landmarks, mp_pose)
            activity = "SITTING" if knee_ratio < 0.5 else "STANDING"
            confidence = 0.75 if activity == "SITTING" else 0.8
        elif config.SITTING_ANGLE_MIN <= body_angle < config.STANDING_ANGLE_MIN:
            activity = "SITTING"
            confidence = 0.7

        self.previous_landmarks = landmarks
        self.timeline.append((now, activity))

        return {
            "activity": activity,
            "confidence": confidence,
            "movement": is_moving,
            "inactivity_duration": round(inactivity_duration, 1)
        }

    def get_timeline(self):
        return [
            (time.strftime("%H:%M:%S", time.localtime(t)), act)
            for t, act in self.timeline
        ]