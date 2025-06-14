"""Entity extraction prompts for software development domains.

This module provides customized prompt templates that extend Graphiti's built-in
entity extraction capabilities with domain-specific knowledge for software
development, documentation, and system architecture.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from graphiti_core.prompts.models import Message

from ...utils.logging import LoggingConfig
from ..types import EntityType

logger = LoggingConfig.get_logger(__name__)


class PromptDomain(Enum):
    """Supported prompt domains."""

    SOFTWARE_DEVELOPMENT = "software_development"
    DOCUMENTATION = "documentation"
    SYSTEM_ARCHITECTURE = "system_architecture"
    API_DOCUMENTATION = "api_documentation"
    CODE_REVIEW = "code_review"
    GENERAL = "general"


@dataclass
class PromptContext:
    """Context information for prompt generation."""

    episode_content: str
    entity_types: list[dict[str, Any]]
    domain: PromptDomain = PromptDomain.GENERAL
    custom_prompt: str = ""
    reference_time: str | None = None
    previous_episodes: list[dict[str, Any]] = field(default_factory=list)
    extraction_hints: dict[str, list[str]] = field(default_factory=dict)
    confidence_threshold: float = 0.5
    max_entities: int = 50


@dataclass
class PromptTemplate:
    """Template for entity extraction prompts."""

    name: str
    domain: PromptDomain
    system_prompt: str
    user_prompt_template: str
    entity_guidelines: dict[str, str] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)
    version: str = "1.0"

    def format_user_prompt(self, context: PromptContext) -> str:
        """Format the user prompt with context information."""
        return self.user_prompt_template.format(
            episode_content=context.episode_content,
            entity_types=json.dumps(context.entity_types, indent=2),
            custom_prompt=context.custom_prompt,
            reference_time=context.reference_time or datetime.utcnow().isoformat(),
            extraction_hints=self._format_extraction_hints(context.extraction_hints),
            confidence_threshold=context.confidence_threshold,
            max_entities=context.max_entities,
            domain_guidelines=self._get_domain_guidelines(),
        )

    def _format_extraction_hints(self, hints: dict[str, list[str]]) -> str:
        """Format extraction hints for the prompt."""
        if not hints:
            return ""

        formatted = []
        for entity_type, hint_list in hints.items():
            formatted.append("- {entity_type}: {', '.join(hint_list)}")

        return "\n".join(formatted)

    def _get_domain_guidelines(self) -> str:
        """Get domain-specific guidelines."""
        return self.entity_guidelines.get(self.domain.value, "")

    def generate_messages(self, context: PromptContext) -> list[Message]:
        """Generate prompt messages for LLM."""
        return [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=self.format_user_prompt(context)),
        ]


class SoftwareDevelopmentPrompts:
    """Pre-defined prompts for software development entity extraction."""

    @staticmethod
    def get_software_entity_extraction_prompt() -> PromptTemplate:
        """Get the main software development entity extraction prompt."""

        system_prompt = """You are an expert software architect and code analyst specializing in extracting entities from software development content.

Your task is to identify and extract software-related entities such as services, APIs, databases, teams, technologies, and concepts from technical documentation, code, and related content.

Focus on entities that are relevant for understanding system architecture, dependencies, and relationships in software projects."""

        user_prompt_template = """
<CONTENT>
{episode_content}
</CONTENT>

<ENTITY_TYPES>
{entity_types}
</ENTITY_TYPES>

<DOMAIN_GUIDELINES>
{domain_guidelines}
</DOMAIN_GUIDELINES>

<EXTRACTION_HINTS>
{extraction_hints}
</EXTRACTION_HINTS>

Extract software development entities from the CONTENT above. Focus on:

1. **Services & APIs**: Microservices, REST APIs, GraphQL endpoints, web services
2. **Databases & Storage**: Databases, tables, schemas, data stores, caches
3. **Technologies**: Programming languages, frameworks, libraries, tools
4. **Teams & People**: Development teams, engineers, product owners, stakeholders
5. **Projects & Features**: Software projects, features, modules, components
6. **Concepts**: Architectural patterns, design principles, methodologies

{custom_prompt}

