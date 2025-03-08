from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal, Dict, Any, List


class BrowsingTask(BaseModel):
    """Request model for the browsing task."""
    url: str  # The URL to browse
    instruction: str  # Natural language instruction for what to do on the page


class BrowserActionRequest(BaseModel):
    """Request model for browser actions."""
    action_type: Literal["click", "scroll_down", "scroll_up", "screenshot", "get_html"]
    element_selector: Optional[str] = None  # For click actions
    scroll_amount: Optional[int] = None  # For scroll actions, in pixels


class ScreenshotUpdate(BaseModel):
    """Model for screenshot updates."""
    type: Literal["screenshot"] = "screenshot"
    image_data: str  # Base64 encoded image
    timestamp: float


class MessageUpdate(BaseModel):
    """Model for message updates from the agent."""
    type: Literal["message"] = "message"
    content: str
    thinking: Optional[str] = None
    timestamp: float


class ActionUpdate(BaseModel):
    """Model for action updates from the agent."""
    type: Literal["action"] = "action"
    action: str
    details: Dict[str, Any]
    timestamp: float


class StatusUpdate(BaseModel):
    """Model for status updates from the agent."""
    type: Literal["status"] = "status"
    status: str
    timestamp: float


class ErrorUpdate(BaseModel):
    """Model for error updates from the agent."""
    type: Literal["error"] = "error"
    message: str
    timestamp: float 