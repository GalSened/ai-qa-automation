"""
QA Analyzer - Main FastAPI application
Orchestrates code analysis, LLM interaction, and test generation
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import json
import httpx
import asyncio
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="QA Analyzer", version="1.0.0")

# Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://playwright-mcp:8001")
CODE_DIR = Path("/app/code")
GENERATED_TESTS_DIR = Path("/app/generated_tests")
CONFIG_DIR = Path("/app/config")

# Ensure directories exist
GENERATED_TESTS_DIR.mkdir(exist_ok=True)

class CodeAnalysisRequest(BaseModel):
    """Request model for code analysis"""
    file_path: str
    test_type: str = "integration"  # integration, unit, e2e
    target_url: Optional[str] = "http://localhost:3000"

class TestAction(BaseModel):
    """Model for Playwright test actions"""
    action: str
    selector: Optional[str] = None
    url: Optional[str] = None
    text: Optional[str] = None
    timeout: Optional[int] = 30000

class GeneratedTest(BaseModel):
    """Model for generated test response"""
    test_name: str
    file_path: str
    actions: List[TestAction]
    test_code: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "qa-analyzer"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "QA Analyzer Service", "version": "1.0.0"}

@app.post("/analyze", response_model=GeneratedTest)
async def analyze_code(request: CodeAnalysisRequest):
    """
    Main endpoint: Analyze code and generate Playwright tests
    
    Flow:
    1. Read and analyze the code file
    2. Send to LLM for test scenario generation
    3. Convert to Playwright actions via MCP
    4. Generate PyTest + Playwright test file
    5. Save to generated_tests directory
    """
    try:
        logger.info(f"Starting analysis for: {request.file_path}")
        
        # Step 1: Read the code file
        code_content = await read_code_file(request.file_path)
        
        # Step 2: Analyze with LLM
        test_scenarios = await analyze_with_llm(code_content, request.test_type)
        
        # Step 3: Convert to Playwright actions
        actions = await generate_playwright_actions(test_scenarios, request.target_url)
        
        # Step 4: Generate test code
        test_code = generate_pytest_code(actions, request.file_path, request.test_type)
        
        # Step 5: Save generated test
        test_file_path = await save_generated_test(test_code, request.file_path)
        
        return GeneratedTest(
            test_name=f"test_{Path(request.file_path).stem}",
            file_path=str(test_file_path),
            actions=actions,
            test_code=test_code
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

async def read_code_file(file_path: str) -> str:
    """Read and return the content of a code file"""
    full_path = CODE_DIR / file_path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

async def analyze_with_llm(code_content: str, test_type: str) -> Dict[str, Any]:
    """
    Send code to Ollama LLM for analysis and test scenario generation
    """
    prompt = f"""
    SYSTEM PROMPT:
    You are a senior QA automation engineer. Your job is to generate comprehensive, executable test scenarios for the code provided. Always:
    - Assert all key functionality and user interactions
    - Check all expected outputs and status codes
    - Cover edge cases and error handling
    - Include both positive and negative tests
    - Output your response as strict JSON, no extra commentary
    - For each user interaction, output explicit, actionable steps (e.g., 'Fill the username field with \"existinguser\"', 'Fill the email field with \"invalid-email\"', 'Click the Register button').
    - For each assertion, specify the expected selector or field name and the expected error or success message (e.g., 'Assert that .error contains \"Invalid email address.\"').
    - For each edge case, describe the exact input values and expected outcome.
    
    Code to analyze:
    ```
    {code_content}
    ```
    
    Test Type: {test_type}
    
    Please provide:
    1. Key functionality that needs testing
    2. User interactions to test (as a list of objects with 'test_name' and 'steps', where each step is explicit and actionable)
    3. Expected behaviors and assertions (as a list of objects with 'test_name', 'selector', and 'expected_outcome')
    4. Edge cases to consider (as a list of objects with 'test_name', 'steps', and 'expected_outcome')
    
    Format your response as JSON with this structure:
    {{
        "functionality": ["list of key features"],
        "user_interactions": [{{"test_name": "...", "steps": ["..."]}}],
        "assertions": [{{"test_name": "...", "selector": "...", "expected_outcome": "..."}}],
        "edge_cases": [{{"test_name": "...", "steps": ["..."], "expected_outcome": "..."}}]
    }}
    """
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llama3.1:8b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 2000
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="LLM analysis failed")
            
            result = response.json()
            
            # Extract and parse the JSON from LLM response
            llm_response = result.get("response", "")
            logger.info(f"LLM Response: {llm_response}")
            
            # Try to extract JSON from the response
            try:
                import re
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    # Fallback: create basic test scenarios
                    return {
                        "functionality": ["Basic functionality test"],
                        "user_interactions": ["Page load", "User interaction"],
                        "assertions": ["Page loads successfully", "Elements are visible"],
                        "edge_cases": ["Network error", "Invalid input"]
                    }
            except json.JSONDecodeError:
                # Fallback for invalid JSON
                return {
                    "functionality": ["Basic functionality test"],
                    "user_interactions": ["Page load", "User interaction"],
                    "assertions": ["Page loads successfully", "Elements are visible"],
                    "edge_cases": ["Network error", "Invalid input"]
                }
                
    except Exception as e:
        logger.error(f"LLM communication failed: {str(e)}")
        # Return fallback scenarios
        return {
            "functionality": ["Basic functionality test"],
            "user_interactions": ["Page load", "User interaction"],
            "assertions": ["Page loads successfully", "Elements are visible"],
            "edge_cases": ["Network error", "Invalid input"]
        }

async def generate_playwright_actions(test_scenarios: Dict[str, Any], target_url: str) -> List[TestAction]:
    """
    Convert test scenarios to Playwright actions via MCP server
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/generate_actions",
                json={
                    "scenarios": test_scenarios,
                    "target_url": target_url
                }
            )
            
            if response.status_code != 200:
                logger.warning("MCP server unavailable, using fallback actions")
                return generate_fallback_actions(target_url)
            
            actions_data = response.json().get("actions", [])
            return [TestAction(**action) for action in actions_data]
            
    except Exception as e:
        logger.warning(f"MCP communication failed: {str(e)}, using fallback")
        return generate_fallback_actions(target_url)

