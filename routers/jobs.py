from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List

from database import get_db
from models import Job, Company, User, JobStatus, JobType
from schemas import JobCreate, JobUpdate, JobOut, JobListOut
from auth_utils import get_current_user, get_current_employer

router = APIRouter()


@router.get("/", response_model=JobListOut)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Поиск по названию/навыкам"),
    city: Optional[str] = None,
    job_type: Optional[JobType] = None,
    category: Optional[str] = None,
    salary_min: Optional[float] = None,
    is_hot: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Список вакансий с фильтрами"""
    query = select(Job).where(Job.status == JobStatus.active).join(Job.company)

    if q:
        query = query.where(
            or_(
                Job.title.ilike(f"%{q}%"),
                Job.description.ilike(f"%{q}%"),
            )
        )
    if city:
        query = query.where(Job.city.ilike(f"%{city}%"))
    if job_type:
        query = query.where(Job.job_type == job_type)
    if category:
        query = query.where(Job.category == category)
    if salary_min:
        query = query.where(Job.salary_min >= salary_min)
    if is_hot is not None:
        query = query.where(Job.is_hot == is_hot)

    # Считаем общее количество
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Пагинация
    query = query.order_by(Job.is_hot.desc(), Job.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListOut(items=jobs, total=total, page=page, per_page=per_page)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Получить вакансию по ID"""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    # Увеличиваем счётчик просмотров
    job.views_count += 1
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/", response_model=JobOut)
async def create_job(
    body: JobCreate,
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Создать вакансию (только работодатель)"""
    if not user.company:
        raise HTTPException(status_code=400, detail="Сначала создайте профиль компании")

    job = Job(**body.model_dump(), company_id=user.company.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.patch("/{job_id}", response_model=JobOut)
async def update_job(
    job_id: int,
    body: JobUpdate,
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Обновить вакансию"""
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.company_id == user.company.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    user: User = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db)
):
    """Удалить вакансию"""
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.company_id == user.company.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    await db.delete(job)
    await db.commit()
    return {"success": True}


@router.get("/categories/list")
async def get_categories():
    """Список категорий вакансий"""
    return {
        "categories": [
            "IT и разработка", "Дизайн", "Маркетинг", "Продажи",
            "Финансы", "HR", "Юриспруденция", "Медицина",
            "Образование", "Строительство", "Логистика", "Производство",
            "Административный персонал", "Туризм", "Другое"
        ]
    }
