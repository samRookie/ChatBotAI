"""Project API endpoints for ChatbotAI Stage 3 Phase 1."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.api.models import (
    ProjectCreate,
    ProjectDeleteResponse,
    ProjectDetailResponse,
    ProjectResponse,
)
from app.services import project_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_project(payload: ProjectCreate) -> ProjectResponse:
    try:
        data = project_service.create_project(
            name=payload.name,
            description=payload.description,
        )
        return ProjectResponse(**data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Failed to create project: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )


@router.get("", response_model=list[ProjectResponse])
@router.get("/", response_model=list[ProjectResponse], include_in_schema=False)
def list_projects() -> list[ProjectResponse]:
    try:
        projects = project_service.list_projects()
        return [ProjectResponse(**p) for p in projects]
    except Exception as exc:
        logger.error("Failed to list projects: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects",
        )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
def get_project_detail(project_id: str) -> ProjectDetailResponse:
    try:
        data = project_service.get_project_detail(project_id)
        if data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return ProjectDetailResponse(**data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch project detail for %s: %s", project_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch project detail",
        )


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
def delete_project(project_id: str) -> ProjectDeleteResponse:
    try:
        deleted = project_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found",
            )
        return ProjectDeleteResponse(id=project_id, status="deleted")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete project %s: %s", project_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project",
        )
