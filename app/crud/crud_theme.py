from typing import List, Optional
from app.schemas.theme_documents import ThemeDoc, ThemePackageDoc


async def get_theme_packages(skip: int = 0, limit: int = 100) -> List[ThemePackageDoc]:
    return await ThemePackageDoc.find_many().skip(skip).limit(limit).to_list()


async def get_theme_package_by_id(theme_package_id: str) -> Optional[ThemePackageDoc]:
    return await ThemePackageDoc.get(theme_package_id)


async def get_themes(skip: int = 0, limit: int = 100) -> List[ThemeDoc]:
    return await ThemeDoc.find_many().skip(skip).limit(limit).to_list()


async def get_theme_by_id(theme_id: str) -> Optional[ThemeDoc]:
    return await ThemeDoc.get(theme_id)
