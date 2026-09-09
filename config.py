# Central place for all tunable thresholds — change values here, not inside logic files

# Fall detection thresholds
FALL_ANGLE_THRESHOLD = 40        # degrees; below this = considered horizontal
FALL_HIP_SPEED_THRESHOLD = 0.9   # normalized hip-y units per second; above this = fast drop

# Activity recognition thresholds
STANDING_ANGLE_MIN = 60          # degrees; above this = upright posture
SITTING_ANGLE_MIN = 40           # between sitting/standing range
MOVEMENT_THRESHOLD = 0.04       # normalized landmark movement per frame to count as "moving"
NO_MOVEMENT_SECONDS = 5          # seconds of stillness before flagging NO_MOVEMENT

# Video/camera settings
DEFAULT_FPS = 30

# Risk engine thresholds
RISK_LOW_MAX = 30
RISK_MODERATE_MAX = 60
RISK_HIGH_MAX = 80
# 81-100 = CRITICAL

EMERGENCY_RISK_THRESHOLD = 81
EMERGENCY_NO_MOVEMENT_SECONDS = 30   # required stillness before an emergency can trigger
