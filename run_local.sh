#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Run Streamlit from the venv explicitly
exec /home/robebeaiwiz/shadow-tribunal/.venv/bin/python -m streamlit run streamlit_app/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501

