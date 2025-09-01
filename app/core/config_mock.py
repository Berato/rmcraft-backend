"""Mock configuration to bypass pydantic_settings dependency"""

class MockSettings:
    DATABASE_URL = "sqlite:///test.db"
    SECRET_KEY = "test_secret"
    DEBUG = True

settings = MockSettings()
