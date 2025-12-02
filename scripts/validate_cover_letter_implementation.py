#!/usr/bin/env python3
"""
Simple validation script for strategic cover letter implementation
"""

def test_imports():
    """Test that all modules can be imported"""
    try:
        from app.services.cover_letter_service import validate_cover_letter_data, format_cover_letter_for_storage
        print("✅ Cover letter service imports OK")
    except ImportError as e:
        print(f"❌ Cover letter service import failed: {e}")
        return False

    try:
        from app.features.cover_letter_orchestrator import process_resume_for_chroma, assemble_cover_letter_content
        print("✅ Cover letter orchestrator imports OK")
    except ImportError as e:
        print(f"❌ Cover letter orchestrator import failed: {e}")
        return False

    try:
        from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent
        from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent
        from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent
        print("✅ Cover letter agents import OK")
    except ImportError as e:
        print(f"❌ Cover letter agents import failed: {e}")
        return False

    return True


def test_service_functions():
    """Test service functions"""
    from app.services.cover_letter_service import validate_cover_letter_data, format_cover_letter_for_storage

    # Test validation
    valid_data = {
        "openingParagraph": "Dear Hiring Manager,",
        "bodyParagraphs": ["I am excited to apply."],
        "closingParagraph": "Thank you.",
        "finalContent": "Full content",
        "resumeId": "test-123"
    }

    assert validate_cover_letter_data(valid_data) == True
    print("✅ Service validation works")

    # Test formatting
    formatted = format_cover_letter_for_storage(valid_data)
    assert "createdAt" in formatted
    assert "updatedAt" in formatted
    print("✅ Service formatting works")


def test_orchestrator_functions():
    """Test orchestrator utility functions"""
    from app.features.cover_letter_orchestrator import assemble_cover_letter_content

    test_content = {
        "opening_paragraph": "Dear Hiring Manager,",
        "body_paragraphs": ["I am excited.", "My experience includes X."],
        "closing_paragraph": "Thank you."
    }

    result = assemble_cover_letter_content(test_content)
    expected = "Dear Hiring Manager,\n\nI am excited.\n\nMy experience includes X.\n\nThank you."
    assert result == expected
    print("✅ Content assembly works")


def test_resume_processing():
    """Test resume processing for ChromaDB"""
    from app.features.cover_letter_orchestrator import process_resume_for_chroma

    test_resume = {
        "experience": [
            {
                "company": "Test Corp",
                "position": "Developer",
                "responsibilities": ["Developed software"]
            }
        ],
        "skills": [{"name": "Python"}],
        "summary": "Experienced developer"
    }

    documents, metadatas, ids = process_resume_for_chroma(test_resume)

    assert len(documents) > 0
    assert len(metadatas) > 0
    assert len(ids) > 0
    print("✅ Resume processing works")


if __name__ == "__main__":
    print("🧪 Testing Strategic Cover Letter Implementation")
    print("=" * 50)

    if not test_imports():
        print("❌ Import tests failed")
        exit(1)

    print("\n📋 Testing service functions...")
    test_service_functions()

    print("\n📋 Testing orchestrator functions...")
    test_orchestrator_functions()

    print("\n📋 Testing resume processing...")
    test_resume_processing()

    print("\n✅ All basic tests passed!")
    print("\n📝 Implementation Summary:")
    print("- ✅ Cover letter orchestrator created")
    print("- ✅ Three specialized agents (analyst, writer, editor)")
    print("- ✅ API endpoint for strategic cover letter generation")
    print("- ✅ Service layer for utilities")
    print("- ✅ Basic test suite")
    print("- ✅ Router registration in main.py")
    print("\n🚀 Ready for testing with: USE_MOCK_ADK=true python main.py")
    print("📡 API endpoint: POST /api/v1/cover-letters/strategic-create")
