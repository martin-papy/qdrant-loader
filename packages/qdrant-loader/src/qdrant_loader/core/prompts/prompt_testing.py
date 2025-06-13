"""Prompt testing and evaluation system for entity extraction.

This module provides tools for testing, evaluating, and iterating on entity
extraction prompts to ensure high accuracy and consistency.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..entity_extractor import EntityExtractor, EntityType, ExtractedEntity
from .entity_prompts import EntityPromptManager, PromptDomain, PromptTemplate
from ...utils.logging import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class TestResultStatus(Enum):
    """Status of a prompt test result."""

    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class PromptTestCase:
    """Test case for prompt evaluation."""

    name: str
    input_text: str
    expected_entities: List[Dict[str, Any]]
    domain: PromptDomain = PromptDomain.SOFTWARE_DEVELOPMENT
    custom_prompt: str = ""
    extraction_hints: Dict[str, List[str]] = field(default_factory=dict)
    confidence_threshold: float = 0.5
    description: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary."""
        return {
            "name": self.name,
            "input_text": self.input_text,
            "expected_entities": self.expected_entities,
            "domain": self.domain.value,
            "custom_prompt": self.custom_prompt,
            "extraction_hints": self.extraction_hints,
            "confidence_threshold": self.confidence_threshold,
            "description": self.description,
            "tags": self.tags,
        }


