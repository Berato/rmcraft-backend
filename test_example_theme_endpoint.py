"""
Test the use_example_theme flag in the render-pdfs endpoint.
"""
import pytest
from app.services.designer_pdf import get_example_theme
from app.schemas.theme import ThemeSchema


def test_get_example_theme():
    """Test that get_example_theme returns a valid ThemeSchema."""
    theme = get_example_theme()
    
    # Verify it's a ThemeSchema
    assert isinstance(theme, ThemeSchema)
    
    # Verify it has a name and description
    assert theme.name == "Example Professional Theme"
    assert "proper proportions" in theme.description.lower()
    assert "compact spacing" in theme.description.lower()
    
    # Verify resume template
    assert theme.resume_template is not None
    assert theme.resume_template.template is not None
    assert theme.resume_template.styles is not None
    
    # Verify resume template has key elements
    assert "{{ resume.personalInfo.firstName }}" in theme.resume_template.template
    assert "{{ resume.summary }}" in theme.resume_template.template
    assert "resume.experience" in theme.resume_template.template
    
    # Verify resume styles have compact spacing
    assert "font-size: 10pt" in theme.resume_template.styles or "font-size: 9.5pt" in theme.resume_template.styles
    assert ".summary-text" in theme.resume_template.styles
    assert "@page" in theme.resume_template.styles
    
    # Verify cover letter template
    assert theme.cover_letter_template is not None
    assert theme.cover_letter_template.template is not None
    assert theme.cover_letter_template.styles is not None
    
    # Verify cover letter template has key elements
    assert "cover_letter.openingParagraph" in theme.cover_letter_template.template
    assert "cover_letter.bodyParagraphs" in theme.cover_letter_template.template
    
    print("✅ get_example_theme() returns a valid, complete ThemeSchema")
    print(f"   - Resume template: {len(theme.resume_template.template)} chars")
    print(f"   - Resume styles: {len(theme.resume_template.styles)} chars")
    print(f"   - Cover template: {len(theme.cover_letter_template.template)} chars")
    print(f"   - Cover styles: {len(theme.cover_letter_template.styles)} chars")


def test_example_theme_matches_examples_file():
    """Verify get_example_theme uses the same examples as the theme_examples.py file."""
    from app.agents.theme_examples import get_resume_example_for_agent, get_cover_letter_example_for_agent
    
    theme = get_example_theme()
    resume_ex = get_resume_example_for_agent()
    cover_ex = get_cover_letter_example_for_agent()
    
    # Verify resume template matches
    assert theme.resume_template.template == resume_ex['template']
    assert theme.resume_template.styles == resume_ex['styles']
    
    # Verify cover letter template matches
    assert theme.cover_letter_template.template == cover_ex['template']
    assert theme.cover_letter_template.styles == cover_ex['styles']
    
    print("✅ get_example_theme() uses the exact same templates as theme_examples.py")


def test_example_theme_can_render():
    """Test that the example theme can actually render with sample data."""
    from app.services.designer_pdf import render_template_to_html
    
    theme = get_example_theme()
    
    # Sample resume data
    resume_data = {
        "personalInfo": {
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane@example.com",
            "phone": "555-1234",
            "location": "San Francisco, CA",
            "linkedin": "linkedin.com/in/janedoe"
        },
        "summary": "Experienced software engineer with 5+ years of experience in full-stack development. "
                   "Proven track record of delivering high-quality applications. "
                   "Passionate about clean code and user experience. "
                   "Seeking challenging opportunities in innovative tech companies.",
        "experience": [
            {
                "company": "Tech Corp",
                "position": "Senior Developer",
                "startDate": "2020-01",
                "endDate": "Present",
                "responsibilities": [
                    "Led team of 5 developers",
                    "Improved performance by 40%",
                    "Implemented CI/CD pipeline"
                ]
            },
            {
                "company": "Startup Inc",
                "position": "Software Engineer",
                "startDate": "2018-06",
                "endDate": "2019-12",
                "responsibilities": [
                    "Developed REST APIs",
                    "Built responsive frontends"
                ]
            }
        ],
        "skills": [
            {"id": "1", "name": "Python"},
            {"id": "2", "name": "JavaScript"},
            {"id": "3", "name": "React"},
            {"id": "4", "name": "PostgreSQL"}
        ],
        "education": [
            {
                "id": "1",
                "institution": "University of California",
                "degree": "BS Computer Science",
                "startDate": "2014",
                "endDate": "2018"
            }
        ]
    }
    
    # Sample cover letter data
    cover_data = {
        "title": "Application for Senior Developer Position",
        "openingParagraph": "I am writing to express my strong interest in the Senior Developer position at your company.",
        "bodyParagraphs": [
            "With over 5 years of experience in software development, I have consistently delivered high-quality solutions.",
            "My expertise in Python and JavaScript, combined with my leadership experience, makes me an ideal candidate.",
        ],
        "companyConnection": "I am particularly excited about your company's mission to innovate in the tech space.",
        "closingParagraph": "Thank you for considering my application. I look forward to discussing how I can contribute to your team."
    }
    
    # Try to render both templates
    try:
        resume_html = render_template_to_html(theme.resume_template.template, {"resume": resume_data})
        cover_html = render_template_to_html(theme.cover_letter_template.template, {"cover_letter": cover_data})
        
        # Basic checks that HTML was generated
        assert len(resume_html) > 500
        assert "Jane" in resume_html
        assert "Doe" in resume_html
        assert "Experienced software engineer" in resume_html
        assert "Tech Corp" in resume_html
        
        assert len(cover_html) > 200
        assert "Application for Senior Developer Position" in cover_html
        assert "strong interest" in cover_html
        
        print("✅ Example theme can successfully render with sample data")
        print(f"   - Resume HTML: {len(resume_html)} chars")
        print(f"   - Cover HTML: {len(cover_html)} chars")
        
    except Exception as e:
        pytest.fail(f"Failed to render templates: {e}")


if __name__ == "__main__":
    print("Testing example theme functionality...\n")
    
    try:
        test_get_example_theme()
        print()
        test_example_theme_matches_examples_file()
        print()
        test_example_theme_can_render()
        print("\n🎉 All example theme tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit(1)
