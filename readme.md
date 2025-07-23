# AI Agent Test Automation System

A production-grade, fully local AI-powered test automation system using Playwright, PyTest, and Llama 3.

## Architecture

The system consists of 4 containerized services:

1. **Ollama** - Local LLM (Llama 3) for AI reasoning
2. **QA Analyzer** - FastAPI service that orchestrates code analysis and test generation
3. **Playwright MCP** - Converts AI scenarios into Playwright actions
4. **QA Runner** - Executes generated tests and produces reports

## Quick Start

### 1. Build and Start System

```bash
docker-compose up --build
```

Wait for Ollama to download Llama 3 model (first run only).

### 2. Add Code for Analysis

Place your source code files in the `code/` directory:

```bash
# Example: Add a React component
cp my-app/src/LoginForm.jsx code/
```

### 3. Generate Tests

Call the QA Analyzer API:

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "LoginForm.jsx",
    "test_type": "integration",
    "target_url": "http://localhost:3000"
  }'
```

### 4. Run Generated Tests

Execute tests in the QA Runner:

```bash
docker exec -it qa-runner python run_tests.py
```

### 5. View Results

Check test results:

- JSON results: `test_results/test_results.json`
- HTML reports: `test_results/*.html`
- Screenshots: `test_results/*.png`

## API Endpoints

### QA Analyzer (Port 8000)

- `POST /analyze` - Analyze code and generate tests
- `GET /tests` - List generated test files
- `DELETE /tests/{name}` - Delete a test file
- `GET /health` - Health check

### Playwright MCP (Port 8001)

- `POST /generate_actions` - Convert scenarios to Playwright actions
- `GET /action_examples` - List supported actions
- `GET /health` - Health check

## Example Generated Actions

The system generates structured Playwright actions like:

```json
[
  {"action": "goto", "url": "http://localhost:3000"},
  {"action": "click", "selector": "#login"},
  {"action": "fill", "selector": "#username", "text": "testuser"},
  {"action": "assert_text", "selector": ".welcome", "text": "Hello"}
]
```

## Directory Structure

```
├── docker-compose.yml          # Main orchestration
├── qa-analyzer/               # AI code analysis service
├── playwright-mcp/            # Playwright action generation
├── qa-runner/                 # Test execution service  
├── code/                      # Source code for analysis
├── generated_tests/           # AI-generated test files
├── test_results/              # Test execution results
└── config/                    # Configuration files
```

## Hardware Requirements

- Apple Silicon Mac (M1/M2/M3) with 16GB+ RAM
- Docker Desktop for Mac
- ~10GB free disk space for models and containers

## Troubleshooting

### Ollama Model Download

If Llama 3 download fails:

```bash
docker exec -it ollama ollama pull llama3.1:8b
```

### Test Execution Issues

Check QA Runner logs:

```bash
docker logs qa-runner
```

### Port Conflicts

Change ports in docker-compose.yml if 8000/8001 are in use.

## License

MIT License - See LICENSE file for details.



ai-qa-automation/
├── docker-compose.yml
├── qa-analyzer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── playwright-mcp/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── mcp_server.py
├── qa-runner/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run_tests.py
├── src/App.tsx
├── package.json
└── other files...



```

```
