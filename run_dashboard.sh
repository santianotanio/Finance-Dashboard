#!/usr/bin/env bash
# Finance Dashboard - launcher (Linux / macOS)
cd "$(dirname "$0")"
if [ -f ".venv/bin/streamlit" ]; then
    ./.venv/bin/streamlit run app.py --server.port 8501 --server.runOnSave true
elif [ -f ".fedora.financedashboard/bin/streamlit" ]; then
    ./.fedora.financedashboard/bin/streamlit run app.py --server.port 8501 --server.runOnSave true
else
    streamlit run app.py --server.port 8501 --server.runOnSave true
fi
