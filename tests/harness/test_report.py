"""
Test Report Generator Module.

This module generates professional test reports following the format:
- Test prompt
- Expected behavior
- Actual behavior
- Pass/Fail assessment
- Specific bugs, weaknesses, or unverifiable assumptions
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import json


class TestResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class TestIssue:
    """A specific issue found during testing."""
    severity: IssueSeverity
    category: str  # e.g., "Schema Validation", "Aggregation", "Conflict Resolution"
    description: str
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    
    def __str__(self) -> str:
        result = f"[{self.severity.value}] {self.category}: {self.description}"
        if self.evidence:
            result += f"\n   Evidence: {self.evidence}"
        if self.recommendation:
            result += f"\n   Recommendation: {self.recommendation}"
        return result


@dataclass
class TestAssertion:
    """A single assertion within a test."""
    description: str
    expected: Any
    actual: Any
    passed: bool
    error_message: Optional[str] = None
    
    def __str__(self) -> str:
        status = "✓" if self.passed else "✗"
        result = f"{status} {self.description}"
        if not self.passed:
            result += f"\n   Expected: {self.expected}"
            result += f"\n   Actual: {self.actual}"
            if self.error_message:
                result += f"\n   Error: {self.error_message}"
        return result


@dataclass
class TestCase:
    """A complete test case with prompt, expectations, and results."""
    name: str
    description: str
    test_prompt: Dict[str, Any]
    expected_behavior: List[str]
    actual_behavior: List[str] = field(default_factory=list)
    result: TestResult = TestResult.INCONCLUSIVE
    assertions: List[TestAssertion] = field(default_factory=list)
    issues: List[TestIssue] = field(default_factory=list)
    duration_ms: Optional[float] = None
    raw_output: Optional[Dict[str, Any]] = None
    
    def add_assertion(
        self,
        description: str,
        expected: Any,
        actual: Any,
        passed: bool,
        error_message: Optional[str] = None
    ):
        """Add an assertion to this test case."""
        self.assertions.append(TestAssertion(
            description=description,
            expected=expected,
            actual=actual,
            passed=passed,
            error_message=error_message
        ))
        self.actual_behavior.append(f"{'PASS' if passed else 'FAIL'}: {description}")
    
    def add_issue(
        self,
        severity: IssueSeverity,
        category: str,
        description: str,
        evidence: Optional[str] = None,
        recommendation: Optional[str] = None
    ):
        """Add an issue found during testing."""
        self.issues.append(TestIssue(
            severity=severity,
            category=category,
            description=description,
            evidence=evidence,
            recommendation=recommendation
        ))
    
    def calculate_result(self):
        """Calculate the overall test result from assertions."""
        if not self.assertions:
            self.result = TestResult.INCONCLUSIVE
        elif all(a.passed for a in self.assertions):
            self.result = TestResult.PASS
        elif any(a.passed for a in self.assertions):
            self.result = TestResult.PARTIAL
        else:
            self.result = TestResult.FAIL
    
    def __str__(self) -> str:
        lines = [
            f"=" * 70,
            f"TEST: {self.name}",
            f"=" * 70,
            f"Description: {self.description}",
            "",
            "TEST PROMPT:",
            json.dumps(self.test_prompt, indent=2),
            "",
            "EXPECTED BEHAVIOR:",
        ]
        
        for exp in self.expected_behavior:
            lines.append(f"  - {exp}")
        
        lines.extend([
            "",
            "ASSERTIONS:",
        ])
        
        for assertion in self.assertions:
            lines.append(f"  {assertion}")
        
        lines.extend([
            "",
            f"RESULT: {self.result.value}",
        ])
        
        if self.issues:
            lines.extend([
                "",
                "ISSUES FOUND:",
            ])
            for issue in self.issues:
                lines.append(f"  {issue}")
        
        if self.duration_ms:
            lines.append(f"\nDuration: {self.duration_ms:.2f}ms")
        
        return "\n".join(lines)


@dataclass
class TestReport:
    """A complete test report containing multiple test cases."""
    title: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recommendations: List[str] = field(default_factory=list)
    unverifiable_assumptions: List[str] = field(default_factory=list)
    
    def add_test_case(self, test_case: TestCase):
        """Add a test case to the report."""
        self.test_cases.append(test_case)
    
    def add_recommendation(self, recommendation: str):
        """Add a general recommendation."""
        self.recommendations.append(recommendation)
    
    def add_unverifiable_assumption(self, assumption: str):
        """Record an assumption that cannot be verified."""
        self.unverifiable_assumptions.append(assumption)
    
    @property
    def total_tests(self) -> int:
        return len(self.test_cases)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for tc in self.test_cases if tc.result == TestResult.PASS)
    
    @property
    def failed_tests(self) -> int:
        return sum(1 for tc in self.test_cases if tc.result == TestResult.FAIL)
    
    @property
    def partial_tests(self) -> int:
        return sum(1 for tc in self.test_cases if tc.result == TestResult.PARTIAL)
    
    @property
    def all_issues(self) -> List[TestIssue]:
        issues = []
        for tc in self.test_cases:
            issues.extend(tc.issues)
        return issues
    
    @property
    def critical_issues(self) -> List[TestIssue]:
        return [i for i in self.all_issues if i.severity == IssueSeverity.CRITICAL]
    
    def __str__(self) -> str:
        lines = [
            "#" * 70,
            f"# TEST REPORT: {self.title}",
            "#" * 70,
            f"Generated: {self.created_at}",
            f"Description: {self.description}",
            "",
            "=" * 70,
            "SUMMARY",
            "=" * 70,
            f"Total Tests: {self.total_tests}",
            f"Passed: {self.passed_tests}",
            f"Failed: {self.failed_tests}",
            f"Partial: {self.partial_tests}",
            f"Critical Issues: {len(self.critical_issues)}",
            "",
        ]
        
        # Individual test cases
        for tc in self.test_cases:
            lines.append(str(tc))
            lines.append("")
        
        # Unverifiable assumptions
        if self.unverifiable_assumptions:
            lines.extend([
                "=" * 70,
                "UNVERIFIABLE ASSUMPTIONS",
                "=" * 70,
            ])
            for idx, assumption in enumerate(self.unverifiable_assumptions, 1):
                lines.append(f"{idx}. {assumption}")
            lines.append("")
        
        # Recommendations
        if self.recommendations:
            lines.extend([
                "=" * 70,
                "RECOMMENDATIONS",
                "=" * 70,
            ])
            for idx, rec in enumerate(self.recommendations, 1):
                lines.append(f"{idx}. {rec}")
        
        return "\n".join(lines)
    
    def to_markdown(self) -> str:
        """Generate a markdown version of the report."""
        lines = [
            f"# Test Report: {self.title}",
            "",
            f"**Generated:** {self.created_at}",
            "",
            f"**Description:** {self.description}",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total Tests | {self.total_tests} |",
            f"| Passed | {self.passed_tests} |",
            f"| Failed | {self.failed_tests} |",
            f"| Partial | {self.partial_tests} |",
            f"| Critical Issues | {len(self.critical_issues)} |",
            "",
        ]
        
        lines.append("## Test Cases")
        for tc in self.test_cases:
            result_emoji = {
                TestResult.PASS: "✅",
                TestResult.FAIL: "❌",
                TestResult.PARTIAL: "⚠️",
                TestResult.INCONCLUSIVE: "❓",
                TestResult.ERROR: "💥"
            }.get(tc.result, "❓")
            
            lines.extend([
                "",
                f"### {result_emoji} {tc.name}",
                "",
                f"**Description:** {tc.description}",
                "",
                "<details>",
                "<summary>Test Prompt</summary>",
                "",
                "```json",
                json.dumps(tc.test_prompt, indent=2),
                "```",
                "</details>",
                "",
                "**Expected Behavior:**",
            ])
            
            for exp in tc.expected_behavior:
                lines.append(f"- {exp}")
            
            lines.extend([
                "",
                "**Assertions:**",
                "",
                "| Status | Assertion | Expected | Actual |",
                "|--------|-----------|----------|--------|",
            ])
            
            for a in tc.assertions:
                status = "✓" if a.passed else "✗"
                lines.append(f"| {status} | {a.description} | `{a.expected}` | `{a.actual}` |")
            
            lines.extend([
                "",
                f"**Result:** `{tc.result.value}`",
            ])
            
            if tc.issues:
                lines.extend([
                    "",
                    "**Issues:**",
                ])
                for issue in tc.issues:
                    lines.append(f"- [{issue.severity.value}] {issue.category}: {issue.description}")
        
        if self.recommendations:
            lines.extend([
                "",
                "## Recommendations",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")
        
        if self.unverifiable_assumptions:
            lines.extend([
                "",
                "## Unverifiable Assumptions",
                "",
            ])
            for assumption in self.unverifiable_assumptions:
                lines.append(f"- {assumption}")
        
        return "\n".join(lines)
