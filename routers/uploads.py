from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client
import os, time

from database import get_db
from models import User
from auth_utils import get_current_user

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = "ishjoy-public"

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

ALLOWED_IMAGE = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE:
        raise HTTPException(400, "Разрешены только JPG, PNG, WEBP")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Файл слишком большой. Максимум 10MB")

    path = f"avatars/user_{user.id}_{int(time.time())}.jpg"
    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(path, content, {"content-type": file.content_type, "upsert": "true"})
    url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"

    user.avatar_url = url
    await db.commit()
    return {"url": url}

@router.post("/company-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE:
        raise HTTPException(400, "Разрешены только JPG, PNG, WEBP")
    if not user.company:
        raise HTTPException(400, "Сначала создайте профиль компании")

    content = await file.read()
    path = f"logos/company_{user.company.id}_{int(time.time())}.jpg"
    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(path, content, {"content-type": file.content_type, "upsert": "true"})
    url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"

    user.company.logo_url = url
    await db.commit()
    return {"url": url}

@router.post("/resume-pdf")
async def upload_resume_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Разрешены только PDF файлы")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Максимум 5MB")

    path = f"resumes/resume_{user.id}_{int(time.time())}.pdf"
    sb = get_supabase()
    sb.storage.from_(BUCKET).upload(path, content, {"content-type": "application/pdf", "upsert": "true"})
    url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
    return {"url": url}
