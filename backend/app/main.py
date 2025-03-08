from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import time
from dotenv import load_dotenv
import asyncio
import logging
from .browser_agent import BrowserAgent
from .models import BrowsingTask

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Web Browsing Agent")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections and their browser agents
active_connections = {}

@app.get("/")
async def read_root():
    return {"status": "AI Web Browsing Agent API is running"}

@app.get("/ping")
async def ping():
    return {"status": "pong", "timestamp": time.time()}

@app.get("/connections")
async def get_connections():
    """Return information about active connections for debugging purposes."""
    return {
        "active_connections": len(active_connections),
        "connection_ids": list(active_connections.keys())
    }

@app.websocket("/ws/browser")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = id(websocket)
    browser_agent = None
    
    try:
        # Check if we have too many connections
        if len(active_connections) >= 10:  # Arbitrary limit to prevent resource exhaustion
            logger.warning(f"Too many connections ({len(active_connections)}), rejecting new connection")
            await websocket.close(code=1013, reason="Too many connections")
            return
        
        # Add connection to active connections
        browser_agent = BrowserAgent()
        active_connections[connection_id] = {
            "websocket": websocket,
            "browser_agent": browser_agent,
            "last_activity": time.time()
        }
        
        logger.info(f"WebSocket connection established (id: {connection_id})")
        logger.info(f"Total active connections: {len(active_connections)}")
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "status",
            "status": "Connected",
            "timestamp": time.time()
        })
        
        while True:
            # Add a small timeout to prevent CPU spinning
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                # Send a ping to keep the connection alive
                await websocket.send_json({
                    "type": "ping", 
                    "timestamp": time.time()
                })
                continue
                
            active_connections[connection_id]["last_activity"] = time.time()
            logger.info(f"Received message of size: {len(data)} bytes")
            
            try:
                task_data = json.loads(data)
                task = BrowsingTask(**task_data)
            except Exception as e:
                logger.error(f"Invalid task data: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Invalid task data: {str(e)}",
                    "timestamp": time.time()
                })
                continue
            
            logger.info(f"Starting browsing task for URL: {task.url}")
            
            # Handle the browsing session
            async for update in browser_agent.execute_task(task.url, task.instruction):
                try:
                    # Log the size of each message type we're sending
                    if update["type"] == "screenshot":
                        logger.info(f"Sending screenshot update to client, size: {len(update['image_data'])} bytes")
                    else:
                        logger.info(f"Sending {update['type']} update to client")
                    
                    # Use a timeout to prevent hanging on send
                    send_task = asyncio.create_task(websocket.send_json(update))
                    await asyncio.wait_for(send_task, timeout=5.0)
                    
                    # Small delay to prevent overwhelming the client
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error sending update to client: {str(e)}")
                    
            logger.info("Browsing task completed")
            active_connections[connection_id]["last_activity"] = time.time()
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally (id: {connection_id})")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        try:
            error_message = {"type": "error", "message": str(e), "timestamp": time.time()}
            await websocket.send_json(error_message)
        except:
            logger.error("Failed to send error message to client")
    finally:
        # Clean up connection resources
        if connection_id in active_connections:
            del active_connections[connection_id]
            logger.info(f"Removed connection from active connections (id: {connection_id})")
            logger.info(f"Remaining active connections: {len(active_connections)}")
        
        # Clean up browser agent resources
        if browser_agent:
            logger.info("Cleaning up browser agent resources")
            try:
                await browser_agent.close()
                logger.info("Browser agent resources cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up browser agent: {str(e)}")

# Background task to clean up inactive connections
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_inactive_connections())

async def cleanup_inactive_connections():
    while True:
        try:
            current_time = time.time()
            connection_ids = list(active_connections.keys())
            
            for connection_id in connection_ids:
                connection = active_connections.get(connection_id)
                if not connection:
                    continue
                    
                # Close connections inactive for more than 10 minutes
                if current_time - connection["last_activity"] > 600:
                    logger.info(f"Closing inactive connection (id: {connection_id})")
                    try:
                        await connection["websocket"].close(code=1000, reason="Inactive connection")
                    except:
                        pass
                        
                    if connection_id in active_connections:
                        try:
                            await connection["browser_agent"].close()
                        except:
                            pass
                            
                        del active_connections[connection_id]
            
            # Log active connection count once per minute
            logger.info(f"Active connections: {len(active_connections)}")
            
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            
        await asyncio.sleep(60)  # Run cleanup every minute 