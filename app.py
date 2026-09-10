import cv2
import mediapipe as mp
import math

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

VIDEO_PATH = "test_videos/bedroom1.mp4"

# TUNABLE THRESHOLDS (adjust these based on testing)
ANGLE_THRESHOLD = 40          # body_angle below this = considered horizontal
SPEED_THRESHOLD = 0.9         # hip_drop_speed above this = fast downward motion
CONFIRM_FRAMES_NEEDED = 6     # must stay horizontal for this many consecutive frames to confirm a fall


cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"ERROR: Could not open video file: {VIDEO_PATH}")
    exit()

video_fps = cap.get(cv2.CAP_PROP_FPS)
if not video_fps or video_fps <= 0:
    video_fps = 30

print(f"Playing {VIDEO_PATH} at {video_fps:.1f} FPS")
print("Press 'q' to quit, 'r' to reset/acknowledge a fall alert.")

previous_hip_y = None
frame_number = 0

fall_alert_active = False       # sticky alert, stays on until 'r' is pressed
horizontal_streak = 0           # counts consecutive frames the body has been horizontal
fast_drop_seen_recently = False # was there a fast drop shortly before going horizontal?
fast_drop_cooldown = 0          # frames remaining where a recent fast-drop still "counts"

while True:
    ret, frame = cap.read()
    if not ret:
        print("Video ended.")
        break

    frame_number += 1

    body_angle = None
    hip_drop_speed = 0.0

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(rgb_frame)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark

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
        body_angle = math.degrees(math.atan2(dy, dx))

        if previous_hip_y is not None:
            hip_drop_speed = (hip_y - previous_hip_y) * video_fps
        previous_hip_y = hip_y

        is_horizontal = body_angle < ANGLE_THRESHOLD
        is_fast_drop_now = hip_drop_speed > SPEED_THRESHOLD

        if is_fast_drop_now:
            fast_drop_cooldown = 10
        elif fast_drop_cooldown > 0:
            fast_drop_cooldown -= 1
        fast_drop_seen_recently = fast_drop_cooldown > 0


        if is_horizontal and fast_drop_seen_recently:
            horizontal_streak += 1
        else:
            horizontal_streak = 0


        if horizontal_streak >= CONFIRM_FRAMES_NEEDED:
            fall_alert_active = True

        print(f"Frame {frame_number}: angle={body_angle:.1f}  hip_speed={hip_drop_speed:.2f}  "
              f"streak={horizontal_streak}  alert_active={fall_alert_active}")

        mp_drawing.draw_landmarks(
            frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
        )
    else:
        previous_hip_y = None
        horizontal_streak = 0
        print(f"Frame {frame_number}: no person detected")

    status_text = "FALL DETECTED!" if fall_alert_active else "Normal"
    status_color = (0, 0, 255) if fall_alert_active else (0, 255, 0)

    cv2.putText(frame, f"Status: {status_text}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    if body_angle is not None:
        cv2.putText(frame, f"Body angle: {body_angle:.1f}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Hip drop speed: {hip_drop_speed:.2f}", (10, 85),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(frame, f"Horizontal streak: {horizontal_streak}/{CONFIRM_FRAMES_NEEDED}", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
    if fall_alert_active:
        cv2.putText(frame, "Press 'r' to acknowledge/reset", (10, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    cv2.imshow("ElderCare AI Guardian - Fall Detection", frame)

    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'):
        print("Quitting...")
        break
    elif key == ord('r'):
        fall_alert_active = False
        horizontal_streak = 0
        print(">>> Alert manually reset/acknowledged <<<")

cap.release()
cv2.destroyAllWindows()