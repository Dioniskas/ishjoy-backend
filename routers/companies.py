from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import User, Company, Job, Application, JobStatus
from schemas import CompanyCreate, CompanyOut
from auth_utils import get_current_user, get_current_employer

router = APIRouter()


class DashboardStats(BaseModel):
    total_jobs: int
    active_jobs: int
    total_views: int
    total_applicants: int
    pending_applicants: int
    invited_applicants: int


@router.post("/", response_model=CompanyOut)
async def create_company(
    body: CompanyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать профиль компании"""
    if user.company:
        raise HTTPException(status_code=400, detail="Профиль компании уже создан")

    company = Company(owner_id=user.id, **body.model_dump())
    db.add(company)

    # Автоматически меняем роль на работодателя
    from models import UserRole
    user.role = UserRole.employer

    await db.commit()
    await db.refresh(company)
    return company


@router.get("/my", response_model=CompanyOut)
async def get_my_company(
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Получить профиль своей компании"""
    if not user.company:
        raise HTTPException(status_code=404, detail="Профиль компании не найден")
    return user.company


@router.patch("/my", response_model=CompanyOut)
async def update_company(
    body: CompanyCreate,
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Обновить профиль компании"""
    if not user.company:
        raise HTTPException(status_code=404, detail="Профиль компании не найден")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user.company, field, value)

    await db.commit()
    await db.refresh(user.company)
    return user.company


@router.get("/my/dashboard", response_model=DashboardStats)
async def get_dashboard(
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Статистика для дашборда работодателя"""
    if not user.company:
        raise HTTPException(status_code=404, detail="Профиль компании не найден")

    company_id = user.company.id

    # Вакансии
    jobs_result = await db.execute(select(Job).where(Job.company_id == company_id))
    jobs = jobs_result.scalars().all()

    active_jobs = [j for j in jobs if j.status == JobStatus.active]
    total_views = sum(j.views_count for j in jobs)
    job_ids = [j.id for j in jobs]

    # Отклики
    total_applicants = 0
    pending = 0
    invited = 0

    if job_ids:
        apps_result = await db.execute(
            select(Application).where(Application.job_id.in_(job_ids))
        )
        apps = apps_result.scalars().all()
        total_applicants = len(apps)
        pending = len([a for a in apps if a.status == 'pending'])
        invited = len([a for a in apps if a.status == 'invited'])

    return DashboardStats(
        total_jobs=len(jobs),
        active_jobs=len(active_jobs),
        total_views=total_views,
        total_applicants=total_applicants,
        pending_applicants=pending,
        invited_applicants=invited,
    )


@router.get("/my/jobs")
async def get_my_jobs(
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Вакансии своей компании с количеством откликов"""
    if not user.company:
        raise HTTPException(status_code=404, detail="Нет профиля компании")

    result = await db.execute(
        select(Job).where(Job.company_id == user.company.id)
        .order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()

    output = []
    for job in jobs:
        apps_result = await db.execute(
            select(Application).where(Application.job_id == job.id)
        )
        apps = apps_result.scalars().all()
        output.append({
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "job_type": job.job_type,
            "city": job.city,
            "salary_min": float(job.salary_min) if job.salary_min else None,
            "salary_max": float(job.salary_max) if job.salary_max else None,
            "views_count": job.views_count,
            "is_hot": job.is_hot,
            "created_at": job.created_at,
            "total_applicants": len(apps),
            "pending": len([a for a in apps if a.status == "pending"]),
            "invited": len([a for a in apps if a.status == "invited"]),
        })

    return output


@router.get("/my/applicants")
async def get_my_applicants(
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Все отклики на вакансии компании"""
    if not user.company:
        raise HTTPException(status_code=404, detail="Нет профиля компании")

    result = await db.execute(
        select(Application)
        .join(Job)
        .where(Job.company_id == user.company.id)
        .order_by(Application.created_at.desc())
    )
    apps = result.scalars().all()

    output = []
    for app in apps:
        output.append({
            "id": app.id,
            "status": app.status,
            "cover_letter": app.cover_letter,
            "created_at": app.created_at,
            "job_id": app.job_id,
            "user_id": app.user_id,
        })
    return output
