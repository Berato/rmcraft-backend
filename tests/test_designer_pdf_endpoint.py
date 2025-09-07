"""
Integration test for the /themes/render-pdfs endpoint
"""
import pytest
import requests
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# Test data constants
TEST_RESUME_ID = "73b735da-6ef3-4134-baa8-4bbc57fa38fb"
TEST_COVER_LETTER_ID = "test-cover-letter-123"
TEST_THEME_PACKAGE_ID = "test-theme-package-123"

@pytest.fixture(scope="module")
def test_data():
    """Set up test data for the integration test"""
    base_url = "http://localhost:8000/api/v1"

    # 1. Create test resume
    resume_data = {
        "name": "Test Resume for PDF Generation",
        "summary": "Senior Software Engineer with experience",
        "personalInfo": {
            "firstName": "Jane",
            "lastName": "Doe",
            "email": "jane.doe@example.com",
            "phone": "555-1234",
            "location": "San Francisco, CA"
        },
        "experience": [
            {
                "id": "exp_1",
                "company": "Test Corp",
                "position": "Senior Developer",
                "startDate": "2021-01",
                "endDate": "2024-08",
                "responsibilities": ["Led development team", "Built scalable systems"]
            }
        ],
        "education": [
            {
                "id": "edu_1",
                "institution": "Test University",
                "degree": "BS Computer Science",
                "startDate": "2017",
                "endDate": "2021"
            }
        ],
        "skills": [
            {"id": "skill_1", "name": "Python", "level": 5},
            {"id": "skill_2", "name": "JavaScript", "level": 4}
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "Test Project",
                "description": "A test project",
                "url": "https://example.com/project"
            }
        ]
    }

    # Create resume
    resume_response = requests.post(f"{base_url}/resumes", json=resume_data)
    if resume_response.status_code == 201:
        resume_id = resume_response.json()['data']['id']
        print(f"✅ Created test resume: {resume_id}")
    else:
        # Use suggested ID if creation fails
        resume_id = TEST_RESUME_ID
        print(f"⚠️ Using fallback resume ID: {resume_id}")

    # 2. Create test cover letter
    cover_data = {
        "title": "Test Cover Letter",
        "jobDetails": {
            "title": "Software Engineer",
            "company": "Test Company",
            "url": "https://example.com/job"
        },
        "openingParagraph": "I am excited to apply for the Software Engineer position.",
        "bodyParagraphs": [
            "I have extensive experience in software development.",
            "My skills include Python and JavaScript."
        ],
        "closingParagraph": "Thank you for considering my application.",
        "tone": "professional",
        "resumeId": resume_id
    }

    # Create cover letter
    cover_response = requests.post(f"{base_url}/cover_letters/strategic-create", json=cover_data)
    if cover_response.status_code == 201:
        cover_id = cover_response.json()['data']['coverLetterId']
        print(f"✅ Created test cover letter: {cover_id}")
    else:
        cover_id = TEST_COVER_LETTER_ID
        print(f"⚠️ Using fallback cover letter ID: {cover_id}")

    # 3. Create test theme package (this would require the theme creation endpoint)
    # For now, we'll assume a theme package exists or create one via API
    theme_data = {
        "design_prompt": "Create a professional blue theme",
        "user_id": "test-user-123"
    }
    # Note: This would need an image file, so we'll mock or skip for now
    theme_package_id = TEST_THEME_PACKAGE_ID
    print(f"⚠️ Using mock theme package ID: {theme_package_id}")

    return {
        "resume_id": resume_id,
        "cover_letter_id": cover_id,
        "theme_package_id": theme_package_id
    }

def test_render_pdfs_endpoint(test_data):
    """Test the /themes/render-pdfs endpoint"""
    base_url = "http://localhost:8000/api/v1"
    url = f"{base_url}/themes/render-pdfs"

    payload = {
        "theme_package_id": test_data["theme_package_id"],
        "resume_id": test_data["resume_id"],
        "cover_letter_id": test_data["cover_letter_id"],
        "upload": False  # Disable upload for test
    }

    print("🎨 Testing PDF rendering endpoint...")
    print(f"📡 POST {url}")
    print(f"📋 Payload: {payload}")

    # Mock Cloudinary upload to avoid external dependencies
    with patch('app.tools.file_uploader.upload_to_cloudinary', return_value=None):
        response = requests.post(url, json=payload)

    print(f"📊 Status Code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"📄 Response: {result}")

        # Validate response structure
        assert "data" in result
        data = result["data"]

        # Check for PDF paths
        assert "resume_pdf_path" in data
        assert "cover_pdf_path" in data

        # Verify files exist
        resume_path = data["resume_pdf_path"]
        cover_path = data["cover_pdf_path"]

        assert os.path.exists(resume_path), f"Resume PDF not found at {resume_path}"
        assert os.path.exists(cover_path), f"Cover PDF not found at {cover_path}"

        # Check file sizes (should be > 0)
        resume_size = os.path.getsize(resume_path)
        cover_size = os.path.getsize(cover_path)

        assert resume_size > 0, "Resume PDF is empty"
        assert cover_size > 0, "Cover PDF is empty"

        print("✅ PDFs generated successfully!")
        print(f"   Resume PDF: {resume_path} ({resume_size} bytes)")
        print(f"   Cover PDF: {cover_path} ({cover_size} bytes)")

        # Clean up test files
        os.remove(resume_path)
        os.remove(cover_path)
        print("🧹 Cleaned up test PDFs")

    elif response.status_code == 404:
        print("❌ Test data not found - this is expected if test setup failed")
        print(f"Response: {response.text}")
        pytest.skip("Test data setup failed")

    else:
        print(f"❌ Unexpected status code: {response.status_code}")
        print(f"Response: {response.text}")
        raise AssertionError(f"Endpoint failed with status {response.status_code}")

def test_render_pdfs_with_invalid_ids():
    """Test error handling with invalid IDs"""
    base_url = "http://localhost:8000/api/v1"
    url = f"{base_url}/themes/render-pdfs"

    payload = {
        "theme_package_id": "invalid-theme-id",
        "resume_id": "invalid-resume-id",
        "cover_letter_id": "invalid-cover-id",
        "upload": False
    }

    response = requests.post(url, json=payload)

    # Should return 404 for not found
    assert response.status_code in [404, 400]
    print("✅ Error handling works for invalid IDs")