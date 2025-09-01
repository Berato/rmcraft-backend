"""
Integration test for the Schema Assembler Plan implementation.
This test verifies that the updated strategic resume agent works with the schema assembler.
"""

import asyncio
import json
from unittest.mock import Mock, patch
from app.agents.resume.strategic.schema_assembler import create_resume_from_fragments


async def test_schema_assembler_integration():
    """
    Integration test to verify schema assembler works with realistic agent outputs.
    """
    # Mock agent outputs that might come from the LLM agents
    mock_agent_outputs = {
        "experiences": json.dumps({
            "experiences": [
                {
                    "id": "exp_1",
                    "company": "Tech Corp",
                    "position": "Senior Engineer",
                    "startDate": "2020-01",
                    "endDate": "2023-01",
                    "responsibilities": ["Led development", "Mentored team"]
                }
            ]
        }),
        "skills": json.dumps({
            "skills": [
                {"id": "skill_1", "name": "Python", "level": 5},
                {"id": "skill_2", "name": "JavaScript", "level": 4}
            ],
            "additional_skills": ["Docker", "AWS"]
        }),
        "projects": json.dumps({
            "projects": [
                {
                    "id": "proj_1",
                    "name": "E-commerce Platform",
                    "description": "Built scalable e-commerce platform",
                    "url": "https://example.com"
                }
            ]
        }),
        "summary": json.dumps({
            "summary": "Experienced software engineer with 5+ years in web development"
        }),
        "design_brief": json.dumps({
            "layout_description": "Modern two-column resume layout",
            "color_palette": {"primary": "#1a365d", "accent": "#3182ce"},
            "google_fonts": ["Inter", "Roboto Slab"],
            "design_prompt_for_developer": "Create a clean, modern resume with two columns"
        }),
        "jinja_template": json.dumps({
            "jinja_template": "<html><body>{{ summary }}</body></html>",
            "css_styles": "body { font-family: Inter; }"
        })
    }

    # Simulate collecting outputs from agents
    collected_fragments = {}

    for key, raw_output in mock_agent_outputs.items():
        try:
            # Simulate the JSON parsing that happens in the main workflow
            cleaned = raw_output.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            parsed = json.loads(cleaned)

            # Store the full parsed dict for schema assembler
            collected_fragments[key] = parsed
        except json.JSONDecodeError:
            print(f"Failed to parse {key}")
            collected_fragments[key] = None

    # Use schema assembler to create final resume
    final_resume, diagnostics = create_resume_from_fragments(collected_fragments)

    # Verify the final resume structure
    assert "experiences" in final_resume
    assert "skills" in final_resume
    assert "projects" in final_resume
    assert "summary" in final_resume
    assert "design_brief" in final_resume
    assert "jinja_template" in final_resume
    assert "css_styles" in final_resume

    # Verify experiences
    assert len(final_resume["experiences"]) == 1
    assert final_resume["experiences"][0]["company"] == "Tech Corp"

    # Verify skills
    assert len(final_resume["skills"]["skills"]) == 2
    assert final_resume["skills"]["skills"][0]["name"] == "Python"

    # Verify projects
    assert len(final_resume["projects"]) == 1
    assert final_resume["projects"][0]["name"] == "E-commerce Platform"

    # Verify summary
    assert "software engineer" in final_resume["summary"]

    # Verify design brief
    assert "layout_description" in final_resume["design_brief"]
    assert "color_palette" in final_resume["design_brief"]

    # Check diagnostics
    successful_fields = [d for d in diagnostics if d.status == "OK"]
    repaired_fields = [d for d in diagnostics if d.status == "PARTIAL"]

    print(f"✅ Integration test passed!")
    print(f"   - {len(successful_fields)} fields validated successfully")
    print(f"   - {len(repaired_fields)} fields required repairs")
    print(f"   - Total fields processed: {len(diagnostics)}")

    return final_resume, diagnostics


if __name__ == "__main__":
    # Run the integration test
    asyncio.run(test_schema_assembler_integration())
