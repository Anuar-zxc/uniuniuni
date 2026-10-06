from fastapi import APIRouter

from app.api.v1 import admin, ai, auth, billing, interviews, jobs, orgs, profile, progress, resumes

api_router = APIRouter()
for module in (auth, profile, resumes, jobs, interviews, progress, billing, ai, admin, orgs):
    api_router.include_router(module.router)
