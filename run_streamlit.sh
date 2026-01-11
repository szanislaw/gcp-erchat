#!/bin/bash
# Script to run the Streamlit UI

# Make sure the FastAPI backend is running first
echo "Starting Streamlit UI..."
echo "Make sure the FastAPI backend is running on http://localhost:8080"
echo ""

streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
