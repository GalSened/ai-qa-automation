"""
Playwright MCP Server
Converts AI-generated test scenarios into structured Playwright actions
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Playwright MCP Server", version="1.0.0")

class ActionRequest(BaseModel):
    """Request model for action generation"""
    scenarios: Dict[str, Any]
    target_url: str

class PlaywrightAction(BaseModel):
    """Playwright action model"""
    action: str
    selector: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    timeout: Optional[int] = 30000

class ActionResponse(BaseModel):
    """Response model for generated actions"""
    actions: List[PlaywrightAction]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "playwright-mcp"}

@app.post("/generate_actions", response_model=ActionResponse)
async def generate_actions(request: ActionRequest):
    """
    Convert test scenarios into Playwright actions
    
    This is the core MCP functionality that translates
    AI-generated scenarios into executable Playwright commands
    """
    try:
        logger.info(f"Generating actions for URL: {request.target_url}")
        
        actions = []
        
        # Start with navigation
        actions.append(PlaywrightAction(
            action="goto",
            url=request.target_url
        ))
        
        # Wait for page load
        actions.append(PlaywrightAction(
            action="wait_for_load_state",
            timeout=30000
        ))
        
        # Process functionality scenarios
        functionality = request.scenarios.get("functionality", [])
        for func in functionality[:3]:  # Limit to 3 main functions
            actions.extend(generate_functionality_actions(func))
        
        # Process user interactions
        interactions = request.scenarios.get("user_interactions", [])
        for interaction in interactions[:5]:  # Limit to 5 interactions
            actions.extend(generate_interaction_actions(interaction))
        
        # Process assertions
        assertions = request.scenarios.get("assertions", [])
        for assertion in assertions[:3]:  # Limit to 3 assertions
            actions.extend(generate_assertion_actions(assertion))
        
        # Add screenshot for evidence
        actions.append(PlaywrightAction(
            action="screenshot",
            selector="page"
        ))
        
        logger.info(f"Generated {len(actions)} Playwright actions")
        
        return ActionResponse(actions=actions)
        
    except Exception as e:
        logger.error(f"Action generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Action generation failed: {str(e)}")

def generate_functionality_actions(functionality: str) -> List[PlaywrightAction]:
    """Generate actions for functionality testing"""
    actions = []
    
    # Basic functionality patterns
    if "form" in functionality.lower() or "input" in functionality.lower():
        actions.append(PlaywrightAction(
            action="assert_visible",
            selector="form, input, textarea"
        ))
    
    if "button" in functionality.lower() or "click" in functionality.lower():
        actions.append(PlaywrightAction(
            action="assert_visible",
            selector="button, .btn, [role='button']"
        ))
    
    if "navigation" in functionality.lower() or "menu" in functionality.lower():
        actions.append(PlaywrightAction(
            action="assert_visible",
            selector="nav, .nav, .menu, header"
        ))
    
    return actions

def generate_interaction_actions(interaction: str) -> List[PlaywrightAction]:
    """Generate actions for user interactions"""
    actions = []
    
    if "click" in interaction.lower():
        actions.append(PlaywrightAction(
            action="click",
            selector="button:first-of-type, .btn:first-of-type"
        ))
    
    if "type" in interaction.lower() or "input" in interaction.lower():
        actions.append(PlaywrightAction(
            action="fill",
            selector="input:first-of-type",
            text="test input"
        ))
    
    if "submit" in interaction.lower():
        actions.append(PlaywrightAction(
            action="click",
            selector="button[type='submit'], input[type='submit']"
        ))
    
    if "load" in interaction.lower():
        actions.append(PlaywrightAction(
            action="wait_for_load_state",
            timeout=30000
        ))
    
    return actions

def generate_assertion_actions(assertion: str) -> List[PlaywrightAction]:
    """Generate actions for assertions"""
    actions = []
    
    if "visible" in assertion.lower() or "display" in assertion.lower():
        actions.append(PlaywrightAction(
            action="assert_visible",
            selector="main, .main, #main, .content"
        ))
    
    if "text" in assertion.lower() or "content" in assertion.lower():
        actions.append(PlaywrightAction(
            action="assert_text",
            selector="h1, .title, .heading",
            text="expected content"
        ))
    
    if "success" in assertion.lower():
        actions.append(PlaywrightAction(
            action="assert_visible",
            selector=".success, .alert-success, .message-success"
        ))
    
    return actions

@app.get("/action_examples")
async def get_action_examples():
    """Return examples of supported Playwright actions"""
    return {
        "supported_actions": [
            {
                "action": "goto",
                "description": "Navigate to URL",
                "example": {"action": "goto", "url": "http://localhost:3000"}
            },
            {
                "action": "click",
                "description": "Click an element",
                "example": {"action": "click", "selector": "#login-button"}
            },
            {
                "action": "fill",
                "description": "Fill input field",
                "example": {"action": "fill", "selector": "#username", "text": "testuser"}
            },
            {
                "action": "assert_visible",
                "description": "Assert element is visible",
                "example": {"action": "assert_visible", "selector": ".welcome-message"}
            },
            {
                "action": "assert_text",
                "description": "Assert element contains text",
                "example": {"action": "assert_text", "selector": ".welcome", "text": "Hello"}
            },
            {
                "action": "wait_for_load_state",
                "description": "Wait for page load",
                "example": {"action": "wait_for_load_state", "timeout": 30000}
            },
            {
                "action": "screenshot",
                "description": "Take screenshot",
                "example": {"action": "screenshot", "selector": "page"}
            }
        ]
    }