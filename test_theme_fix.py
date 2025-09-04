#!/usr/bin/env python3
"""
Quick test script to verify the theme creation endpoint works after fixing the template variable issue.
"""

import requests
import io
from PIL import Image

def test_theme_creation():
    """Test the theme creation endpoint with a simple request."""
    
    # Create a simple test image
    img = Image.new('RGB', (100, 100), color='blue')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    # Prepare the multipart form data
    files = {
        'inspiration_image': ('test.png', img_buffer, 'image/png')
    }
    
    data = {
        'design_prompt': 'Create a modern, professional theme with blue accents',
        'user_id': 'test-user-123'
    }
    
    # Make the request
    try:
        print("🚀 Testing theme creation endpoint...")
        response = requests.post(
            'http://127.0.0.1:8000/api/v1/themes/themes/create',
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 201:
            print("✅ Theme creation successful!")
            result = response.json()
            print(f"Theme Name: {result.get('name', 'N/A')}")
            print(f"Description: {result.get('description', 'N/A')}")
        else:
            print("❌ Theme creation failed!")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_theme_creation()
