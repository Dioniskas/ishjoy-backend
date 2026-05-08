from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn

from database import engine
from routers import auth, jobs, resumes, applications, ai_features, companies, notifications, uploads

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="Ishjoy API",
    description="Backend для платформы поиска работы Ishjoy (Узбекистан)",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Авторизация"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Вакансии"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["Резюме"])
app.include_router(applications.router, prefix="/api/applications", tags=["Отклики"])
app.include_router(ai_features.router, prefix="/api/ai", tags=["AI функции"])
app.include_router(companies.router, prefix="/api/companies", tags=["Компании"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Уведомления"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Загрузка файлов"])

@app.get("/")
async def root():
    return {"message": "Ishjoy API работает!", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
