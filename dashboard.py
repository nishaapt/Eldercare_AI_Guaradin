import streamlit as st
import cv2
import mediapipe as mp
import time
from datetime import datetime

import config
from ai.fall_detection import FallDetector
from ai.activity_detection import ActivityDetector
from risk.risk_engine import RiskEngine


try:
    from notify import send_fall_alert_email
except Exception:
    send_fall_alert_email = None

try:
    from sms_alert import send_sms_alert
except Exception:
    send_sms_alert = None

try:
    # from call_caretaker import call_caretaker  # temporarily disabled — will re-enable later
    call_caretaker = None
except Exception:
    call_caretaker = None

st.set_page_config(page_title="Eldercare Guardian AI", page_icon="🛡️", layout="wide")

# ---------------------------------------------------------------------------
# ROOM CONFIG — add/edit rooms here. Each room needs its own test video.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# STYLING
# ---------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.main .block-container { opacity: 1 !important; }
div[data-testid="stAppViewContainer"] * { opacity: 1 !important; }

.stApp { background: #f4f7fb; }
.block-container { padding-top: 1.5rem; max-width: 1200px; }
.brand-row { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
.brand-title { font-size: 20px; font-weight: bold; color: #173f5f; }
.brand-sub { color: #4b5563; font-size: 14px; margin-bottom: 20px; }
.elder-card {
    background: white; padding: 22px; border-radius: 15px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.06); margin-bottom: 22px;
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;
}
.elder-card h2 { margin-bottom: 10px; font-size: 19px; color: #111827; }
.elder-card p { margin: 5px 0; color: #374151; font-size: 14px; }
.status-box { text-align: center; padding: 18px 32px; border-radius: 12px; min-width: 180px; }
.status-box.safe { background: #eaf8ee; }
.status-box.warning { background: #fff4e0; }
.status-box.emergency { background: #ffe5e5; }
.status-box .icon { font-size: 30px; display: block; }
.status-box h3 { font-size: 20px; margin: 4px 0; }
.status-box.safe h3 { color: #16803c; }
.status-box.warning h3 { color: #b8720a; }
.status-box.emergency h3 { color: #d62828; }
.status-box p { font-size: 12px; color: #374151; margin: 0; }
.monitoring { background: white; padding: 22px; border-radius: 15px; margin-bottom: 22px; box-shadow: 0 3px 12px rgba(0,0,0,0.06); }
.monitor-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.monitor-header h2 { margin-bottom: 3px; font-size: 18px; color: #111827; }
.monitor-header p { color: #4b5563; font-size: 13px; }
.live-indicator { background: #ffe5e5; color: #d62828; padding: 7px 14px; border-radius: 20px; font-size: 13px; font-weight: bold; }
.camera-info { display: flex; justify-content: space-between; margin-top: 10px; padding: 8px 4px; font-size: 13px; color: #374151; font-weight: 600; }
.stat-card { background: white; padding: 18px 20px; border-radius: 15px; box-shadow: 0 3px 12px rgba(0,0,0,0.06); }
.stat-card h3 { font-size: 14px; color: #374151; font-weight: 700; }
.stat-card .value { font-size: 26px; font-weight: bold; margin-top: 10px; color: #111827; }
.alerts-card { background: white; padding: 22px; border-radius: 15px; box-shadow: 0 3px 12px rgba(0,0,0,0.06); margin-bottom: 22px; }
.no-alert { color: #374151; font-size: 15px; }
.alert-entry {
    background: #fff0f0;
    border-left: 6px solid #d62828;
    padding: 16px 18px;
    border-radius: 10px;
    margin-bottom: 12px;
    font-size: 15px;
    line-height: 1.6;
    color: #5b1111;
    font-weight: 600;
}
.alert-entry strong { color: #7a1717; font-size: 16px; }
div[data-testid="stButton"] button { border-radius: 8px; font-weight: bold; padding: 10px 0; border: none; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
for key, default in [
    ("running", False), ("alert_count", 0), ("last_detection", "No detection"),
    ("alert_history", []), ("prev_emergency_state", False), ("notified_this_alert", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

st.markdown("""
<div class="brand-row"><span style="font-size:26px;">🛡️</span><span class="brand-title">Eldercare Guardian AI</span></div>
<div class="brand-sub">Real-time safety dashboard</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ROOM SELECTOR
# ---------------------------------------------------------------------------
selected_room = st.selectbox("📍 Select Room / Camera", list(ROOMS.keys()))

VIDEO_PATH = ROOMS[selected_room]["video"]
ELDER_NAME = ROOMS[selected_room]["name"]
ELDER_AGE = ROOMS[selected_room]["age"]
ELDER_ROOM = selected_room

if "last_room" not in st.session_state:
    st.session_state.last_room = selected_room

if st.session_state.last_room != selected_room:
    st.session_state.running = False
    st.session_state.prev_emergency_state = False
    st.session_state.notified_this_alert = False
    st.session_state.last_room = selected_room

elder_status_placeholder = st.empty()

col_buttons1, col_buttons2, col_buttons3 = st.columns(3)
with col_buttons1:
    start_button = st.button("▶ Start Monitoring", use_container_width="stretch")
with col_buttons2:
    reset_button = st.button("✓ Acknowledge Alert", use_container_width="stretch")
with col_buttons3:
    call_button = st.button("📞 Call Caretaker", use_container_width="stretch")

if reset_button:
    st.session_state.prev_emergency_state = False
    st.session_state.notified_this_alert = False

if call_button:
    now_str = datetime.now().strftime("%I:%M:%S %p")
    if send_sms_alert is not None:
        try:
            send_sms_alert(ELDER_NAME, ELDER_ROOM, now_str)
        except Exception as e:
            print(f"ERROR: SMS alert failed: {e}")
    if call_caretaker is not None:
        try:
            call_caretaker(ELDER_NAME, ELDER_ROOM, now_str)
        except Exception as e:
            print(f"ERROR: call alert failed: {e}")
    st.error("📞 Emergency alert sent to caretaker!")

if start_button:
    st.session_state.running = True

st.markdown('<div class="monitoring">', unsafe_allow_html=True)
st.markdown(f"""
<div class="monitor-header">
    <div><h2>📹 Live Monitoring</h2><p>{ELDER_ROOM} Camera</p></div>
    <div class="live-indicator">🔴 LIVE</div>
</div>
""", unsafe_allow_html=True)
video_placeholder = st.empty()
camera_info_placeholder = st.empty()
st.markdown('</div>', unsafe_allow_html=True)

stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    alert_count_placeholder = st.empty()
with stat_col2:
    last_detection_placeholder = st.empty()
with stat_col3:
    activity_stat_placeholder = st.empty()

st.markdown('<div class="alerts-card">', unsafe_allow_html=True)
st.markdown(
    '<h2 style="color:#111827; font-size:18px; font-weight:800; margin-bottom:12px;">📋 Alert History</h2>',
    unsafe_allow_html=True,
)
alert_history_placeholder = st.empty()
st.markdown('</div>', unsafe_allow_html=True)

with st.expander("Technical details (for the tech team)"):
    tech_details_placeholder = st.empty()


def render_elder_status(risk_level, emergency, reasons):
    if emergency:
        css_class, icon, word = "emergency", "🔴", "FALL DETECTED"
    elif risk_level in ("HIGH", "MODERATE"):
        css_class, icon, word = "warning", "🟡", "WARNING"
    else:
        css_class, icon, word = "safe", "🟢", "SAFE"

    reason_text = ", ".join(reasons) if reasons else "No fall detected"

    elder_status_placeholder.markdown(f"""
    <div class="elder-card">
        <div>
            <h2>👵 Elder Information</h2>
            <p><strong>Name:</strong> {ELDER_NAME}</p>
            <p><strong>Age:</strong> {ELDER_AGE}</p>
            <p><strong>Room:</strong> {ELDER_ROOM}</p>
        </div>
        <div class="status-box {css_class}">
            <span class="icon">{icon}</span>
            <h3>{word}</h3>
            <p>{reason_text}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_stat_cards(alert_count, last_detection, activity_label):
    alert_count_placeholder.markdown(f"""
    <div class="stat-card"><h3>🚨 Today's Alerts</h3><div class="value">{alert_count}</div></div>
    """, unsafe_allow_html=True)
    last_detection_placeholder.markdown(f"""
    <div class="stat-card"><h3>⏰ Last Detection</h3><div class="value" style="font-size:16px;">{last_detection}</div></div>
    """, unsafe_allow_html=True)
    activity_stat_placeholder.markdown(f"""
    <div class="stat-card"><h3>🚶 Current Activity</h3><div class="value" style="font-size:18px;">{activity_label}</div></div>
    """, unsafe_allow_html=True)


def render_alert_history():
    if not st.session_state.alert_history:
        alert_history_placeholder.markdown('<p class="no-alert">No alerts yet.</p>', unsafe_allow_html=True)
    else:
        entries = ""
        for entry in st.session_state.alert_history[:10]:
            entries += f"""
            <div class="alert-entry">
                🚨 <strong>Fall Detected</strong><br>
                Elder: {ELDER_NAME}<br>
                Location: {ELDER_ROOM}<br>
                Time: {entry}
            </div>
            """
        alert_history_placeholder.markdown(entries, unsafe_allow_html=True)


if not st.session_state.running:
    render_elder_status("LOW", False, [])
    video_placeholder.markdown(
        '<div style="background:#111827; height:330px; border-radius:12px; display:flex; align-items:center; justify-content:center; color:#e5e7eb;">Video will appear here — click Start Monitoring</div>',
        unsafe_allow_html=True)
    camera_info_placeholder.markdown(
        '<div class="camera-info"><span>📹 Camera</span><span>⚪ Standing by</span><span>⏱ Not active</span></div>',
        unsafe_allow_html=True)
    render_stat_cards(st.session_state.alert_count, st.session_state.last_detection, "—")
    render_alert_history()

if st.session_state.running:
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    cap = cv2.VideoCapture(VIDEO_PATH)

    fall_detector = FallDetector()
    activity_detector = ActivityDetector()
              FRAME_SKIP = 3
              processed_frame_count = 0

    if not cap.isOpened():
        st.error(f"Could not open video: {VIDEO_PATH}")
    else:
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if not video_fps or video_fps <= 0:
            video_fps = config.DEFAULT_FPS

        activity_label_map = {
            "WALKING": "🚶 Walking", "SITTING": "🪑 Sitting", "STANDING": "🧍 Standing",
            "LYING": "🛏️ Lying Down", "NO_MOVEMENT": "⏸️ Not Moving",
        }

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark

                fall_result = fall_detector.detect_fall(landmarks, mp_pose, video_fps)
                activity_result = activity_detector.detect_activity(landmarks, mp_pose)
                risk_result = risk_engine.assess(fall_result, activity_result)

                mp_drawing.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(23, 63, 95), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
            else:
                # No person detected this frame — treat as no new signal
                fall_result = {"fall_detected": False, "trigger_now": False, "confidence": 0.0,
                                "body_angle": 0.0, "hip_drop_speed": 0.0}
                activity_result = {"activity": "STANDING", "confidence": 0.0,
                                    "movement": False, "inactivity_duration": 0.0}
                risk_result = {"risk_score": 0, "risk_level": "LOW", "emergency": False,
                                "reason": ["No person detected"]}

            # Fire alerts (email/SMS/call) only on a NEW emergency, not every frame it stays true
            if risk_result["emergency"] and not st.session_state.prev_emergency_state:
                now_str = datetime.now().strftime("%I:%M:%S %p")
                st.session_state.alert_count += 1
                st.session_state.last_detection = now_str
                st.session_state.alert_history.insert(0, now_str)
                st.session_state.notified_this_alert = False

            if risk_result["emergency"] and not st.session_state.notified_this_alert:
                if send_fall_alert_email is not None:
                    try:
                        send_fall_alert_email(ELDER_NAME, ELDER_ROOM, st.session_state.last_detection)
                    except Exception as e:
                        print(f"ERROR: email alert failed: {e}")
                if send_sms_alert is not None:
                    try:
                        send_sms_alert(ELDER_NAME, ELDER_ROOM, st.session_state.last_detection)
                    except Exception as e:
                        print(f"ERROR: SMS alert failed: {e}")
                if call_caretaker is not None:
                    try:
                        call_caretaker(ELDER_NAME, ELDER_ROOM, st.session_state.last_detection)
                    except Exception as e:
                        print(f"ERROR: call alert failed: {e}")
                st.session_state.notified_this_alert = True

            st.session_state.prev_emergency_state = risk_result["emergency"]

            activity_label = activity_label_map.get(activity_result["activity"], activity_result["activity"])

            render_elder_status(risk_result["risk_level"], risk_result["emergency"], risk_result["reason"])
            render_stat_cards(st.session_state.alert_count, st.session_state.last_detection, activity_label)
            render_alert_history()

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            camera_info_placeholder.markdown(
                '<div class="camera-info"><span>📹 Camera</span><span>🟢 Camera Online</span><span>⏱ Monitoring Active</span></div>',
                unsafe_allow_html=True)

            tech_details_placeholder.markdown(f"""
            Risk score: {risk_result['risk_score']}/100 ({risk_result['risk_level']})  
            Emergency: {risk_result['emergency']}  
            Activity: {activity_result['activity']} (confidence {activity_result['confidence']})  
            Fall confidence: {fall_result['confidence']}  
            Body angle: {fall_result['body_angle']}° | Hip drop speed: {fall_result['hip_drop_speed']}  
            Inactivity: {activity_result['inactivity_duration']}s  
            Reasons: {', '.join(risk_result['reason'])}
            """)

            time.sleep(1 / video_fps)

        cap.release()
        st.session_state.running = False
        st.info('Video ended. Click "Start Monitoring" to replay.')