**Extraction Guidelines:**
- Extract entities that are explicitly mentioned or clearly implied
- Use full, descriptive names (avoid abbreviations when possible)
- Focus on entities relevant to software architecture and development
- Avoid extracting actions, relationships, or temporal information
- Prioritize entities that help understand system structure and dependencies
- Consider the context of software development workflows

**Quality Standards:**
- Confidence threshold: {confidence_threshold}
- Maximum entities to extract: {max_entities}
- Prefer specific, well-defined entities over vague concepts
- Ensure entity names are clear and unambiguous

**Reference Time:** {reference_time}
"""

        entity_guidelines = {
            "software_development": """
**Software Development Entity Guidelines:**

- **Service**: Named microservices, web services, APIs (e.g., "User Authentication Service", "Payment API")
- **Database**: Specific databases, tables, schemas (e.g., "PostgreSQL Users DB", "Redis Cache")
- **Technology**: Programming languages, frameworks, tools (e.g., "React", "Docker", "Kubernetes")
- **Team**: Development teams, squads, departments (e.g., "Backend Team", "Platform Engineering")
- **Person**: Individual developers, architects, product owners (e.g., "John Smith", "Lead Developer")
- **Project**: Software projects, features, modules (e.g., "Mobile App Redesign", "Authentication Module")
- **API**: Specific API endpoints, interfaces (e.g., "REST User API", "GraphQL Schema")
- **Endpoint**: Specific API endpoints, routes (e.g., "/api/v1/users", "GET /health")
- **Organization**: Companies, departments, external vendors (e.g., "Engineering Org", "AWS")
- **Concept**: Architectural patterns, methodologies (e.g., "Microservices Architecture", "CI/CD Pipeline")
""",
        }

        examples = [
            {
                "input": "The User Service connects to PostgreSQL database and exposes a REST API for user management. The Frontend Team uses React to consume this API.",
                "expected_entities": [
                    {"name": "User Service", "type": "SERVICE"},
                    {"name": "PostgreSQL", "type": "DATABASE"},
                    {"name": "REST API", "type": "API"},
                    {"name": "Frontend Team", "type": "TEAM"},
                    {"name": "React", "type": "TECHNOLOGY"},
                ],
            },
            {
                "input": "Our microservices architecture includes the Payment Gateway, Order Processing Service, and Notification Service. All services use Docker containers and are deployed on Kubernetes.",
                "expected_entities": [
                    {"name": "Payment Gateway", "type": "SERVICE"},
                    {"name": "Order Processing Service", "type": "SERVICE"},
                    {"name": "Notification Service", "type": "SERVICE"},
                    {"name": "Docker", "type": "TECHNOLOGY"},
                    {"name": "Kubernetes", "type": "TECHNOLOGY"},
                    {"name": "Microservices Architecture", "type": "CONCEPT"},
                ],
            },
        ]

        return PromptTemplate(
            name="software_entity_extraction",
            domain=PromptDomain.SOFTWARE_DEVELOPMENT,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            entity_guidelines=entity_guidelines,
            examples=examples,
            version="1.0",
        )

    @staticmethod
    def get_api_documentation_prompt() -> PromptTemplate:
        """Get prompt optimized for API documentation entity extraction."""

        system_prompt = """You are an expert API documentation analyst specializing in extracting entities from API specifications, documentation, and related technical content.

Focus on identifying APIs, endpoints, services, data models, and related technical entities that define the structure and behavior of software interfaces."""

        user_prompt_template = """
<API_CONTENT>
{episode_content}
</API_CONTENT>

<ENTITY_TYPES>
{entity_types}
</ENTITY_TYPES>

Extract API-related entities from the content above. Focus specifically on:

1. **API Services**: Named APIs, web services, microservices
2. **Endpoints**: Specific API endpoints, routes, paths
3. **Data Models**: Request/response models, schemas, DTOs
4. **Technologies**: API frameworks, protocols, standards
5. **Authentication**: Auth methods, security schemes
6. **Databases**: Data stores accessed by APIs

{custom_prompt}

**API-Specific Guidelines:**
- Extract specific endpoint paths (e.g., "/api/v1/users", "/health")
- Identify API services by name (e.g., "User Management API")
- Capture data models and schemas mentioned
- Note authentication and security mechanisms
- Include API frameworks and technologies used

