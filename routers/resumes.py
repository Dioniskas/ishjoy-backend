from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models import Resume, User
from schemas import ResumeCreate, ResumeOut
from auth_utils import get_current_user

router = APIRouter()


@router.get("/my", response_model=List[ResumeOut])
async def my_resumes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Мои резюме"""
    result = await db.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{resume_id}", response_model=ResumeOut)
async def get_resume(resume_id: int, db: AsyncSession = Depends(get_db)):
    """Получить резюме по ID"""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено")
    if not resume.is_public:
        raise HTTPException(status_code=403, detail="Резюме приватное")
    return resume


@router.post("/", response_model=ResumeOut)
async def create_resume(
    body: ResumeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать резюме"""
    resume = Resume(
        user_id=user.id,
        **body.model_dump()
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.patch("/{resume_id}", response_model=ResumeOut)
async def update_resume(
    resume_id: int,
    body: ResumeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Обновить резюме"""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(resume, field, value)
    await db.commit()
    await db.refresh(resume)
    return resume


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить резюме"""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено")

    await db.delete(resume)
    await db.commit()
    return {"success": True}
