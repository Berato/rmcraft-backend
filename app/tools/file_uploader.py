# In app/tools/file_uploader.py
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

def configure_cloudinary():
    """Configures the Cloudinary client with credentials from .env."""
    cloudinary.config(
        cloud_name=os.getenv("CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_SECRET"),
        secure=True
    )

def upload_to_cloudinary(file_path: str, public_id: str) -> str | None:
    """Uploads a file to Cloudinary and returns its secure URL."""
    try:
        configure_cloudinary()
        upload_result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type="auto",
            overwrite=True
        )
        print(f"✅ File successfully uploaded to Cloudinary.")
        return upload_result.get('secure_url')
    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        return None