**Reference Time:** {reference_time}
"""

        return PromptTemplate(
            name="api_documentation_extraction",
            domain=PromptDomain.API_DOCUMENTATION,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            version="1.0",
        )

    @staticmethod
    def get_code_review_prompt() -> PromptTemplate:
        """Get prompt optimized for code review entity extraction."""

        system_prompt = """You are an expert code reviewer specializing in extracting entities from code review comments, pull requests, and development discussions.

Focus on identifying the software components, issues, improvements, and technical entities discussed in code review contexts."""

        user_prompt_template = """
<CODE_REVIEW_CONTENT>
{episode_content}
</CODE_REVIEW_CONTENT>

<ENTITY_TYPES>
{entity_types}
</ENTITY_TYPES>

Extract entities from the code review content above. Focus on:

1. **Code Components**: Classes, functions, modules, files mentioned
2. **Issues**: Bugs, performance problems, security concerns
3. **Technologies**: Libraries, frameworks, tools discussed
4. **People**: Reviewers, authors, team members
5. **Concepts**: Design patterns, best practices, methodologies

{custom_prompt}

**Code Review Guidelines:**
- Extract specific code components being reviewed
- Identify technical issues and improvements discussed
- Capture tools and technologies mentioned
- Note people involved in the review process
- Focus on actionable technical entities

