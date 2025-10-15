"""
Test the manual cover letter creation endpoint
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.session import get_db
from app.models.cover_letter import CoverLetter
import json

client = TestClient(app)

def test_create_manual_cover_letter_success(db: Session):
    """Test successful creation of a manual cover letter"""
    # Prepare test data
    payload = {
        "title": "Test Manual Cover Letter",
        "raw_text": "Dear Hiring Manager,\n\nThis is a test cover letter.\n\nBest regards,\nTest User",
        "notes": "Test notes"
    }

    # Make the request
    response = client.post("/api/v1/cover-letters/manual-create", json=payload)

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["content"] == payload["raw_text"]
    assert data["notes"] == payload["notes"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Verify database
    cover_letter = db.query(CoverLetter).filter(CoverLetter.id == data["id"]).first()
    assert cover_letter is not None
    assert cover_letter.title == payload["title"]
    assert cover_letter.finalContent == payload["raw_text"]


def test_create_manual_cover_letter_missing_title():
    """Test creation with missing required title"""
    payload = {
        "raw_text": "Some content"
    }

    response = client.post("/api/v1/cover-letters/manual-create", json=payload)
    assert response.status_code == 422  # Validation error


def test_create_manual_cover_letter_empty_text():
    """Test creation with empty raw_text"""
    payload = {
        "title": "Test",
        "raw_text": ""
    }

    response = client.post("/api/v1/cover-letters/manual-create", json=payload)
    assert response.status_code == 422  # Validation error


def test_create_manual_cover_letter_text_too_long():
    """Test creation with text exceeding length limit"""
    payload = {
        "title": "Test",
        "raw_text": "A" * 51000  # Over 50KB
    }

    response = client.post("/api/v1/cover-letters/manual-create", json=payload)
    assert response.status_code == 422
    assert "exceeds maximum length" in response.json()["detail"]


def test_create_manual_cover_letter_with_optional_fields():
    """Test creation with optional resume_id and job_profile_id"""
    import uuid
    resume_id = str(uuid.uuid4())
    job_profile_id = str(uuid.uuid4())

    payload = {
        "title": "Test with IDs",
        "raw_text": "Content",
        "resume_id": resume_id,
        "job_profile_id": job_profile_id,
        "user_id": str(uuid.uuid4()),
        "notes": "Optional notes"
    }

    response = client.post("/api/v1/cover-letters/manual-create", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["resume_id"] == resume_id
    assert data["job_profile_id"] == job_profile_id
    assert data["notes"] == payload["notes"]