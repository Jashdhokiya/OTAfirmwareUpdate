"""
Deployment management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.schemas.deployment import (
    DeploymentCreate, DeploymentResponse, DeploymentListResponse,
    DeploymentAttemptResponse, DashboardStats,
)
from app.services.deployment_service import DeploymentService
from app.security.auth import get_current_user

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get("", response_model=DeploymentListResponse)
async def list_deployments(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    deployments = await DeploymentService.list_deployments(db, status_filter=status, limit=limit)
    items = []
    for d in deployments:
        resp = DeploymentResponse.model_validate(d)
        if d.firmware_release:
            resp.firmware_version = d.firmware_release.version
            resp.firmware_release_name = d.firmware_release.release_name
        items.append(resp)
    return DeploymentListResponse(deployments=items, total=len(items))


@router.post("", response_model=DeploymentResponse)
async def create_deployment(
    data: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        deployment = await DeploymentService.create_deployment(db, data, current_user.id)
        resp = DeploymentResponse.model_validate(deployment)
        if deployment.firmware_release:
            resp.firmware_version = deployment.firmware_release.version
            resp.firmware_release_name = deployment.firmware_release.release_name
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get dashboard statistics computed from real data."""
    stats = await DeploymentService.get_dashboard_stats(db)
    # Convert deployment objects to response models
    recent = []
    for d in stats["recent_deployments"]:
        resp = DeploymentResponse.model_validate(d)
        if d.firmware_release:
            resp.firmware_version = d.firmware_release.version
            resp.firmware_release_name = d.firmware_release.release_name
        recent.append(resp)
    stats["recent_deployments"] = recent
    return DashboardStats(**stats)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    deployment = await DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    resp = DeploymentResponse.model_validate(deployment)
    if deployment.firmware_release:
        resp.firmware_version = deployment.firmware_release.version
        resp.firmware_release_name = deployment.firmware_release.release_name
    return resp


@router.post("/{deployment_id}/start", response_model=DeploymentResponse)
async def start_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        deployment = await DeploymentService.start_deployment(db, deployment_id)
        resp = DeploymentResponse.model_validate(deployment)
        if deployment.firmware_release:
            resp.firmware_version = deployment.firmware_release.version
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{deployment_id}/cancel", response_model=DeploymentResponse)
async def cancel_deployment(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        deployment = await DeploymentService.cancel_deployment(db, deployment_id)
        return DeploymentResponse.model_validate(deployment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{deployment_id}/devices")
async def get_deployment_devices(
    deployment_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    attempts = await DeploymentService.get_deployment_attempts(db, deployment_id)
    return {"attempts": [
        {
            "id": a.id,
            "deployment_id": a.deployment_id,
            "device_id": a.device_id,
            "status": a.status,
            "attempt_number": a.attempt_number,
            "stage_number": a.stage_number,
            "command_id": a.command_id,
            "error_code": a.error_code,
            "error_message": a.error_message,
            "started_at": a.started_at.isoformat() if a.started_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "device_name": a.device.display_name if a.device else None,
            "device_uid": a.device.device_uid if a.device else None,
        }
        for a in attempts
    ]}