**Reference Time:** {reference_time}
"""

        return PromptTemplate(
            name="code_review_extraction",
            domain=PromptDomain.CODE_REVIEW,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            version="1.0",
        )


class EntityPromptManager:
    """Manager for entity extraction prompts."""

    def __init__(self):
        """Initialize the prompt manager."""
        self._prompts: dict[str, PromptTemplate] = {}
        self._load_default_prompts()

        logger.info("EntityPromptManager initialized with {len(self._prompts)} prompts")

    def _load_default_prompts(self) -> None:
        """Load default prompt templates."""
        # Software development prompts
        self.register_prompt(
            SoftwareDevelopmentPrompts.get_software_entity_extraction_prompt()
        )
        self.register_prompt(SoftwareDevelopmentPrompts.get_api_documentation_prompt())
        self.register_prompt(SoftwareDevelopmentPrompts.get_code_review_prompt())

        logger.debug("Loaded default prompt templates")

    def register_prompt(self, prompt: PromptTemplate) -> None:
        """Register a new prompt template."""
        self._prompts[prompt.name] = prompt
        logger.debug("Registered prompt template: {prompt.name}")

    def get_prompt(self, name: str) -> PromptTemplate | None:
        """Get a prompt template by name."""
        return self._prompts.get(name)

    def list_prompts(self) -> list[str]:
        """List all available prompt names."""
        return list(self._prompts.keys())

    def get_prompts_by_domain(self, domain: PromptDomain) -> list[PromptTemplate]:
        """Get all prompts for a specific domain."""
        return [prompt for prompt in self._prompts.values() if prompt.domain == domain]

    def generate_entity_extraction_messages(
        self,
        content: str,
        entity_types: list[EntityType],
        domain: PromptDomain = PromptDomain.SOFTWARE_DEVELOPMENT,
        custom_prompt: str = "",
        extraction_hints: dict[str, list[str]] | None = None,
        **kwargs,
    ) -> list[Message]:
        """Generate messages for entity extraction.

        Args:
            content: Text content to extract entities from
            entity_types: List of entity types to extract
            domain: Domain for prompt selection
            custom_prompt: Additional custom instructions
            extraction_hints: Hints for specific entity types
            **kwargs: Additional context parameters

        Returns:
            List of messages for LLM
        """
        # Convert EntityType enum to dict format expected by prompts
        entity_types_dict = [
            {
                "entity_type_id": i,
                "name": entity_type.value,
                "description": self._get_entity_description(entity_type),
            }
            for i, entity_type in enumerate(entity_types)
        ]

        # Create prompt context
        context = PromptContext(
            episode_content=content,
            entity_types=entity_types_dict,
            domain=domain,
            custom_prompt=custom_prompt,
            extraction_hints=extraction_hints or {},
            **kwargs,
        )

        # Select appropriate prompt based on domain
        prompt_name = self._select_prompt_for_domain(domain)
        prompt = self.get_prompt(prompt_name)

        if not prompt:
            logger.warning("No prompt found for domain {domain}, using default")
            prompt = self.get_prompt("software_entity_extraction")

        if not prompt:
            raise ValueError("No default prompt available")

        return prompt.generate_messages(context)

    def _select_prompt_for_domain(self, domain: PromptDomain) -> str:
        """Select the best prompt for a given domain."""
        domain_prompt_map = {
            PromptDomain.SOFTWARE_DEVELOPMENT: "software_entity_extraction",
            PromptDomain.API_DOCUMENTATION: "api_documentation_extraction",
            PromptDomain.CODE_REVIEW: "code_review_extraction",
            PromptDomain.DOCUMENTATION: "software_entity_extraction",
            PromptDomain.SYSTEM_ARCHITECTURE: "software_entity_extraction",
            PromptDomain.GENERAL: "software_entity_extraction",
        }

        return domain_prompt_map.get(domain, "software_entity_extraction")

    def _get_entity_description(self, entity_type: EntityType) -> str:
        """Get description for an entity type."""
        descriptions = {
            EntityType.SERVICE: "A software service, microservice, or web service",
            EntityType.DATABASE: "A database, data store, or storage system",
            EntityType.TEAM: "A development team, squad, or group of people",
            EntityType.PERSON: "An individual person, developer, or team member",
            EntityType.ORGANIZATION: "A company, department, or organizational unit",
            EntityType.PROJECT: "A software project, feature, or development initiative",
            EntityType.CONCEPT: "An architectural pattern, methodology, or abstract concept",
            EntityType.TECHNOLOGY: "A programming language, framework, library, or tool",
            EntityType.API: "An application programming interface or API service",
            EntityType.ENDPOINT: "A specific API endpoint, route, or URL path",
        }

        return descriptions.get(entity_type, "A software-related entity")

    def get_extraction_hints_for_domain(
        self, domain: PromptDomain
    ) -> dict[str, list[str]]:
        """Get default extraction hints for a domain."""
        hints = {
            PromptDomain.SOFTWARE_DEVELOPMENT: {
                "SERVICE": ["service", "microservice", "API", "backend", "frontend"],
                "DATABASE": [
                    "database",
                    "DB",
                    "PostgreSQL",
                    "MySQL",
                    "Redis",
                    "MongoDB",
                ],
                "TECHNOLOGY": ["React", "Node.js", "Python", "Docker", "Kubernetes"],
                "TEAM": ["team", "squad", "engineering", "developers"],
                "API": ["REST", "GraphQL", "API", "endpoint", "interface"],
            },
            PromptDomain.API_DOCUMENTATION: {
                "API": ["REST", "GraphQL", "API", "service", "interface"],
                "ENDPOINT": ["endpoint", "route", "path", "/api/", "GET", "POST"],
                "SERVICE": ["service", "microservice", "backend"],
                "TECHNOLOGY": ["HTTP", "JSON", "OAuth", "JWT", "OpenAPI"],
            },
            PromptDomain.CODE_REVIEW: {
                "TECHNOLOGY": ["library", "framework", "dependency", "package"],
                "PERSON": ["author", "reviewer", "developer", "@"],
                "CONCEPT": ["pattern", "practice", "principle", "architecture"],
            },
        }

        return hints.get(domain, {})

    def update_prompt(self, name: str, **updates) -> bool:
        """Update an existing prompt template."""
        if name not in self._prompts:
            return False

        prompt = self._prompts[name]
        for key, value in updates.items():
            if hasattr(prompt, key):
                setattr(prompt, key, value)

        logger.info("Updated prompt template: {name}")
        return True

    def remove_prompt(self, name: str) -> bool:
        """Remove a prompt template."""
        if name in self._prompts:
            del self._prompts[name]
            logger.info("Removed prompt template: {name}")
            return True
        return False

    def get_prompt_statistics(self) -> dict[str, Any]:
        """Get statistics about registered prompts."""
        domain_counts = {}
        for prompt in self._prompts.values():
            domain = prompt.domain.value
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_prompts": len(self._prompts),
            "domains": domain_counts,
            "prompt_names": list(self._prompts.keys()),
        }
