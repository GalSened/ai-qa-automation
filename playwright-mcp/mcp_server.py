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

def normalize_step(step):
    """Recursively normalize a step to a string for matching, or return None if not possible."""
    if isinstance(step, str):
        return step.lower()
    elif isinstance(step, dict):
        # Try to extract a description, test_name, or step text
        for key in ("description", "test_name", "expected_outcome", "step", "text"):
            if key in step:
                return str(step[key]).lower()
        # If dict has 'steps', flatten and join
        if "steps" in step and isinstance(step["steps"], list):
            return " ".join([normalize_step(s) or "" for s in step["steps"]]).strip().lower()
    elif isinstance(step, list):
        return " ".join([normalize_step(s) or "" for s in step]).strip().lower()
    return None


def flatten_steps(steps):
    """Flatten a list of steps, recursively extracting all strings and dicts with step-like content."""
    flat = []
    if isinstance(steps, str):
        flat.append(steps)
    elif isinstance(steps, dict):
        for key in ("description", "test_name", "expected_outcome", "step", "text"):
            if key in steps:
                flat.append(steps[key])
        if "steps" in steps and isinstance(steps["steps"], list):
            flat.extend(flatten_steps(steps["steps"]))
    elif isinstance(steps, list):
        for s in steps:
            flat.extend(flatten_steps(s))
    return flat


def safe_lower(val):
    if isinstance(val, str):
        return val.lower()
    return str(val).lower() if val is not None else ""

# Patch all scenario processing functions for type safety and logging

def generate_functionality_actions(functionality) -> list:
    actions = []
    try:
        if isinstance(functionality, (list, tuple)):
            for item in functionality:
                actions.extend(generate_functionality_actions(item))
            return actions
        if isinstance(functionality, dict):
            desc = functionality.get("description") or functionality.get("test_name") or str(functionality)
            return generate_functionality_actions(desc)
        if isinstance(functionality, str):
            func_lower = safe_lower(functionality)
            if "form" in func_lower or "input" in func_lower:
                actions.append(PlaywrightAction(
                    action="assert_visible",
                    selector="form, input, textarea"
                ))
            if "button" in func_lower or "click" in func_lower:
                actions.append(PlaywrightAction(
                    action="assert_visible",
                    selector="button, .btn, [role='button']"
                ))
            if "navigation" in func_lower or "menu" in func_lower:
                actions.append(PlaywrightAction(
                    action="assert_visible",
                    selector="nav, .nav, .menu, header"
                ))
        return actions
    except Exception as e:
        logger.error(f"Error in generate_functionality_actions: {e} | input: {functionality}")
        return []


def parse_field_and_value(step):
    """Extract field and value from a step string."""
    import re
    # Username
    if "username" in step:
        match = re.search(r"'(.*?)'", step)
        value = match.group(1) if match else "testuser"
        return ("#username, input#username, input[name='username']", value)
    # Email
    if "email" in step:
        match = re.search(r"'(.*?)'", step)
        value = match.group(1) if match else "user@example.com"
        return ("#email, input#email, input[name='email']", value)
    # Password
    if "password" in step and "confirm" not in step:
        match = re.search(r"'(.*?)'", step)
        value = match.group(1) if match else "P@ssw0rd"
        return ("#password, input#password, input[name='password']", value)
    # Confirm Password
    if "confirm password" in step:
        match = re.search(r"'(.*?)'", step)
        value = match.group(1) if match else "P@ssw0rd"
        return ("#confirmPassword, input#confirmPassword, input[name='confirmPassword']", value)
    return (None, None)


def generate_interaction_actions(interaction) -> list:
    actions = []
    try:
        if isinstance(interaction, (list, tuple)):
            for item in interaction:
                actions.extend(generate_interaction_actions(item))
            return actions
        if isinstance(interaction, dict):
            if "steps" in interaction and isinstance(interaction["steps"], list):
                for step in interaction["steps"]:
                    actions.extend(generate_interaction_actions(step))
            else:
                desc = interaction.get("description") or interaction.get("test_name") or str(interaction)
                actions.extend(generate_interaction_actions(desc))
            return actions
        if isinstance(interaction, str):
            step_lower = safe_lower(interaction)
            # Field filling
            for field in ["username", "email", "password", "confirm password"]:
                if field in step_lower and any(word in step_lower for word in ["enter", "type", "input", "provide", "set"]):
                    selector, value = parse_field_and_value(interaction)
                    if selector:
                        actions.append(PlaywrightAction(
                            action="fill",
                            selector=selector,
                            text=value
                        ))
            # Submit/click
            if any(word in step_lower for word in ["submit", "click"]):
                actions.append(PlaywrightAction(
                    action="click",
                    selector="button[type='submit'], input[type='submit'], button, .btn, [role='button']"
                ))
            # Clear fields
            if "clear" in step_lower:
                for sel in ["#username, input#username, input[name='username']", "#email, input#email, input[name='email']", "#password, input#password, input[name='password']", "#confirmPassword, input#confirmPassword, input[name='confirmPassword']"]:
                    actions.append(PlaywrightAction(
                        action="fill",
                        selector=sel,
                        text=""
                    ))
            # Wait for load
            if "load" in step_lower:
                actions.append(PlaywrightAction(
                    action="wait_for_load_state",
                    timeout=30000
                ))
        return actions
    except Exception as e:
        logger.error(f"Error in generate_interaction_actions: {e} | input: {interaction}")
        return []