def generate_fallback_actions(target_url: str) -> List[TestAction]:
    """Generate basic fallback Playwright actions"""
    return [
        TestAction(action="goto", url=target_url),
        TestAction(action="wait_for_load_state", timeout=30000),
        TestAction(action="assert_visible", selector="body"),
        TestAction(action="screenshot", selector="page")
    ]

def generate_pytest_code(actions: List[TestAction], original_file: str, test_type: str) -> str:
    """
    Generate complete PyTest + Playwright test code from actions
    """
    test_name = f"test_{Path(original_file).stem}_{test_type}"
    
    # Convert actions to Playwright code
    action_code = []
    for action in actions:
        if action.action == "goto":
            action_code.append(f'    await page.goto("{action.url}")')
        elif action.action == "click":
            action_code.append(f'    await page.click("{action.selector}")')
        elif action.action == "fill":
            action_code.append(f'    await page.fill("{action.selector}", "{action.text}")')
        elif action.action == "assert_visible":
            action_code.append(f'    await expect(page.locator("{action.selector}")).to_be_visible()')
        elif action.action == "assert_text":
            action_code.append(f'    await expect(page.locator("{action.selector}")).to_contain_text("{action.text}")')
        elif action.action == "wait_for_load_state":
            action_code.append(f'    await page.wait_for_load_state("networkidle")')
        elif action.action == "screenshot":
            action_code.append(f'    await page.screenshot(path="results/{test_name}.png")')
    
    actions_str = "\n".join(action_code)
    
    return f'''"""
Generated test for: {original_file}
Test type: {test_type}
Generated by QA Analyzer AI Agent
"""

import pytest
from playwright.async_api import async_playwright, expect
import asyncio


class Test{test_name.replace("test_", "").title().replace("_", "")}:
    """Test class for {original_file}"""
    
    @pytest.mark.asyncio
    async def {test_name}(self):
        """
        Main test method for {test_type} testing
        Generated from AI analysis of {original_file}
        """
        async with async_playwright() as p:
            # Launch browser (headless for CI/CD)
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            # Create new page
            page = await browser.new_page()
            
            try:
                # Execute generated actions
{actions_str}
                
                # Additional assertions
                await expect(page).to_have_title(lambda title: len(title) > 0)
                
                print(f"✅ Test {test_name} completed successfully")
                
            except Exception as e:
                # Take screenshot on failure
                await page.screenshot(path=f"results/{test_name}_failure.png")
                print(f"❌ Test {test_name} failed: {{str(e)}}")
                raise
                
            finally:
                await browser.close()


if __name__ == "__main__":
    # Run the test directly
    asyncio.run(Test{test_name.replace("test_", "").title().replace("_", "")}.{test_name}(Test{test_name.replace("test_", "").title().replace("_", "")}()))
'''

async def save_generated_test(test_code: str, original_file: str) -> Path:
    """Save generated test code to file"""
    test_filename = f"test_{Path(original_file).stem}.py"
    test_path = GENERATED_TESTS_DIR / test_filename
    
    try:
        with open(test_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info(f"Generated test saved to: {test_path}")
        return test_path
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save test: {str(e)}")

@app.get("/tests")
async def list_generated_tests():
    """List all generated test files"""
    try:
        test_files = list(GENERATED_TESTS_DIR.glob("*.py"))
        return {
            "generated_tests": [
                {
                    "name": f.name,
                    "path": str(f.relative_to(GENERATED_TESTS_DIR)),
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                }
                for f in test_files
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tests: {str(e)}")

@app.delete("/tests/{test_name}")
async def delete_test(test_name: str):
    """Delete a generated test file"""
    test_path = GENERATED_TESTS_DIR / test_name
    
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="Test file not found")
    
    try:
        test_path.unlink()
        return {"message": f"Test {test_name} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete test: {str(e)}")