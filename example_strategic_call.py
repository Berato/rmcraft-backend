"""
Example script showing how to call the strategic resume analysis endpoint
with proper multipart/form-data encoding for both form fields and file upload.
"""
import requests

def call_strategic_endpoint():
    """Example of how to call the strategic resume analysis endpoint correctly"""
    url = "http://localhost:8000/api/v1/resumes/strategic-analysis"

    # Form data (these become the individual fields)
    form_data = {
        "resume_id": "cme3py2tu0003fbrzfxt8wuum",
        "job_description_url": "https://www.grammarly.com/careers/jobs/engineering/software-engineer-front-end?gh_jid=5856147",
        "design_prompt": "A clean designer resume with strong, bold fonts and presence. Take most inspiration from the image I've uploaded to get an idea of what I'm going for."
    }

    # File to upload (replace 'path/to/your/image.jpg' with actual image path)
    files = {
        "inspiration_image": ("image.jpg", open("path/to/your/image.jpg", "rb"), "image/jpeg")
    }

    try:
        response = requests.post(url, data=form_data, files=files)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Success!")
            print(f"Message: {result['message']}")
            print(f"Data: {result['data']}")
        else:
            print(f"❌ Error: {response.json()}")

    except FileNotFoundError:
        print("❌ Image file not found. Please provide a valid image path.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure the FastAPI server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Example: Calling Strategic Resume Analysis Endpoint")
    print("Make sure to:")
    print("1. Start the FastAPI server: python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    print("2. Replace 'path/to/your/image.jpg' with an actual image file path")
    print("3. Update the resume_id to a valid resume ID from your database")
    print()

    call_strategic_endpoint()
