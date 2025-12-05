import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys

# Ensure we can import from the current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []

@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return "<h1>Agent Server is Running</h1><p>Go to /static/index.html if you created it, or ensure it exists.</p>"

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Reconstruct history
        messages = []
        for msg in request.history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            # System messages could be handled if needed
            
        # Add new message
        messages.append(HumanMessage(content=request.message))
        
        initial_input = {
            "messages": messages,
            # Initialize other state fields if necessary
        }
        
        # Invoke graph
        # Note: In a real persistent app, we would use a thread_id and checkpointer
        # Here we pass the full history every time
        final_state = await graph.ainvoke(initial_input)
        
        # Get the last message from the agent
        output_messages = final_state.get("messages", [])
        last_message = output_messages[-1]
        
        response_text = last_message.content if last_message else "No response generated."
        
        return {
            "response": response_text,
            "status": final_state.get("status"),
            "buyer_entity": final_state.get("buyer_entity")
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Starting server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

