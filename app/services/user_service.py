from app.schemas.UserSchemas import User, UserCreate, UserUpdate
from typing import Optional
from datetime import datetime

async def get_user(user_id: str) -> Optional[User]:
    return await User.get(user_id)

async def get_user_by_email(email: str) -> Optional[User]:
    return await User.find_one(User.email == email)

async def create_user(user_in: UserCreate) -> User:
    user = User(
        id=user_in.id, # Use provided ID (from Clerk)
        email=user_in.email,
        name=user_in.name,
        firstName=user_in.firstName,
        lastName=user_in.lastName,
        phone=user_in.phone,
        website=user_in.website,
        linkedin=user_in.linkedin,
        location=user_in.location,
        onboardingComplete=user_in.onboardingComplete
    )
    await user.save()
    return user

async def update_user(user_id: str, user_in: UserUpdate) -> Optional[User]:
    user = await User.get(user_id)
    if not user:
        return None
    
    update_data = user_in.model_dump(exclude_unset=True)
    if update_data:
        update_data["updatedAt"] = datetime.now()
        await user.update({"$set": update_data})
        # Refresh to get updated fields
        user = await User.get(user_id)
        
    return user
