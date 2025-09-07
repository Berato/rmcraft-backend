# In app/tools/file_uploader.py
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


def _get_env(name: str, *aliases: str) -> str | None:
    """Return the first non-empty env var among name + aliases."""
    for key in (name, *aliases):
        val = os.getenv(key)
        if val:
            return val
    return None


def configure_cloudinary():
    """Configures the Cloudinary client with credentials from .env.

    Preferred keys:
      CLOUDINARY_CLOUD_NAME
      CLOUDINARY_API_KEY
      CLOUDINARY_API_SECRET

    Backwards-compatible fallbacks:
      CLOUD_NAME, CLOUDINARY_SECRET
    """
    cloud_name = _get_env("CLOUDINARY_CLOUD_NAME", "CLOUD_NAME")
    api_key = _get_env("CLOUDINARY_API_KEY")
    api_secret = _get_env("CLOUDINARY_API_SECRET", "CLOUDINARY_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        missing = [k for k, v in {
            'CLOUDINARY_CLOUD_NAME': cloud_name,
            'CLOUDINARY_API_KEY': api_key,
            'CLOUDINARY_API_SECRET': api_secret
        }.items() if not v]
        print(f"⚠️ Cloudinary config missing vars: {missing}. Uploads will likely fail.")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )


def upload_to_cloudinary(file_path: str, public_id: str) -> str | None:
    """Uploads a file to Cloudinary and returns its secure URL.

    Returns None on failure (callers should handle gracefully).
    """
    try:
        configure_cloudinary()
        upload_result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type="auto",
            overwrite=True
        )
        print("✅ File successfully uploaded to Cloudinary.")
        return upload_result.get('secure_url')
    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        return None
