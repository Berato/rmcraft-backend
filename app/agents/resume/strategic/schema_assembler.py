"""
Schema Assembler - Validates, repairs, and builds final Pydantic-shaped resume objects.

This module centralizes Pydantic enforcement and repair for sub-agent outputs,
reducing runtime warnings and brittle behavior from mixing output_schema with tools/transfers.
"""

import json
import logging
from typing import Dict, Any, List, Tuple, Optional, Union
from pydantic import BaseModel, ValidationError
from app.schemas.ResumeSchemas import (
    Experience, Skill, Project, Education, ContactInfo,
    ExperienceAgentOutPutSchema, SkillsAgentOutPutSchema,
    ProjectsAgentOutPutSchema, EducationAgentOutPutSchema,
    ContactInfoAgentOutPutSchema, SummaryAgentOutPutSchema
        , NameAgentOutPutSchema
)

# Configure logging
logger = logging.getLogger(__name__)

class RepairDiagnostic(BaseModel):
    """Diagnostic information for each field repair attempt."""
    field: str
    original_fragment: Any
    repairs_applied: List[str]  # e.g., ["coercion", "llm", "fallback"]
    status: str  # "OK", "PARTIAL", "FAILED"
    retry_count: int = 0
    error_message: Optional[str] = None

class SchemaAssembler:
    """
    Assembles and validates final resume object from sub-agent fragments.

    Handles normalization, validation, deterministic repairs, and fallback logic.
    """

    def __init__(self):
        self.diagnostics: List[RepairDiagnostic] = []

    def clean_json_response(self, raw_text: str) -> str:
        """
        Clean raw LLM response by removing markdown formatting and extracting pure JSON.
        """
        if not raw_text:
            return raw_text

        # Remove markdown code block markers
        text = raw_text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]

        if text.endswith('```'):
            text = text[:-3]

        # Remove any leading/trailing whitespace and newlines
        text = text.strip()

        # If the text starts with markdown headers or explanatory text, try to find JSON
        if not text.startswith('{'):
            # Look for JSON object in the text
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx + 1]

        return text

    def normalize_input(self, value: Any) -> Any:
        """
        Normalize input value for validation.
        - If Pydantic model, call .model_dump()
        - If string, clean and parse JSON
        - Otherwise return as-is
        """
        if hasattr(value, 'model_dump'):
            return value.model_dump()

        if isinstance(value, str):
            # If the string looks like JSON (starts with { or [ or a ``` code block),
            # attempt to parse it. Otherwise, treat it as a plain string and
            # return it unchanged so fields like 'summary' or 'name' are preserved.
            cleaned = self.clean_json_response(value)
            trimmed = cleaned.lstrip()
            if trimmed.startswith('{') or trimmed.startswith('[') or cleaned.startswith('```'):
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON string: {cleaned}")
                    return None
            # Plain text - return as-is so higher-level logic can wrap it into
            # the expected dict shape (e.g., {'summary': '...'}).
            return value

        return value

    def apply_coercion_repairs(self, data: Any, target_schema: BaseModel) -> Tuple[Any, List[str]]:
        """
        Apply deterministic coercion repairs to make data compatible with schema.
        Returns (repaired_data, applied_repairs)
        """
        repairs = []

        if data is None:
            # Try to create minimal valid instance
            try:
                if hasattr(target_schema, '__fields__'):
                    # Pydantic v1
                    fields = target_schema.__fields__
                else:
                    # Pydantic v2
                    fields = target_schema.model_fields

                # Create dict with defaults
                repaired = {}
                for field_name, field_info in fields.items():
                    if hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ == list:
                        repaired[field_name] = []
                    elif hasattr(field_info.annotation, '__origin__') and field_info.annotation.__origin__ == dict:
                        repaired[field_name] = {}
                    elif field_info.annotation == str:
                        repaired[field_name] = ""
                    else:
                        # Use field default or None
                        repaired[field_name] = field_info.default if field_info.default is not ... else None

                repairs.append("coercion: None -> defaults")
                return repaired, repairs
            except Exception as e:
                logger.error(f"Failed to create default instance: {e}")
                return data, repairs

        # If data is not a dict, try to wrap it appropriately
        if not isinstance(data, dict):
            repaired = {"value": data}
            repairs.append("coercion: non-dict -> wrapped")
        else:
            repaired = data.copy()

        # Apply repairs to the repaired dict
        if isinstance(repaired, dict):
            # Handle None values for required strings
            for key, value in repaired.items():
                if value is None and isinstance(key, str):
                    if 'name' in key or 'title' in key or 'description' in key or 'summary' in key:
                        repaired[key] = ""
                        repairs.append(f"coercion: {key} None -> ''")

            # Handle single object -> list conversions
            list_fields = []
            dict_fields = []
            if hasattr(target_schema, '__fields__'):
                # Pydantic v1
                fields = target_schema.__fields__
            else:
                # Pydantic v2
                fields = target_schema.model_fields
            for field_name, field_info in fields.items():
                if hasattr(field_info.annotation, '__origin__'):
                    if field_info.annotation.__origin__ == list:
                        list_fields.append(field_name)
                    elif field_info.annotation.__origin__ == dict:
                        dict_fields.append(field_name)
            for field in list_fields:
                if field in repaired and repaired[field] is not None:
                    value = repaired[field]
                    if not isinstance(value, list):
                        repaired[field] = [value]
                        repairs.append(f"coercion: {field} single -> list")

            # Handle missing list fields
            for field in list_fields:
                if field not in repaired or repaired[field] is None:
                    repaired[field] = []
                    repairs.append(f"coercion: {field} missing -> []")

            # Handle missing dict fields
            for field in dict_fields:
                if field not in repaired or repaired[field] is None:
                    repaired[field] = {}
                    repairs.append(f"coercion: {field} missing -> {{}}")

        return repaired, repairs

    def validate_with_schema(self, data: Any, schema_class: BaseModel) -> Tuple[bool, Optional[ValidationError]]:
        """
        Validate data against Pydantic schema.
        Returns (is_valid, validation_error)
        """
        try:
            schema_class(**data)
            return True, None
        except ValidationError as e:
            return False, e
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            return False, None

    def assemble_resume_object(self, fragments: Dict[str, Any]) -> Tuple[Dict[str, Any], List[RepairDiagnostic]]:
        """
        Main assembly method that validates, repairs, and builds final resume object.

        Args:
            fragments: Dict mapping field names to raw sub-agent outputs

        Returns:
            (final_resume_dict, diagnostics)
        """
        self.diagnostics = []
        final_resume = {}

        # Define field-to-schema mapping
        field_schemas = {
            'experiences': ExperienceAgentOutPutSchema,
            'skills': SkillsAgentOutPutSchema,
            'projects': ProjectsAgentOutPutSchema,
            'education': EducationAgentOutPutSchema,
            'contact_info': ContactInfoAgentOutPutSchema,
            'summary': SummaryAgentOutPutSchema,
            'name': NameAgentOutPutSchema
        }

        for field_name, schema_class in field_schemas.items():
            raw_value = fragments.get(field_name)
            diagnostic = RepairDiagnostic(
                field=field_name,
                original_fragment=raw_value,
                repairs_applied=[],
                status="OK"
            )

            # Step 1: Normalize input
            normalized = self.normalize_input(raw_value)

            # Step 1.5: Wrap non-dict values into expected dict format
            if not isinstance(normalized, dict):
                normalized = {field_name: normalized}

            # Step 2: Attempt validation
            is_valid, validation_error = self.validate_with_schema(normalized, schema_class)

            if is_valid:
                # Extract the field value
                if isinstance(normalized, dict) and field_name in normalized:
                    # Extract the inner value if it's a dict with the field
                    value = normalized[field_name]
                    final_resume[field_name] = value
                else:
                    # For dict schemas, use the whole dict
                    final_resume[field_name] = normalized
                diagnostic.status = "OK"
            else:
                # Quick-accept: if validation failed but the raw fragment contains
                # a non-empty value of the expected Python type for certain
                # flexible fields (summary as str, projects as list), accept it
                # directly to avoid losing useful content from LLMs.
                try:
                    # Determine candidate value (handle wrapped dicts)
                    candidate = None
                    if isinstance(normalized, dict) and field_name in normalized:
                        candidate = normalized[field_name]
                    else:
                        candidate = normalized

                    if field_name == 'summary' and isinstance(candidate, str) and candidate.strip():
                        final_resume[field_name] = candidate
                        diagnostic.status = "OK"
                        self.diagnostics.append(diagnostic)
                        continue

                    if field_name == 'projects' and isinstance(candidate, list) and len(candidate) > 0:
                        final_resume[field_name] = candidate
                        diagnostic.status = "OK"
                        self.diagnostics.append(diagnostic)
                        continue
                except Exception:
                    # Fall through to coercion repairs on any unexpected error
                    pass

                # Step 3: Apply coercion repairs
                repaired, repairs = self.apply_coercion_repairs(normalized, schema_class)
                diagnostic.repairs_applied.extend(repairs)

                # Step 4: Re-validate after coercion
                is_valid_after_coercion, _ = self.validate_with_schema(repaired, schema_class)

                if is_valid_after_coercion:
                    # Extract the field value
                    if isinstance(repaired, dict) and field_name in repaired:
                        # Extract the inner value if it's a dict with the field
                        value = repaired[field_name]
                        final_resume[field_name] = value
                    else:
                        # For dict schemas, use the whole dict
                        final_resume[field_name] = repaired
                    diagnostic.status = "PARTIAL"
                    diagnostic.repairs_applied.append("coercion")
                else:
                    # Step 5: Apply safe fallback
                    if field_name in ['experiences', 'skills', 'projects', 'education', 'contact_info']:
                        final_resume[field_name] = []
                    elif field_name == 'summary':
                        final_resume[field_name] = ""

                    diagnostic.status = "FAILED"
                    diagnostic.repairs_applied.append("fallback")
                    diagnostic.error_message = str(validation_error) if validation_error else "Validation failed"

            self.diagnostics.append(diagnostic)

        # Ensure all required fields exist
        required_fields = [
            'experiences', 'skills', 'projects', 'education', 'contact_info',
            'summary', 'name'
        ]

        for field in required_fields:
            if field not in final_resume:
                if field in ['experiences', 'skills', 'projects', 'education', 'contact_info']:
                    final_resume[field] = []
                else:
                    final_resume[field] = ""

        return final_resume, self.diagnostics

def create_resume_from_fragments(fragments: Dict[str, Any]) -> Tuple[Dict[str, Any], List[RepairDiagnostic]]:
    """
    Convenience function to assemble resume from fragments using SchemaAssembler.
    """
    assembler = SchemaAssembler()
    return assembler.assemble_resume_object(fragments)
