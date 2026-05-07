from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import anthropic
import json
import os

from database import get_db
from models import User, Job, Resume, JobStatus
from schemas import (
    GenerateResumeRequest, AISearchRequest,
    AICoverLetterRequest, AIInterviewRequest, AIChatRequest, ResumeOut
)
from auth_utils import get_current_user

router = APIRouter()

# Anthropic клиент
claude = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@router.post("/generate-resume")
async def generate_resume(
    body: GenerateResumeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    AI генерирует структурированное резюме из свободного текста.
    Пользователь просто описывает себя, AI создаёт профессиональное резюме.
    """
    prompt = f"""Пользователь рассказал о себе:
{body.user_description}

На основе этой информации создай профессиональное резюме в формате JSON.
Верни ТОЛЬКО JSON без пояснений:

{{
  "title": "Желаемая должность",
  "summary": "Краткое профессиональное описание (3-4 предложения)",
  "skills": ["навык1", "навык2", ...],
  "experience": [
    {{
      "company": "Название компании",
      "position": "Должность",
      "start_date": "01.2020",
      "end_date": "03.2023",
      "description": "Основные обязанности и достижения"
    }}
  ],
  "education": [
    {{
      "institution": "Название учебного заведения",
      "degree": "Степень/специальность",
      "year": "2019"
    }}
  ],
  "languages": [
    {{"language": "Русский", "level": "Родной"}},
    {{"language": "Английский", "level": "B2"}}
  ],
  "city": "Город",
  "desired_salary": 5000000
}}

Если информация не указана — придумай разумные значения на основе контекста.
Зарплата в узбекских сумах (UZS).
"""

    message = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Убираем markdown если есть
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    resume_data = json.loads(raw)

    # Сохраняем в БД
    resume = Resume(
        user_id=user.id,
        title=resume_data.get("title", "Специалист"),
        summary=resume_data.get("summary"),
        skills=resume_data.get("skills", []),
        experience=resume_data.get("experience", []),
        education=resume_data.get("education", []),
        languages=resume_data.get("languages", []),
        city=resume_data.get("city"),
        desired_salary=resume_data.get("desired_salary"),
        currency="UZS",
        ai_generated=True,
        is_public=True
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    return {
        "success": True,
        "resume_id": resume.id,
        "resume": resume_data,
        "message": "Резюме создано с помощью AI и сохранено в вашем профиле"
    }


@router.post("/smart-search")
async def smart_search(
    body: AISearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    AI анализирует запрос и находит подходящие вакансии,
    объясняет почему они подходят
    """
    # Получаем вакансии из БД
    result = await db.execute(
        select(Job).where(Job.status == JobStatus.active).limit(50)
    )
    jobs = result.scalars().all()

    jobs_text = "\n".join([
        f"ID:{j.id} | {j.title} в {j.company.name if j.company else 'Компания'} | "
        f"{j.city} | {j.job_type} | Зарплата: {j.salary_min}-{j.salary_max} UZS | "
        f"Навыки: {', '.join(j.skills or [])}"
        for j in jobs
    ])

    prompt = f"""Пользователь ищет работу: "{body.query}"
{f'Город: {body.city}' if body.city else ''}
{f'Тип работы: {body.job_type}' if body.job_type else ''}

Доступные вакансии:
{jobs_text}

Найди 3-5 наиболее подходящих вакансий и объясни почему.
Верни JSON:
{{
  "matches": [
    {{
      "job_id": 1,
      "relevance_score": 95,
      "reason": "Почему эта вакансия подходит (1-2 предложения)"
    }}
  ],
  "advice": "Общий совет по поиску работы по данному запросу"
}}
"""

    message = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    ai_result = json.loads(raw.strip())

    # Добавляем полные данные вакансий
    job_map = {j.id: j for j in jobs}
    enriched_matches = []
    for match in ai_result.get("matches", []):
        job = job_map.get(match["job_id"])
        if job:
            enriched_matches.append({
                **match,
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "city": job.city,
                    "job_type": job.job_type,
                    "salary_min": float(job.salary_min) if job.salary_min else None,
                    "salary_max": float(job.salary_max) if job.salary_max else None,
                }
            })

    return {
        "matches": enriched_matches,
        "advice": ai_result.get("advice", "")
    }


@router.post("/cover-letter")
async def generate_cover_letter(
    body: AICoverLetterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI генерирует сопроводительное письмо"""
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    resume_result = await db.execute(
        select(Resume).where(Resume.id == body.resume_id, Resume.user_id == user.id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Резюме не найдено")

    prompt = f"""Напиши профессиональное сопроводительное письмо для отклика на вакансию.

Вакансия: {job.title} в компании {job.company.name if job.company else 'Компания'}
Описание вакансии: {job.description[:500]}

Кандидат:
- Должность: {resume.title}
- О себе: {resume.summary}
- Навыки: {', '.join(resume.skills or [])}

Требования:
- Письмо на русском языке
- 3-4 абзаца
- Профессиональный но живой тон
- Подчеркни соответствие навыков требованиям вакансии
- Вырази мотивацию работать именно в этой компании
"""

    message = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"cover_letter": message.content[0].text}


@router.post("/interview-prep")
async def interview_prep(
    body: AIInterviewRequest,
    user: User = Depends(get_current_user)
):
    """AI подготовка к собеседованию"""
    prompt = f"""Составь список вопросов для собеседования на должность "{body.job_title}" 
уровня {body.level} с подсказками по ответам.

Верни JSON:
{{
  "technical_questions": [
    {{"question": "...", "hint": "На что обратить внимание в ответе"}}
  ],
  "hr_questions": [
    {{"question": "...", "hint": "..."}}
  ],
  "questions_to_ask": ["Вопрос работодателю 1", "Вопрос работодателю 2"],
  "tips": "Общие советы по этому собеседованию"
}}
"""

    message = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


@router.post("/chat")
async def ai_chat(body: AIChatRequest):
    """Общий AI-чат для карьерных вопросов"""
    system = """Ты — опытный карьерный консультант в Узбекистане. 
Помогаешь людям найти работу, улучшить резюме, подготовиться к собеседованиям.
Знаешь рынок труда Узбекистана, популярные компании (Uzum, Payme, Click, Beeline UZ, MyTaxi и др.)
Отвечай на русском языке, конкретно и полезно. Используй эмодзи."""

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    response = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=system,
        messages=messages
    )

    return {"reply": response.content[0].text}


@router.post("/salary-insight")
async def salary_insight(
    job_title: str,
    city: str = "Ташкент",
    experience_years: int = 2
):
    """AI анализ зарплат по должности"""
    message = await claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""Какая средняя зарплата для "{job_title}" в {city}, Узбекистан 
с опытом {experience_years} лет? 
Дай реалистичные данные в UZS и USD, укажи диапазон junior/middle/senior.
Ответь кратко и структурированно."""
        }]
    )
    return {"insight": message.content[0].text}
