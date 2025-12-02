import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Force mock ADK if needed (or let it fallback naturally)
os.environ['USE_MOCK_ADK'] = 'true'

# Mock weasyprint to avoid import errors on systems without deps
from unittest.mock import MagicMock
sys.modules['weasyprint'] = MagicMock()
sys.modules['app.tools.pdf_generator'] = MagicMock()

# Now import services
from app.services.designer_pdf import render_template_to_html
from app.agents.theme_examples import get_markdown_resume_example_for_agent
from app.schemas.theme import ThemeSchema, ThemeTemplate
from app.schemas.ResumeSchemas import ResumeResponse
from app.agents.resume.strategic.markdown_resume_agent import markdown_resume_agent

async def test_end_to_end_markdown_strategy():
    print("🚀 Starting End-to-End Markdown Resume Test...")

    # 1. Create a "Real" Resume Object (Input)
    # 1. Create a "Real" Resume Object (Input)
    # We use a simple class to avoid Beanie initialization issues
    class MockResume:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self):
            return self.__dict__

    print("\n📝 Loading Input Resume...")
    input_resume = MockResume(
        id="test_resume_123",
        userId="user_123",
        name="John Doe Resume",
        personalInfo={
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "555-0123",
            "location": "San Francisco, CA",
            "linkedin": "linkedin.com/in/johndoe"
        },
        experience=[
            {
                "id": "exp_1",
                "company": "Tech Corp",
                "position": "Software Engineer",
                "startDate": "2020-01",
                "endDate": "Present",
                "responsibilities": ["Wrote code", "Fixed bugs"]
            }
        ],
        skills=[{"id": "s1", "name": "Python"}, {"id": "s2", "name": "React"}],
        projects=[],
        education=[],
        createdAt=datetime.now(),
        updatedAt=datetime.now(),
        # Initialize markdown fields
        summary_markdown=None,
        experience_markdown=None,
        skills_markdown=None,
        projects_markdown=None,
        education_markdown=None
    )

    job_description_url = "https://example.com/job/senior-engineer"
    print(f"   Target Job: {job_description_url}")

    # 2. Run the Agent (The "Magic" Part)
    print("\n🤖 Running Markdown Resume Agent...")
    try:
        agent_result = await markdown_resume_agent(
            resume=input_resume,
            job_description_url=job_description_url
        )
        
        print("✅ Agent finished successfully!")
        print("   Generated Markdown Fragments:")
        for key, value in agent_result.items():
            print(f"   - {key}: {len(value)} chars")

    except Exception as e:
        print(f"❌ Agent failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Update Resume with Agent Output
    print("\n💾 Updating Resume with Markdown Content...")
    input_resume.summary_markdown = agent_result.get("summary_markdown")
    input_resume.experience_markdown = agent_result.get("experience_markdown")
    input_resume.skills_markdown = agent_result.get("skills_markdown")
    input_resume.projects_markdown = agent_result.get("projects_markdown")
    input_resume.education_markdown = agent_result.get("education_markdown")

    # 4. Get the Markdown Theme
    print("\n🎨 Applying Markdown Theme...")
    markdown_theme_data = get_markdown_resume_example_for_agent()
    
    theme = ThemeSchema(
        name="Markdown Theme",
        description="Test theme for markdown",
        resume_template=ThemeTemplate(
            template=markdown_theme_data["template"],
            styles=markdown_theme_data["styles"]
        ),
        cover_letter_template=ThemeTemplate(
            template="<div>Cover Letter</div>",
            styles=""
        )
    )

    # 5. Render HTML (Fallback since WeasyPrint needs system deps)
    print("\n📄 Rendering HTML...")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Convert Pydantic model to dict for the renderer
        resume_dict = input_resume.model_dump()
        
        # Render HTML manually using the helper
        from app.services.designer_pdf import render_template_to_html
        
        html_content = render_template_to_html(theme.resume_template.template, {"resume": resume_dict})
        
        # Add styles to HTML for viewing
        full_html = f"<style>{theme.resume_template.styles}</style>\n{html_content}"
        
        html_path = os.path.join(output_dir, f"resume_{input_resume.id}.html")
        with open(html_path, "w") as f:
            f.write(full_html)
            
        print(f"✅ HTML created successfully at: {html_path}")
        
        print(f"\n🎉 SUCCESS! You can view the designed resume at:\n{html_path}")
        
        # Try to open it on Mac
        try:
            os.system(f"open {html_path}")
            print("   (Opened HTML automatically)")
        except:
            pass

    except Exception as e:
        print(f"❌ Error rendering HTML: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_end_to_end_markdown_strategy())
