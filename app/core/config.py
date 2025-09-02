try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    PYDANTIC_SETTINGS_AVAILABLE = True
except ImportError:
    # Fallback for testing/mock environments
    from .config_mock import settings
    PYDANTIC_SETTINGS_AVAILABLE = False

if PYDANTIC_SETTINGS_AVAILABLE:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    class Settings(BaseSettings):
        DATABASE_URL: str
        GOOGLE_API_KEY: str
        GOOGLE_GENAI_USE_VERTEXAI: str = "FALSE"

        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    settings = Settings()
else:
    # Use mock settings
    from .config_mock import settings
