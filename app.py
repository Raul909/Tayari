import uvicorn
import os

# Ensure the backend module can be imported
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.app.main import app

if __name__ == "__main__":
    # Hugging Face Spaces Gradio/Streamlit environments run on port 7860
    # We use 2 workers to leverage the 2 vCPUs on the free tier
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=7860, workers=2)
