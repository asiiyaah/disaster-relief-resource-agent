import os
import sys
import re
import time
import gradio as gr
from dotenv import load_dotenv

# Ensure the app folder is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(override=True)

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent

# Initialize the ADK services
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, session_service=session_service, app_name="disaster-relief")

# A mapping to track session IDs per chat thread
sessions = {}

def respond(message: str, chat_history, request: gr.Request):
    # Retrieve user IP or session identifier
    session_key = getattr(request, "client", None)
    client_ip = session_key.host if session_key else "default_user"
    
    # Get or create a session for this specific client thread
    if client_ip not in sessions:
        session = session_service.create_session_sync(user_id=client_ip, app_name="disaster-relief")
        sessions[client_ip] = session.id
    
    session_id = sessions[client_ip]
    
    # Construct the user message
    new_message = types.Content(
        role="user", parts=[types.Part.from_text(text=message)]
    )
    
    # Run the agent workflow and stream results
    try:
        events = runner.run(
            new_message=new_message,
            user_id=client_ip,
            session_id=session_id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
        
        full_response = ""
        node_outputs = {}
        
        for event in events:
            # Check for error nodes/crashes
            if getattr(event, "error_code", None) or getattr(event, "error_message", None):
                err_msg = event.error_message or ""
                # Rate limit or server load hint
                if any(code in err_msg for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                    full_response = (
                        "⚠️ **Gemini API Service Temporarily Unavailable (503/429) or High Demand.**\n\n"
                        "The AI servers are currently experiencing heavy traffic. "
                        "Please wait about 30 seconds and try sending your request again."
                    )
                else:
                    full_response = f"❌ **Error occurred:** {event.error_code}\n\n{err_msg}"
                yield full_response
                return
            # Skip streaming the internal classifier's output JSON to the UI
            if event.node_info and event.node_info.path and "classifier_agent" in event.node_info.path:
                continue
                
            if event.content and event.content.parts:
                node_path = event.node_info.path if event.node_info else "unknown"
                text = "".join(p.text for p in event.content.parts if p.text)
                if text:
                    is_partial = getattr(event, "partial", True)
                    if is_partial:
                        # Accumulate delta text for this node
                        node_outputs[node_path] = node_outputs.get(node_path, "") + text
                    else:
                        # Final aggregated content replaces the delta buffer
                        node_outputs[node_path] = text
                    
                    # Reconstruct the response without duplication
                    full_response = "".join(
                        val for path, val in node_outputs.items()
                        if "classifier_agent" not in path
                    )
                    yield full_response
                    
        # Fallback if no text event was yielded
        if not node_outputs:
            yield "The request was processed, but no content was returned. Please try rephrasing your prompt."
            
    except Exception as e:
        err_str = str(e)
        if any(code in err_str for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
            yield (
                "⚠️ **Gemini API Service Temporarily Unavailable (503/429) or High Demand.**\n\n"
                "The AI servers are currently experiencing heavy traffic. "
                "Please wait about 30 seconds and try sending your request again."
            )
        else:
            yield f"⚠️ **System Error:** {err_str}"


# Premium layout using Gradio blocks
theme = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="slate",
    neutral_hue="gray",
    font=[gr.themes.GoogleFont("Outfit"), "sans-serif"]
)

with gr.Blocks(title="Kerala Emergency Relief Portal") as demo:
    gr.HTML(
        """
        <div style="text-align: center; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #0f766e; font-size: 2.5rem; font-weight: 800; margin-bottom: 10px;">
                🌊 Kerala Disaster Relief Portal
            </h1>
            <p style="font-size: 1.1rem; color: #4b5563;">
                An AI-powered emergency dispatcher to route disaster queries to relief shelter lookup, medical emergency services, or critical escalation channels.
            </p>
        </div>
        """
    )
    
    with gr.Row():
        with gr.Column(scale=4):
            chat = gr.ChatInterface(
                fn=respond,
                textbox=gr.Textbox(
                    placeholder="Describe your situation (e.g. 'My house in Wayanad is flooded' or 'I need shelter')",
                    container=False,
                    scale=7
                ),
                examples=[
                    ["My house is flooded. I need a safe place to stay tonight."],
                    ["Where is the nearest relief camp in Wayanad?"],
                    ["I am pregnant and the roads in Idukki are blocked due to landslides!"],
                    ["My grandmother in Alappuzha needs an emergency hospital refilling insulin refills."]
                ],
                cache_examples=False,
            )
            
        with gr.Column(scale=1):
            gr.Markdown(
                """
                ### 📢 Emergency Directives
                - **Primary Helplines**:
                  - Police: **100**
                  - Fire Force: **101**
                  - Disaster Management: **1078**
                  - State Control Room: **+91-471-2364424**
                  
                ### 🚨 Critical Vulnerability
                System automatically escalates to emergency rescue for:
                - Pregnant individuals
                - Families with infants
                - Disabled or elderly citizens
                - Critical medical distress (chest pain, unconsciousness)
                - Blocked evacuation routes
                """
            )

if __name__ == "__main__":
    # Auto-build RAG index on startup if missing
    try:
        from app.rag_pipeline import build_index, INDEX_PATH
        if not os.path.exists(INDEX_PATH):
            print("🚀 RAG index not found. Building index from local documents...")
            status = build_index()
            print(f"Index build status: {status}")
    except Exception as e:
        print(f"Error building RAG index on startup: {e}")

    demo.queue()
    # Run server locally on 0.0.0.0, using GRADIO_SERVER_PORT environment variable if set
    port = int(os.getenv("GRADIO_SERVER_PORT", 8080))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=theme)
