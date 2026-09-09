import time
from collections import Counter, deque
from datetime import datetime
from zoneinfo import ZoneInfo

import cv2
import mediapipe as mp
import streamlit as st

import config
from ai.activity_detection import ActivityDetector
from ai.fall_detection import FallDetector
from risk.risk_engine import RiskEngine


st.set_page_config(page_title="Eldercare Guardian AI", page_icon="🛡️", layout="wide")

ROOMS = {
    "Bedroom 1": {
        "video": "test_videos/bedroom1.mp4",
        "name": "Mr. Ram Sharma",
        "age": "72 years",
    },
    "Bedroom 2": {
        "video": "test_videos/bedroom2.mp4",
        "name": "Mrs. Sunita Sharma",
        "age": "68 years",
    },
    "Bedroom 3": {
        "video": "test_videos/bedroom3.mp4",
        "name": "Mr. Anil Kapoor",
        "age": "75 years",
    },
}

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
INDIA_TIME = ZoneInfo("Asia/Kolkata")

st.markdown(
    """
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {max-width: 1100px; padding-top: 1.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

for key, default in {
    "running": False,
    "alert_count": 0,
    "last_detection": "No detection",
    "alert_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("🛡️ Eldercare Guardian AI")
st.caption("Video safety monitoring")

selected_room = st.selectbox("📍 Select Room / Camera", list(ROOMS))
room = ROOMS[selected_room]

button_one, button_two = st.columns(2)
with button_one:
    start_button = st.button("▶ Start Monitoring", width="stretch")
with button_two:
    stop_button = st.button("■ Stop Monitoring", width="stretch")

if start_button:
    st.session_state.running = True
if stop_button:
    st.session_state.running = False

status_placeholder = st.empty()
video_placeholder = st.empty()
details_placeholder = st.empty()


def india_time_now():
    return datetime.now(INDIA_TIME).strftime("%I:%M:%S %p")


def stable_activity(history, current_activity):
    """Avoid changing the label because of one noisy pose frame."""
    history.append(current_activity)
    return Counter(history).most_common(1)[0][0]


if not st.session_state.running:
    status_placeholder.info("Choose a room and click Start Monitoring.")
    video_placeholder.markdown(
        "<div style='height:330px;display:flex;align-items:center;justify-content:center;"
        "background:#111827;color:#fff;border-radius:12px'>"
        "Video will appear here</div>",
        unsafe_allow_html=True,
    )
else:
    cap = cv2.VideoCapture(room["video"])
    if not cap.isOpened():
        st.error(f"Could not open video: {room['video']}")
        st.session_state.running = False
    else:
        source_fps = cap.get(cv2.CAP_PROP_FPS) or config.DEFAULT_FPS
        frame_skip = 3  # Process 10 frames per second from a 30-FPS video.
        display_fps = max(1, source_fps / frame_skip)
        frame_number = 0
        activity_history = deque(maxlen=7)

        fall_detector = FallDetector()
        activity_detector = ActivityDetector()
        risk_engine = RiskEngine()

        with mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:
            while cap.isOpened() and st.session_state.running:
                ok, frame = cap.read()
                if not ok:
                    break

                frame_number += 1
                if frame_number % frame_skip != 0:
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb_frame)

                activity_label = "No person detected"
                emergency = False
                reasons = ["No person detected"]
                fall_confidence = 0.0

                if results.pose_landmarks:
                    landmarks = results.pose_landmarks.landmark
                    fall_result = fall_detector.detect_fall(
                        landmarks, mp_pose, display_fps
                    )
                    activity_result = activity_detector.detect_activity(landmarks, mp_pose)
                    risk_result = risk_engine.assess(fall_result, activity_result)

                    activity_label = stable_activity(
                        activity_history, activity_result["activity"]
                    )
                    fall_confidence = fall_result["confidence"]

                    # A new fall must alert immediately. The old risk rule waited 30 seconds.
                    emergency = fall_result["trigger_now"] or risk_result["emergency"]
                    reasons = risk_result["reason"]
                    if fall_result["trigger_now"]:
                        reasons = ["Fast drop and horizontal posture detected"]
                        now = india_time_now()
                        st.session_state.alert_count += 1
                        st.session_state.last_detection = now
                        st.session_state.alert_history.insert(0, now)

                    mp_drawing.draw_landmarks(
                        frame,
                        results.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 170, 80), thickness=2, circle_radius=2),
                        mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2),
                    )

                if emergency:
                    status_placeholder.error(
                        f"🚨 FALL DETECTED — {room['name']} — {', '.join(reasons)}"
                    )
                else:
                    status_placeholder.success(
                        f"🟢 Monitoring {room['name']} in {selected_room}"
                    )

                video_placeholder.image(
                    cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                    channels="RGB",
                    width="stretch",
                )
                details_placeholder.info(
                    f"Current activity: **{activity_label.replace('_', ' ')}**  |  "
                    f"Fall confidence: **{fall_confidence}**  |  "
                    f"Alerts today: **{st.session_state.alert_count}**  |  "
                    f"Last alert: **{st.session_state.last_detection}**"
                )

                # Keep the original video duration while displaying fewer processed frames.
                time.sleep(1 / display_fps)

        cap.release()
        st.session_state.running = False
        st.info('Video ended. Click "Start Monitoring" to replay.')

if st.session_state.alert_history:
    st.subheader("📋 Fall Alert History")
    for alert_time in st.session_state.alert_history[:10]:
        st.write(f"🚨 Fall alert at {alert_time} — {selected_room}")
