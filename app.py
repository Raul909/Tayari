import spaces
import gradio as gr
import sys
import os
import traceback

@spaces.GPU
def dummy_gpu(text):
    return text

try:
    # Remove the root directory from sys.path to prevent 'app.py' from shadowing the 'app' module
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir in sys.path:
        sys.path.remove(root_dir)
    if '' in sys.path:
        sys.path.remove('')

    # Add backend directory to sys.path so we can import 'app.main'
    backend_dir = os.path.join(root_dir, "backend")
    sys.path.insert(0, backend_dir)
    os.chdir(backend_dir)

    import uvicorn
    from app.main import app as fastapi_app

    def api_status():
        return "Tayari API is running successfully on Hugging Face Spaces!"

    with gr.Blocks() as demo:
        gr.Markdown("# Tayari API Portal")
        gr.Markdown("This is the backend API server for the Tayari Flood Warning system. The frontend is hosted on Cloudflare Pages.")
        status_text = gr.Textbox(value=api_status(), label="API Status")
        
        # Dummy GPU component to satisfy ZeroGPU requirements
        with gr.Accordion("GPU Test (ZeroGPU Requirement)", open=False):
            in_text = gr.Textbox(label="Input")
            out_text = gr.Textbox(label="Output")
            btn = gr.Button("Test GPU")
            btn.click(fn=dummy_gpu, inputs=in_text, outputs=out_text)

    # Mount Gradio app onto our FastAPI app at root "/" (no conflict now as we renamed "/" to "/api/info" in main.py)
    # We set ssr_mode=False to disable the Node.js SSR sidecar process in Gradio 5.x.
    app = gr.mount_gradio_app(fastapi_app, demo, path="/", ssr_mode=False)

except Exception as e:
    error_traceback = traceback.format_exc()
    
    with gr.Blocks() as demo:
        gr.Markdown(f"# IMPORT ERROR\n```\n{error_traceback}\n```")
        with gr.Accordion("GPU Test (ZeroGPU Requirement)", open=False):
            in_text = gr.Textbox(label="Input")
            out_text = gr.Textbox(label="Output")
            btn = gr.Button("Test GPU")
            btn.click(fn=dummy_gpu, inputs=in_text, outputs=out_text)
            
    app = demo

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
