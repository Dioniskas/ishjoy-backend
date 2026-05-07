from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import os

from database import get_db
from models import User
from auth_utils import get_current_user

router = APIRouter()

# Firebase Admin SDK — инициализируем один раз
_firebase_app = None

def get_firebase():
    global _firebase_app
    if _firebase_app:
        return _firebase_app
    try:
        import firebase_admin
        from firebase_admin import credentials
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase-credentials.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception as e:
        print(f"Firebase init error: {e}")
        return None


# ─── СХЕМЫ ──────────────────────────────────────────────────
class RegisterDeviceRequest(BaseModel):
    fcm_token: str
    platform: str = "android"  # android | ios | web

class SendNotificationRequest(BaseModel):
    user_id: int
    title: str
    body: str
    type: str = "default"  # new_job | new_application | status_changed
    data: dict = {}


# ─── ЭНДПОИНТЫ ──────────────────────────────────────────────
@router.post("/register-device")
async def register_device(
    body: RegisterDeviceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Сохраняем FCM токен устройства"""
    user.fcm_token = body.fcm_token
    user.device_platform = body.platform
    await db.commit()
    return {"success": True, "message": "Устройство зарегистрировано"}


@router.post("/send")
async def send_notification(
    body: SendNotificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Отправить push-уведомление пользователю"""
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.fcm_token:
        return {"success": False, "message": "Нет FCM токена у пользователя"}

    background_tasks.add_task(
        _send_fcm_notification,
        token=user.fcm_token,
        title=body.title,
        body_text=body.body,
        notif_type=body.type,
        data=body.data,
    )
    return {"success": True, "message": "Уведомление отправлено"}


async def _send_fcm_notification(token: str, title: str, body_text: str, notif_type: str, data: dict):
    """Реальная отправка через Firebase Admin SDK"""
    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body_text),
            data={"type": notif_type, **{k: str(v) for k, v in data.items()}},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    icon="ic_notification",
                    color="#00C37A",
                    sound="default",
                ),
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"Уведомление отправлено: {response}")
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")


# ─── HELPER ФУНКЦИИ (вызывать из других роутеров) ────────────
async def notify_new_application(employer_user: User, job_title: str, applicant_name: str, db):
    """Уведомить работодателя о новом отклике"""
    if not employer_user.fcm_token:
        return
    await _send_fcm_notification(
        token=employer_user.fcm_token,
        title="📨 Новый отклик",
        body_text=f"{applicant_name} откликнулся на '{job_title}'",
        notif_type="new_application",
        data={"job_title": job_title},
    )


async def notify_application_status(applicant: User, job_title: str, status: str):
    """Уведомить соискателя об изменении статуса отклика"""
    if not applicant.fcm_token:
        return
    status_messages = {
        "invited": ("✅ Вас приглашают!", f"Вы приглашены на собеседование по вакансии '{job_title}'"),
        "rejected": ("😔 Отклик отклонён", f"К сожалению, по вакансии '{job_title}' принято другое решение"),
        "viewed": ("👁 Резюме просмотрено", f"Работодатель просмотрел ваш отклик на '{job_title}'"),
    }
    title, body = status_messages.get(status, ("🔔 Обновление отклика", f"Статус отклика на '{job_title}' изменился"))
    await _send_fcm_notification(
        token=applicant.fcm_token,
        title=title,
        body_text=body,
        notif_type="status_changed",
        data={"job_title": job_title, "status": status},
    )


async def notify_matching_jobs(user: User, jobs: list):
    """Уведомить соискателя о подходящих новых вакансиях"""
    if not user.fcm_token or not jobs:
        return
    job = jobs[0]
    await _send_fcm_notification(
        token=user.fcm_token,
        title="💼 Новая подходящая вакансия",
        body_text=f"{job.get('title')} — {job.get('company')}",
        notif_type="new_job",
        data={},
    )