def generate_assertion_actions(assertion) -> list:
    actions = []
    try:
        if isinstance(assertion, (list, tuple)):
            for item in assertion:
                actions.extend(generate_assertion_actions(item))
            return actions
        if isinstance(assertion, dict):
            for key in ("expected_outcome", "description", "test_name"):
                if key in assertion:
                    actions.extend(generate_assertion_actions(assertion[key]))
            return actions
        if isinstance(assertion, str):
            assertion_lower = safe_lower(assertion)
            # Error messages
            import re
            error_match = re.search(r"'(.*?)'", assertion)
            if "error" in assertion_lower or "invalid" in assertion_lower or "not match" in assertion_lower or "already taken" in assertion_lower:
                msg = error_match.group(1) if error_match else "Error"
                actions.append(PlaywrightAction(
                    action="assert_text",
                    selector=".error, [role='alert']",
                    text=msg
                ))
            # Success messages
            if "success" in assertion_lower:
                msg = error_match.group(1) if error_match else "Registration successful!"
                actions.append(PlaywrightAction(
                    action="assert_text",
                    selector=".success, [role='status']",
                    text=msg
                ))
            # Cleared fields
            if "cleared" in assertion_lower or "empty" in assertion_lower:
                for sel in ["#username, input#username, input[name='username']", "#email, input#email, input[name='email']", "#password, input#password, input[name='password']", "#confirmPassword, input#confirmPassword, input[name='confirmPassword']"]:
                    actions.append(PlaywrightAction(
                        action="assert_text",
                        selector=sel,
                        text=""
                    ))
            # Generic visible/content assertions
            if "visible" in assertion_lower or "display" in assertion_lower:
                actions.append(PlaywrightAction(
                    action="assert_visible",
                    selector="main, .main, #main, .content"
                ))
            if "text" in assertion_lower or "content" in assertion_lower:
                actions.append(PlaywrightAction(
                    action="assert_text",
                    selector="h1, .title, .heading",
                    text="expected content"
                ))
        return actions
    except Exception as e:
        logger.error(f"Error in generate_assertion_actions: {e} | input: {assertion}")
        return []


def generate_edge_case_actions(edge_case) -> list:
    actions = []
    try:
        if isinstance(edge_case, (list, tuple)):
            for item in edge_case:
                actions.extend(generate_edge_case_actions(item))
            return actions
        if isinstance(edge_case, dict):
            for key in ("description", "test_name"):
                if key in edge_case:
                    actions.extend(generate_edge_case_actions(edge_case[key]))
            return actions
        if isinstance(edge_case, str):
            edge_case_lower = safe_lower(edge_case)
            actions.extend(generate_functionality_actions(edge_case))
        return actions
    except Exception as e:
        logger.error(f"Error in generate_edge_case_actions: {e} | input: {edge_case}")
        return []

def extract_all_steps(obj):
    """Recursively extract all step strings from any nested structure."""
    steps = []
    if isinstance(obj, str):
        steps.append(obj)
    elif isinstance(obj, dict):
        # If this dict has a 'steps' key, process it
        if 'steps' in obj and isinstance(obj['steps'], list):
            for s in obj['steps']:
                steps.extend(extract_all_steps(s))
        else:
            # Otherwise, process all values
            for v in obj.values():
                steps.extend(extract_all_steps(v))
    elif isinstance(obj, list):
        for item in obj:
            steps.extend(extract_all_steps(item))
    return steps

# Patch generate_actions to use extract_all_steps for user_interactions and edge_cases
@app.post("/generate_actions", response_model=ActionResponse)
async def generate_actions(request: ActionRequest):
    try:
        logger.info(f"Generating actions for URL: {request.target_url}")
        actions = []
        actions.append(PlaywrightAction(
            action="goto",
            url=request.target_url
        ))
        actions.append(PlaywrightAction(
            action="wait_for_load_state",
            timeout=30000
        ))
        # Process functionality scenarios
        functionality = request.scenarios.get("functionality", [])
        for func in functionality:
            actions.extend(generate_functionality_actions(func))
        # Process user interactions (recursively extract all steps)
        interactions = request.scenarios.get("user_interactions", [])
        for step in extract_all_steps(interactions):
            actions.extend(generate_interaction_actions(step))
        # Process assertions
        assertions = request.scenarios.get("assertions", [])
        for assertion in assertions:
            actions.extend(generate_assertion_actions(assertion))
        # Process edge cases (recursively extract all steps)
        edge_cases = request.scenarios.get("edge_cases", [])
        for step in extract_all_steps(edge_cases):
            actions.extend(generate_interaction_actions(step))
        actions.append(PlaywrightAction(
            action="screenshot",
            selector="page"
        ))
        logger.info(f"Generated {len(actions)} Playwright actions")
        return ActionResponse(actions=actions)
    except Exception as e:
        logger.error(f"Action generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Action generation failed: {str(e)}")

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