@dataclass
class PromptTestResult:
    """Result of a prompt test execution."""

    test_case: PromptTestCase
    extracted_entities: List[ExtractedEntity]
    status: TestResultStatus
    accuracy_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    missing_entities: List[Dict[str, Any]] = field(default_factory=list)
    unexpected_entities: List[ExtractedEntity] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert test result to dictionary."""
        return {
            "test_case": self.test_case.to_dict(),
            "extracted_entities": [
                {
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "confidence": entity.confidence,
                }
                for entity in self.extracted_entities
            ],
            "status": self.status.value,
            "accuracy_score": self.accuracy_score,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "execution_time": self.execution_time,
            "errors": self.errors,
            "missing_entities": self.missing_entities,
            "unexpected_entities": [
                {
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "confidence": entity.confidence,
                }
                for entity in self.unexpected_entities
            ],
            "timestamp": self.timestamp.isoformat(),
        }


class PromptTester:
    """System for testing and evaluating entity extraction prompts."""

    def __init__(
        self, entity_extractor: EntityExtractor, prompt_manager: EntityPromptManager
    ):
        """Initialize the prompt tester.

        Args:
            entity_extractor: EntityExtractor instance for testing
            prompt_manager: EntityPromptManager for prompt access
        """
        self.entity_extractor = entity_extractor
        self.prompt_manager = prompt_manager
        self._test_cases: Dict[str, PromptTestCase] = {}
        self._test_results: List[PromptTestResult] = []

        logger.info("PromptTester initialized")

    def add_test_case(self, test_case: PromptTestCase) -> None:
        """Add a test case to the test suite."""
        self._test_cases[test_case.name] = test_case
        logger.debug(f"Added test case: {test_case.name}")

    def load_test_cases_from_dict(self, test_cases_data: List[Dict[str, Any]]) -> None:
        """Load test cases from dictionary data."""
        for case_data in test_cases_data:
            test_case = PromptTestCase(
                name=case_data["name"],
                input_text=case_data["input_text"],
                expected_entities=case_data["expected_entities"],
                domain=PromptDomain(case_data.get("domain", "software_development")),
                custom_prompt=case_data.get("custom_prompt", ""),
                extraction_hints=case_data.get("extraction_hints", {}),
                confidence_threshold=case_data.get("confidence_threshold", 0.5),
                description=case_data.get("description", ""),
                tags=case_data.get("tags", []),
            )
            self.add_test_case(test_case)

        logger.info(f"Loaded {len(test_cases_data)} test cases")

    async def run_test_case(self, test_case: PromptTestCase) -> PromptTestResult:
        """Run a single test case and return the result."""
        logger.debug(f"Running test case: {test_case.name}")
        start_time = time.time()

        try:
            # Extract entities using the entity extractor
            result = await self.entity_extractor.extract_entities(
                text=test_case.input_text,
                source_description=f"Test case: {test_case.name}",
            )

            execution_time = time.time() - start_time

            if result.errors:
                return PromptTestResult(
                    test_case=test_case,
                    extracted_entities=[],
                    status=TestResultStatus.ERROR,
                    execution_time=execution_time,
                    errors=result.errors,
                )

            # Evaluate the results
            evaluation = self._evaluate_extraction_result(
                test_case.expected_entities,
                result.entities,
                test_case.confidence_threshold,
            )

            # Determine status
            status = self._determine_test_status(evaluation)

            test_result = PromptTestResult(
                test_case=test_case,
                extracted_entities=result.entities,
                status=status,
                accuracy_score=evaluation["accuracy"],
                precision=evaluation["precision"],
                recall=evaluation["recall"],
                f1_score=evaluation["f1_score"],
                execution_time=execution_time,
                missing_entities=evaluation["missing_entities"],
                unexpected_entities=evaluation["unexpected_entities"],
            )

            logger.debug(
                f"Test case {test_case.name} completed: {status.value} "
                f"(F1: {evaluation['f1_score']:.2f})"
            )

            return test_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Test case {test_case.name} failed with error: {e}")

            return PromptTestResult(
                test_case=test_case,
                extracted_entities=[],
                status=TestResultStatus.ERROR,
                execution_time=execution_time,
                errors=[str(e)],
            )

    async def run_test_suite(
        self,
        test_case_names: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PromptTestResult]:
        """Run multiple test cases and return results."""
        # Filter test cases
        test_cases_to_run = self._filter_test_cases(test_case_names, tags)

        if not test_cases_to_run:
            logger.warning("No test cases to run")
            return []

        logger.info(f"Running {len(test_cases_to_run)} test cases")

        # Run test cases concurrently
        tasks = [self.run_test_case(test_case) for test_case in test_cases_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        test_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Test case failed with exception: {result}")
                test_results.append(
                    PromptTestResult(
                        test_case=test_cases_to_run[i],
                        extracted_entities=[],
                        status=TestResultStatus.ERROR,
                        errors=[str(result)],
                    )
                )
            else:
                test_results.append(result)

        # Store results
        self._test_results.extend(test_results)

        # Log summary
        self._log_test_summary(test_results)

        return test_results

    def _filter_test_cases(
        self,
        test_case_names: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PromptTestCase]:
        """Filter test cases based on names and tags."""
        test_cases = list(self._test_cases.values())

        if test_case_names:
            test_cases = [tc for tc in test_cases if tc.name in test_case_names]

        if tags:
            test_cases = [
                tc for tc in test_cases if any(tag in tc.tags for tag in tags)
            ]

        return test_cases

    def _evaluate_extraction_result(
        self,
        expected_entities: List[Dict[str, Any]],
        extracted_entities: List[ExtractedEntity],
        confidence_threshold: float,
    ) -> Dict[str, Any]:
        """Evaluate extraction results against expected entities."""
        # Filter extracted entities by confidence
        filtered_entities = [
            entity
            for entity in extracted_entities
            if entity.confidence >= confidence_threshold
        ]

        # Convert to comparable format
        expected_set = {
            (entity["name"].lower(), entity["type"].upper())
            for entity in expected_entities
        }

        extracted_set = {
            (entity.name.lower(), entity.entity_type.value.upper())
            for entity in filtered_entities
        }

        # Calculate metrics
        true_positives = len(expected_set & extracted_set)
        false_positives = len(extracted_set - expected_set)
        false_negatives = len(expected_set - extracted_set)

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = true_positives / len(expected_set) if expected_set else 1.0

        # Find missing and unexpected entities
        missing_entities = [
            entity
            for entity in expected_entities
            if (entity["name"].lower(), entity["type"].upper()) not in extracted_set
        ]

        unexpected_entities = [
            entity
            for entity in filtered_entities
            if (entity.name.lower(), entity.entity_type.value.upper())
            not in expected_set
        ]

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "missing_entities": missing_entities,
            "unexpected_entities": unexpected_entities,
        }

    def _determine_test_status(self, evaluation: Dict[str, Any]) -> TestResultStatus:
        """Determine test status based on evaluation metrics."""
        f1_score = evaluation["f1_score"]

        if f1_score >= 0.9:
            return TestResultStatus.PASSED
        elif f1_score >= 0.5:
            return TestResultStatus.PARTIAL
        else:
            return TestResultStatus.FAILED

    def _log_test_summary(self, results: List[PromptTestResult]) -> None:
        """Log a summary of test results."""
        total_tests = len(results)
        passed = sum(1 for r in results if r.status == TestResultStatus.PASSED)
        partial = sum(1 for r in results if r.status == TestResultStatus.PARTIAL)
        failed = sum(1 for r in results if r.status == TestResultStatus.FAILED)
        errors = sum(1 for r in results if r.status == TestResultStatus.ERROR)

        avg_f1 = (
            sum(r.f1_score for r in results) / total_tests if total_tests > 0 else 0.0
        )
        avg_time = (
            sum(r.execution_time for r in results) / total_tests
            if total_tests > 0
            else 0.0
        )

        logger.info(
            f"Test Summary: {total_tests} tests - "
            f"Passed: {passed}, Partial: {partial}, Failed: {failed}, Errors: {errors} - "
            f"Avg F1: {avg_f1:.3f}, Avg Time: {avg_time:.2f}s"
        )

    def get_test_statistics(self) -> Dict[str, Any]:
        """Get statistics about test cases and results."""
        if not self._test_results:
            return {"message": "No test results available"}

        recent_results = self._test_results[-100:]  # Last 100 results

        status_counts = {}
        for status in TestResultStatus:
            status_counts[status.value] = sum(
                1 for r in recent_results if r.status == status
            )

        avg_metrics = {
            "accuracy": sum(r.accuracy_score for r in recent_results)
            / len(recent_results),
            "precision": sum(r.precision for r in recent_results) / len(recent_results),
            "recall": sum(r.recall for r in recent_results) / len(recent_results),
            "f1_score": sum(r.f1_score for r in recent_results) / len(recent_results),
            "execution_time": sum(r.execution_time for r in recent_results)
            / len(recent_results),
        }

        return {
            "total_test_cases": len(self._test_cases),
            "total_results": len(self._test_results),
            "recent_results_count": len(recent_results),
            "status_distribution": status_counts,
            "average_metrics": avg_metrics,
        }

    def export_results(self, filepath: str) -> None:
        """Export test results to a JSON file."""
        results_data = [result.to_dict() for result in self._test_results]

        with open(filepath, "w") as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"Exported {len(results_data)} test results to {filepath}")

    def clear_results(self) -> None:
        """Clear all test results."""
        self._test_results.clear()
        logger.info("Cleared all test results")


def create_default_test_cases() -> List[PromptTestCase]:
    """Create a set of default test cases for software development entity extraction."""

    test_cases = [
        PromptTestCase(
            name="basic_microservices",
            input_text="The User Service connects to PostgreSQL database and exposes a REST API for user management. The Frontend Team uses React to consume this API.",
            expected_entities=[
                {"name": "User Service", "type": "SERVICE"},
                {"name": "PostgreSQL", "type": "DATABASE"},
                {"name": "REST API", "type": "API"},
                {"name": "Frontend Team", "type": "TEAM"},
                {"name": "React", "type": "TECHNOLOGY"},
            ],
            description="Basic microservices architecture with database and frontend",
            tags=["microservices", "basic", "api"],
        ),
        PromptTestCase(
            name="complex_architecture",
            input_text="Our microservices architecture includes the Payment Gateway, Order Processing Service, and Notification Service. All services use Docker containers and are deployed on Kubernetes. The Backend Team maintains these services while the DevOps Team handles deployment.",
            expected_entities=[
                {"name": "Payment Gateway", "type": "SERVICE"},
                {"name": "Order Processing Service", "type": "SERVICE"},
                {"name": "Notification Service", "type": "SERVICE"},
                {"name": "Docker", "type": "TECHNOLOGY"},
                {"name": "Kubernetes", "type": "TECHNOLOGY"},
                {"name": "Backend Team", "type": "TEAM"},
                {"name": "DevOps Team", "type": "TEAM"},
                {"name": "Microservices Architecture", "type": "CONCEPT"},
            ],
            description="Complex microservices with multiple teams and technologies",
            tags=["microservices", "complex", "teams"],
        ),
        PromptTestCase(
            name="api_endpoints",
            input_text="The API exposes several endpoints: GET /api/v1/users for user listing, POST /api/v1/users for user creation, and DELETE /api/v1/users/{id} for user deletion. Authentication is handled via JWT tokens.",
            expected_entities=[
                {"name": "GET /api/v1/users", "type": "ENDPOINT"},
                {"name": "POST /api/v1/users", "type": "ENDPOINT"},
                {"name": "DELETE /api/v1/users/{id}", "type": "ENDPOINT"},
                {"name": "JWT", "type": "TECHNOLOGY"},
                {"name": "API", "type": "API"},
            ],
            description="API endpoints and authentication",
            tags=["api", "endpoints", "authentication"],
        ),
        PromptTestCase(
            name="database_technologies",
            input_text="The system uses PostgreSQL for transactional data, Redis for caching, and Elasticsearch for search functionality. The Data Team manages all database operations.",
            expected_entities=[
                {"name": "PostgreSQL", "type": "DATABASE"},
                {"name": "Redis", "type": "DATABASE"},
                {"name": "Elasticsearch", "type": "DATABASE"},
                {"name": "Data Team", "type": "TEAM"},
            ],
            description="Multiple database technologies and team",
            tags=["database", "caching", "search"],
        ),
        PromptTestCase(
            name="project_and_features",
            input_text="The Mobile App Redesign project includes the new Authentication Module and improved User Profile Feature. The Mobile Team is working with the Design Team to implement these changes.",
            expected_entities=[
                {"name": "Mobile App Redesign", "type": "PROJECT"},
                {"name": "Authentication Module", "type": "PROJECT"},
                {"name": "User Profile Feature", "type": "PROJECT"},
                {"name": "Mobile Team", "type": "TEAM"},
                {"name": "Design Team", "type": "TEAM"},
            ],
            description="Projects, features, and team collaboration",
            tags=["project", "features", "mobile"],
        ),
    ]

    return test_cases
