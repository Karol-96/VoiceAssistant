#!/bin/bash

# Get the directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Add the project root to PYTHONPATH
export PYTHONPATH="$DIR:$PYTHONPATH"

# Run Streamlit
streamlit run "streamlit_app.py"