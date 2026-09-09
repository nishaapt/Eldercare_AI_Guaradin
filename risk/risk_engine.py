# Combine fall detection + activity data into a single risk score and decision

import config

class RiskEngine:
    def __init__(self):
        self.previous_activity = None

    def assess(self, fall_result: dict, activity_result: dict) -> dict:
        """
        fall_result: output from FallDetector.detect_fall()
        activity_result: output from ActivityDetector.detect_activity()

        Returns:
        {
            "risk_score": 91,
            "risk_level": "CRITICAL",
            "emergency": True,
            "reason": ["High fall confidence", "No movement", "Prolonged inactivity"]
        }
        """
        score = 0
        reasons = []

        fall_confidence = fall_result.get("confidence", 0.0)
        fall_active = fall_result.get("fall_detected", False)
        activity = activity_result.get("activity", "STANDING")
        movement = activity_result.get("movement", True)
        inactivity_duration = activity_result.get("inactivity_duration", 0.0)


        if fall_active:
            score += fall_confidence * 50
            if fall_confidence >= 0.8:
                reasons.append("High fall confidence")
            elif fall_confidence >= 0.5:
                reasons.append("Moderate fall confidence")


        if activity == "NO_MOVEMENT":
            score += 20
            reasons.append("No movement")
        elif activity == "LYING" and self.previous_activity not in ("LYING", None):
            # Only add risk for lying if it wasn't already the previous state
            # (prevents penalizing someone who has been resting normally)
            score += 5


        if inactivity_duration > config.NO_MOVEMENT_SECONDS:
            extra = min(30, (inactivity_duration - config.NO_MOVEMENT_SECONDS) * 1.5)
            score += extra
            if inactivity_duration > config.EMERGENCY_NO_MOVEMENT_SECONDS:
                reasons.append("Prolonged inactivity")

        score = round(min(100, max(0, score)))


        if score <= config.RISK_LOW_MAX:
            level = "LOW"
        elif score <= config.RISK_MODERATE_MAX:
            level = "MODERATE"
        elif score <= config.RISK_HIGH_MAX:
            level = "HIGH"
        else:
            level = "CRITICAL"


        emergency = fall_result.get("trigger_now", False) or (
    score >= config.EMERGENCY_RISK_THRESHOLD
    and inactivity_duration >= config.EMERGENCY_NO_MOVEMENT_SECONDS
)

        if not reasons:
            reasons.append("Normal activity")

        self.previous_activity = activity

        return {
            "risk_score": score,
            "risk_level": level,
            "emergency": emergency,
            "reason": reasons
        }
