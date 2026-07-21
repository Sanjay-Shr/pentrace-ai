#!/bin/bash
# Starts FastAPI sandbox in background, then Streamlit on port 7860

uvicorn sandbox.main:app --host 0.0.0.0 --port 8001 &

streamlit run ui/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.fileWatcherType none \
    --browser.gatherUsageStats false