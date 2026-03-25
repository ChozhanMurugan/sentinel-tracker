# Sentinel ML Intelligence Layer

A lightweight FastAPI service integrated with the Sentinel Tracker to perform real-time flight anomaly detection and military aircraft classification. 

## Core Features

- **Real-time Anomaly Detection**: 
    - Implements **Isolation Forest** unsupervised learning to identify unusual flight behaviors.
    - Detects deviations in altitude, speed, heading, and erratic flight patterns.
- **Dynamic Self-Training**:
    - The model trains and periodically re-fits on live incoming data.
    - No pre-trained model files are required; it adapts dynamically to the current global or local flight environment.
- **Explainable Anomaly Scoring**:
    - Generates human-readable reasons for flagged aircraft (e.g., *"unusually fast"*, *"steep descent"*, *"circling / orbit pattern detected"*).
- **Enhanced Military Classifier**:
    - **Multi-layered Heuristics**: Combines ICAO hex-prefix matching with tactical callsign regex analysis.
    - **Broad Coverage**: Identifies aircraft from major air forces (USAF, RAF, VKS Russia, PLAAF, etc.).
- **Real-time Alerts via WebSocket**:
    - Broadcasts anomaly notifications to connected frontend clients as they happen.
- **FastAPI Integration**:
    - Clean REST API for querying latest anomalies and detector statistics.

## Project Structure

- `app/anomaly.py`: Isolation Forest implementation and anomaly explanation logic.
- `app/classifier.py`: Heuristic-based military classification layer.
- `app/collector.py`: Flight data buffering and preprocessing.
- `app/features.py`: Feature engineering for ML models (turn rates, variances, etc.).
- `app/broadcaster.py`: WebSocket manager for real-time result delivery.

## Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Service**:
   ```bash
   python run.py
   ```
   The service will start on port `8001` (default) and begin collecting data from the main Sentinel backend/Redis.
