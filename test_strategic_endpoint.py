"""
Test script to verify the strategic resume analysis endpoint works
"""
import requests
import json

# Test data
form_data = {
    "resume_id": "test-resume-123",
    "job_description_url": "https://example.com/job-posting",
    "design_prompt": "Create a modern, clean resume design"
}

# Create a simple test image (1x1 pixel PNG)
test_image_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
files = {
    "inspiration_image": ("test_image.png", test_image_content, "image/png")
}

# Test endpoint URL (adjust port if needed)
url = "http://localhost:8000/api/v1/resumes/strategic-analysis"

def test_endpoint():
    """Test the strategic resume analysis endpoint"""
    try:
        # For multipart/form-data with file upload, we need to use files parameter
        # Since we don't have an actual image file, we'll just test the form fields
        response = requests.post(url, data=form_data, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Endpoint is working correctly!")
        else:
            print(f"❌ Endpoint returned error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

if __name__ == "__main__":
    print("Testing Strategic Resume Analysis Endpoint...")
    test_endpoint()
