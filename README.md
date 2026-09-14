# 🛡️ ElderCare AI Guardian

> An AI-powered elderly safety monitoring system that uses computer vision, pose estimation, activity recognition, fall detection, and risk assessment to help monitor elderly individuals in real time.

<p align="center">
  <strong>AI-powered • Computer Vision • Real-time Monitoring • Risk Assessment</strong>
</p>

---

## 📌 Overview

**ElderCare AI Guardian** is an intelligent elderly safety monitoring system designed to detect and analyze activities and potentially dangerous situations using computer vision.

The system processes video from monitored rooms and uses **MediaPipe Pose** landmarks to understand human posture and movement. It can identify activities such as:

- 🧍 Standing
- 🚶 Walking
- 🪑 Sitting
- 🛏️ Lying
- ⏸️ No movement
- 🚨 Potential falls

The detected activity is combined with fall-detection information and inactivity duration to calculate an overall **risk score** and classify the situation as:

- 🟢 Low
- 🟡 Moderate
- 🟠 High
- 🔴 Critical

A Streamlit-based dashboard provides a visual monitoring interface with room selection, live video processing, activity information, risk status, and alert history.

---

## 🎯 Problem Statement

Elderly individuals, especially those living alone or requiring assisted care, can face safety risks such as:

- Falls
- Prolonged inactivity
- Sudden changes in movement
- Remaining on the floor after a fall
- Delayed emergency response

Traditional monitoring often requires continuous human supervision.

**ElderCare AI Guardian** aims to provide an automated computer-vision-based monitoring layer that can continuously analyze video and highlight potentially dangerous situations.

---

## 💡 Proposed Solution

The system combines multiple computer vision components into a single monitoring pipeline:

```text
                ┌─────────────────────┐
                │   Video / Camera    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  MediaPipe Pose     │
                │  Landmark Detection │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
     ┌─────────────────┐       ┌─────────────────┐
     │ Activity        │       │ Fall Detection  │
     │ Detection       │       │                 │
     └────────┬────────┘       └────────┬────────┘
              │                         │
              └────────────┬────────────┘
                           ▼
                ┌─────────────────────┐
                │    Risk Engine      │
                │                     │
                │ Risk Score / Level  │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Streamlit Dashboard │
                └──────────┬──────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
          Status / Alerts       Caretaker Alert
