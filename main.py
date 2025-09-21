from fastapi import FastAPI
from agents import  Runner ,TResponseInputItem
from pydantic import BaseModel
from agent import triage_agent
from openai.types.responses import ResponseTextDeltaEvent
from fastapi.responses import StreamingResponse
import json
from typing import AsyncGenerator
from analytics import analytics_router


class chat_request(BaseModel):
    query: str

app = FastAPI()
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
history:list[TResponseInputItem]= []

        
@app.post("/chat/stream")
async def chat(request: chat_request):
    query = request.query
    history.append({"role": "user", "content": query})
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        result = Runner.run_streamed(triage_agent, input=history)
        complete_response = ""
        
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta = event.data.delta
                complete_response += delta
                
                # Format as Server-Sent Events (SSE)
                yield f"data: {json.dumps({'delta': delta, 'type': 'delta'})}\n\n"
        
        # Add the complete response to history after streaming is done
        history.append({"role": "assistant", "content": complete_response})
        
        # Send a final event to indicate completion
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


    

@app.post("/chat")
async def agent_endpoint(request: chat_request):
    query = request.query.strip()
    if not query:
        return {"error": "Query is required"}

    history.append({"role": "user", "content": query})
   
    try:
        result = await Runner.run(triage_agent, history)
        history.append({"role": "assistant", "content": result.final_output})
        return {"response": result.final_output}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message": "Welcome to the Chat API. Use the /chat endpoint to interact."}