"""
QA Runner - Test execution service
Executes generated Playwright + PyTest tests and generates reports
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TESTS_DIR = Path("/app/tests")
RESULTS_DIR = Path("/app/results")
TARGET_APP_DIR = Path("/app/target_app")

# Ensure directories exist
RESULTS_DIR.mkdir(exist_ok=True)

class TestFileHandler(FileSystemEventHandler):
    def __init__(self, runner):
        self.runner = runner

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.py'):
            logger.info(f"New test file detected: {event.src_path}")
            self.runner.run_single_test(Path(event.src_path))

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.py'):
            logger.info(f"Test file modified: {event.src_path}")
            self.runner.run_single_test(Path(event.src_path))

class QATestRunner:
    """Main test runner class"""
    
    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "execution_time": 0,
            "test_results": []
        }
    
    def run_single_test(self, test_file: Path) -> Dict[str, Any]:
        """Run a single test file and return results"""
        logger.info(f"Running test: {test_file.name}")
        
        start_time = time.time()
        
        # Prepare pytest command
        cmd = [
            "python", "-m", "pytest",
            str(test_file),
            "-v",  # Verbose output
            "--tb=short",  # Short traceback format
            f"--html={RESULTS_DIR}/{test_file.stem}_report.html",
            "--self-contained-html",  # Embed CSS/JS in HTML report
            "--capture=no",  # Don't capture stdout
            "-s"  # Don't capture stdout (alternative)
        ]
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                cwd="/app",
                capture_output=True,
                text=True,
                timeout=300  # 5-minute timeout per test
            )
            
            execution_time = time.time() - start_time
            
            # Parse results
            test_result = {
                "test_file": test_file.name,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "status": "passed" if result.returncode == 0 else "failed"
            }
            
            # Extract test counts from pytest output
            stdout_lines = result.stdout.split('\n')
            for line in stdout_lines:
                if 'passed' in line or 'failed' in line:
                    test_result["pytest_summary"] = line.strip()
                    break
            
            logger.info(f"Test {test_file.name} completed with status: {test_result['status']}")
            self.results["test_results"].append(test_result)
            if test_result["status"] == "passed":
                self.results["passed"] += 1
            elif test_result["status"] == "failed":
                self.results["failed"] += 1
            else:
                self.results["skipped"] += 1
            self.results["total_tests"] += 1
            self.save_results()
            
            return test_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test {test_file.name} timed out after 5 minutes")
            return {
                "test_file": test_file.name,
                "execution_time": 300,
                "return_code": -1,
                "status": "timeout",
                "error": "Test execution timed out"
            }
        except Exception as e:
            logger.error(f"Error running test {test_file.name}: {str(e)}")
            return {
                "test_file": test_file.name,
                "execution_time": time.time() - start_time,
                "return_code": -1,
                "status": "error",
                "error": str(e)
            }
    
    def save_results(self):
        """Save test results to JSON file"""
        results_file = RESULTS_DIR / "test_results.json"
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            logger.info(f"Test results saved to: {results_file}")
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
    
    def print_summary(self):
        """Print test execution summary"""
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Skipped: {self.results['skipped']}")
        print(f"Execution Time: {self.results['execution_time']:.2f} seconds")
        print("="*60)
        
        # Print individual test results
        for test_result in self.results["test_results"]:
            status_emoji = "✅" if test_result["status"] == "passed" else "❌" if test_result["status"] == "failed" else "⚠️"
            print(f"{status_emoji} {test_result['test_file']} - {test_result['status'].upper()} ({test_result['execution_time']:.2f}s)")
        
        print("="*60)
        
        # Show where results are saved
        print(f"📊 Detailed results saved to: {RESULTS_DIR}")
        print(f"📈 HTML reports available in: {RESULTS_DIR}")

def main():
    """Main execution function"""
    logger.info("QA Runner with file watcher starting...")
    
    # Check if tests directory exists
    if not TESTS_DIR.exists():
        logger.error(f"Tests directory not found: {TESTS_DIR}")
        logger.info("Make sure tests are generated by the QA Analyzer first")
        sys.exit(1)
    
    # Initialize and run tests
    runner = QATestRunner()
    event_handler = TestFileHandler(runner)
    observer = Observer()
    observer.schedule(event_handler, str(TESTS_DIR), recursive=False)
    observer.start()
    logger.info(f"Watching for new/modified test files in {TESTS_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()