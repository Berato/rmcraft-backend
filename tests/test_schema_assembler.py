"""
Unit tests for Schema Assembler
"""

import pytest
from app.agents.resume.strategic.schema_assembler import SchemaAssembler, create_resume_from_fragments
from app.schemas.ResumeSchemas import Experience, Skill, Project


class TestSchemaAssembler:

    def test_clean_json_response_removes_markdown(self):
        """Test that clean_json_response properly removes markdown formatting."""
        assembler = SchemaAssembler()

        # Test with markdown code blocks
        input_text = '```json\n{"test": "value"}\n```'
        result = assembler.clean_json_response(input_text)
        assert result == '{"test": "value"}'

        # Test with triple backticks
        input_text = '```\n{"test": "value"}\n```'
        result = assembler.clean_json_response(input_text)
        assert result == '{"test": "value"}'

        # Test with explanatory text
        input_text = 'Here is the response: {"test": "value"} and some more text'
        result = assembler.clean_json_response(input_text)
        assert result == '{"test": "value"}'

    def test_normalize_input_pydantic_model(self):
        """Test normalizing Pydantic model input."""
        assembler = SchemaAssembler()

        # Create a mock Pydantic model
        class MockModel:
            def model_dump(self):
                return {"test": "value"}

        mock_model = MockModel()
        result = assembler.normalize_input(mock_model)
        assert result == {"test": "value"}

    def test_normalize_input_json_string(self):
        """Test normalizing JSON string input."""
        assembler = SchemaAssembler()

        json_string = '{"test": "value"}'
        result = assembler.normalize_input(json_string)
        assert result == {"test": "value"}

    def test_apply_coercion_repairs_none_values(self):
        """Test coercion repairs for None values."""
        assembler = SchemaAssembler()

        data = {"name": None, "description": None}
        repaired, repairs = assembler.apply_coercion_repairs(data, type('MockSchema', (), {}))

        assert repaired["name"] == ""
        assert repaired["description"] == ""
        assert "coercion: name None -> ''" in repairs
        assert "coercion: description None -> ''" in repairs

    def test_apply_coercion_repairs_single_to_list(self):
        """Test coercion repairs for single object to list."""
        assembler = SchemaAssembler()

        data = {"experiences": {"company": "TestCo", "position": "Test"}}
        repaired, repairs = assembler.apply_coercion_repairs(data, type('MockSchema', (), {}))

        assert repaired["experiences"] == [{"company": "TestCo", "position": "Test"}]
        assert "coercion: experiences single -> list" in repairs

    def test_assemble_resume_object_happy_path(self):
        """Test successful assembly of well-formed fragments."""
        fragments = {
            "experiences": [{"id": "exp1", "company": "TestCo", "position": "Engineer", "startDate": "2020-01", "endDate": "2023-01", "responsibilities": ["Did stuff"]}],
            "skills": {"skills": [{"id": "skill1", "name": "Python", "level": 4}], "additional_skills": ["JavaScript"]},
            "projects": [{"id": "proj1", "name": "Test Project", "description": "A test project", "url": "https://example.com"}],
            "summary": "A professional summary",
            "design_brief": {"layout": "two-column", "color_palette": {"primary": "#000000"}},
            "jinja_template": "<html>template</html>",
            "css_styles": "body { color: black; }"
        }

        final_resume, diagnostics = create_resume_from_fragments(fragments)

        # Check that all fields are present
        assert "experiences" in final_resume
        assert "skills" in final_resume
        assert "projects" in final_resume
        assert "summary" in final_resume
        assert "design_brief" in final_resume
        assert "jinja_template" in final_resume
        assert "css_styles" in final_resume

        # Check diagnostics
        assert len(diagnostics) > 0
        for diagnostic in diagnostics:
            assert diagnostic.status in ["OK", "PARTIAL", "FAILED"]

    def test_assemble_resume_object_with_malformed_data(self):
        """Test assembly with malformed data that needs repairs."""
        fragments = {
            "experiences": None,  # Should be repaired to empty list
            "skills": None,  # Should be repaired to default structure
            "projects": "not a list",  # Should be repaired
            "summary": None,  # Should be repaired to empty string
            "design_brief": None,  # Should be repaired to empty dict
        }

        final_resume, diagnostics = create_resume_from_fragments(fragments)

        # Check that repairs were applied
        assert final_resume["experiences"] == []
        assert final_resume["skills"] == {"skills": [], "additional_skills": []}
        assert final_resume["projects"] == []
        assert final_resume["summary"] == ""
        assert final_resume["design_brief"] == {}

        # Check that diagnostics show repairs
        failed_diagnostics = [d for d in diagnostics if d.status != "OK"]
        assert len(failed_diagnostics) > 0

    def test_assemble_resume_object_missing_fields(self):
        """Test assembly when some fields are completely missing."""
        fragments = {
            "experiences": [{"id": "exp1", "company": "TestCo", "position": "Engineer", "startDate": "2020-01", "endDate": "2023-01", "responsibilities": ["Did stuff"]}]
            # Missing all other fields
        }

        final_resume, diagnostics = create_resume_from_fragments(fragments)

        # Check that missing fields get defaults
        assert final_resume["experiences"] == fragments["experiences"]
        assert final_resume["skills"] == {"skills": [], "additional_skills": []}
        assert final_resume["projects"] == []
        assert final_resume["summary"] == ""
        assert final_resume["design_brief"] == {}
        assert final_resume["jinja_template"] == ""
        assert final_resume["css_styles"] == ""
