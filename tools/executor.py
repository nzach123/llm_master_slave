"""
Command executor for running tests and other subprocess operations.

Provides safe subprocess execution with timeout and output capture.
"""

import subprocess
import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Represents the result of a command execution."""
    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        timed_out: bool = False
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out
        self.success = exit_code == 0 and not timed_out
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for context injection."""
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
            "success": self.success
        }
    
    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"ExecutionResult({status}, exit_code={self.exit_code})"


def run_command(
    command: List[str],
    timeout: int = 300,
    cwd: Optional[str] = None
) -> ExecutionResult:
    """
    Run a command with timeout and capture output.
    
    Args:
        command: Command and arguments as list (e.g., ["pytest", "-v"])
        timeout: Timeout in seconds (default: 300)
        cwd: Working directory (default: current directory)
        
    Returns:
        ExecutionResult object with output and status
    """
    logger.info(f"Executing command: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            # Capture both stdout and stderr
            # shell=False for security
        )
        
        logger.info(f"Command completed with exit code: {result.returncode}")
        
        return ExecutionResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timed_out=False
        )
        
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds")
        return ExecutionResult(
            exit_code=-1,
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "",
            timed_out=True
        )
    except Exception as e:
        logger.error(f"Command execution failed: {str(e)}")
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr=str(e),
            timed_out=False
        )


def run_pytest(
    test_path: Optional[str] = None,
    verbose: bool = False,
    timeout: int = 180,
    junit_xml: str = "test_report.xml"
) -> ExecutionResult:
    """
    Run pytest with structured XML output.
    
    Args:
        test_path: Specific test file or directory (default: all tests)
        verbose: Enable verbose mode (default: False for minimal output)
        timeout: Timeout in seconds (default: 180)
        junit_xml: Path to save the JUnit XML report
        
    Returns:
        ExecutionResult with test output
    """
    # Clean up old report if exists
    if os.path.exists(junit_xml):
        try:
            os.remove(junit_xml)
        except OSError:
            pass

    # Build pytest command using sys.executable to ensure it runs in the same venv
    import sys
    # Default: match all tests except e2e/integration tests which might require external deps or keys
    command = [sys.executable, "-m", "pytest", "-k", "not e2e", "--tb=short", "-q", f"--junitxml={junit_xml}"]
    
    if verbose:
        command.append("-v")
    
    if test_path:
        command.append(test_path)
    
    logger.info(f"Running pytest (report={junit_xml})...")
    result = run_command(command, timeout=timeout)
    
    if result.success:
        logger.info("All tests passed")
    else:
        logger.warning(f"Tests failed with exit code {result.exit_code}")
    
    return result


def parse_pytest_output(output: str, xml_path: str = "test_report.xml") -> Dict[str, Any]:
    """
    Parse pytest output, prioritizing XML report for structured failure details.
    
    Args:
        output: stdout from pytest (fallback)
        xml_path: path to the JUnit XML report
        
    Returns:
        Dict with parsed test results
    """

    if os.path.exists(xml_path):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            summary = {
                "passed": int(root.get("tests", 0)) - int(root.get("failures", 0)) - int(root.get("errors", 0)),
                "failed": int(root.get("failures", 0)),
                "errors": int(root.get("errors", 0)),
                "total": int(root.get("tests", 0))
            }

            failed_tests = []
            for testcase in root.findall(".//testcase"):
                # check for failure or error
                failure = testcase.find("failure")
                error = testcase.find("error")

                if failure is not None or error is not None:
                    name = testcase.get("name")
                    classname = testcase.get("classname")
                    msg = failure.get("message") if failure is not None else error.get("message")
                    # Limit message length
                    if msg and len(msg) > 500:
                        msg = msg[:500] + "..."

                    failed_tests.append(f"FAILED {classname}::{name} - {msg}")

            return {
                "summary": summary,
                "failed_tests": failed_tests
            }

        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML report: {e}. Falling back to stdout parsing.")

    # Fallback to stdout parsing if XML missing or broken
    lines = output.strip().split('\n')
    
    summary = {"passed": 0, "failed": 0, "errors": 0, "total": 0}
    failed_tests = []
    
    for line in lines:
        if " passed" in line or " failed" in line:
            if "passed" in line:
                try:
                    summary["passed"] = int(line.split()[0])
                except (ValueError, IndexError):
                    pass
            if "failed" in line:
                try:
                    summary["failed"] = int(line.split()[0])
                except (ValueError, IndexError):
                    pass
        
        if line.startswith("FAILED"):
            failed_tests.append(line)
    
    summary["total"] = summary["passed"] + summary["failed"]
    
    return {
        "summary": summary,
        "failed_tests": failed_tests
    }


if __name__ == "__main__":
    # Test the executor
    result = run_pytest()
    print(result)
    print(parse_pytest_output(result.stdout))
