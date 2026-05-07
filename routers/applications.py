from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_db
from models import Application, Job, User, ApplicationStatus
from schemas import ApplicationCreate, ApplicationOut
from auth_utils import get_current_user, get_current_employer

router = APIRouter()


@router.post("/", response_model=ApplicationOut)
async def apply_to_job(
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Откликнуться на вакансию"""
    # Проверяем что вакансия существует
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    # Проверяем дубли
    existing = await db.execute(
        select(Application).where(
            Application.user_id == user.id,
            Application.job_id == body.job_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Вы уже откликались на эту вакансию")

    application = Application(
        user_id=user.id,
        job_id=body.job_id,
        resume_id=body.resume_id,
        cover_letter=body.cover_letter
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@router.get("/my", response_model=List[ApplicationOut])
async def my_applications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Мои отклики"""
    result = await db.execute(
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.created_at.desc())
    )
    return result.scalars().all()


@router.get("/incoming", response_model=List[dict])
async def incoming_applications(
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Входящие отклики на вакансии компании (для работодателя)"""
    if not user.company:
        raise HTTPException(status_code=400, detail="Нет профиля компании")

    result = await db.execute(
        select(Application)
        .join(Job)
        .where(Job.company_id == user.company.id)
        .order_by(Application.created_at.desc())
    )
    applications = result.scalars().all()
    return [{"id": a.id, "job_id": a.job_id, "user_id": a.user_id, "status": a.status, "created_at": a.created_at} for a in applications]


@router.patch("/{application_id}/status")
async def update_status(
    application_id: int,
    status: ApplicationStatus,
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Изменить статус отклика (работодатель)"""
    result = await db.execute(
        select(Application)
        .join(Job)
        .where(Application.id == application_id, Job.company_id == user.company.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Отклик не найден")

    application.status = status
    await db.commit()
    return {"success": True, "status": status}
