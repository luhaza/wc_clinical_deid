#!/bin/bash
# Launch script for Clinical De-identification Pipeline

echo "Starting Clinical De-identification Pipeline..."
echo "Make sure conda environment 'deid-pipeline' is activated!"
echo ""

# Check if streamlit is installed
if ! python -c "import streamlit" &> /dev/null
then
    echo "Streamlit not found. Installing..."
    pip install streamlit
fi

# Check if Tesseract is installed
if ! command -v tesseract &> /dev/null
then
    echo "WARNING: Tesseract not found!"
    echo "Install with: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)"
    echo ""
fi

# Run the app using python -m to avoid PATH issues
python -m streamlit run app.py
