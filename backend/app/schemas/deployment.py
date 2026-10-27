"""
Pydantic schemas for deployment endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RolloutStage(BaseModel):
    name: str
    percentage: Optional[int] = None
    count: Optional[int] = None


class RolloutStrategy(BaseModel):
    type: str = "immediate"  # immediate or staged
    stages: list[RolloutStage] = []
    max_failure_percentage: int = 20
    observation_period_seconds: int = 60


class DeploymentCreate(BaseModel):
    name: str
    firmware_release_id: str
    target_selection: dict  # {"type": "devices", "device_ids": [...]} or {"type": "group", "group_name": "..."}
    rollout_strategy: RolloutStrategy = RolloutStrategy()


class DeploymentResponse(BaseModel):
    id: str
    name: str
    firmware_release_id: str
    target_selection: dict
    rollout_strategy: dict
    status: str
    current_stage: Optional[int]
    total_devices: int
    successful_devices: int
    failed_devices: int
    created_by: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    firmware_version: Optional[str] = None
    firmware_release_name: Optional[str] = None

    class Config:
        from_attributes = True


class DeploymentAttemptResponse(BaseModel):
    id: str
    deployment_id: str
    device_id: str
    status: str
    attempt_number: int
    stage_number: Optional[int]
    command_id: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    device_name: Optional[str] = None
    device_uid: Optional[str] = None

    class Config:
        from_attributes = True


class DeploymentListResponse(BaseModel):
    deployments: list[DeploymentResponse]
    total: int


class DashboardStats(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    devices_needing_attention: int
    total_firmware_releases: int
    active_deployments: int
    deployment_success_rate: float
    recent_deployments: list[DeploymentResponse]
    firmware_distribution: dict[str, int]
