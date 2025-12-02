from fastapi import APIRouter, HTTPException, Depends
from app.schemas.UserSchemas import UserResponse, UserCreate, UserUpdate
from app.services import user_service
from typing import Optional

router = APIRouter()

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(user_id: str):
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/by-email/{email}", response_model=UserResponse)
async def read_user_by_email(email: str):
    user = await user_service.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserResponse)
async def create_user(user_in: UserCreate):
    # Check if user already exists
    existing_user = await user_service.get_user(user_in.id)
    if existing_user:
        # If exists, maybe update it? Or return conflict?
        # For idempotency (webhook), we might want to update or just return existing.
        # But let's stick to standard POST behavior: 409 Conflict if ID exists.
        # However, for Clerk sync, we might want upsert behavior.
        # Let's assume the client handles checking or we return 409.
        raise HTTPException(status_code=409, detail="User already exists")
    
    user = await user_service.create_user(user_in)
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_in: UserUpdate):
    user = await user_service.update_user(user_id, user_in)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
