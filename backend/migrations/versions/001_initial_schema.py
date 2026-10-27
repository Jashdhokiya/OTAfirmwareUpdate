"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table('users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='admin'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Devices
    op.create_table('devices',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_uid', sa.String(64), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('hardware_model', sa.String(100), nullable=False, server_default='ESP32'),
        sa.Column('api_key_hash', sa.String(255), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default='false'),
        sa.Column('firmware_version', sa.String(50), nullable=True),
        sa.Column('desired_firmware_version', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='offline'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ip_address', sa.String(45), nullable=True),
        sa.Column('wifi_rssi', sa.Integer(), nullable=True),
        sa.Column('uptime_seconds', sa.Integer(), nullable=True),
        sa.Column('free_heap_bytes', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON(), server_default='{}'),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('group_name', sa.String(100), nullable=True),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_devices_device_uid', 'devices', ['device_uid'])
    op.create_index('ix_devices_group_name', 'devices', ['group_name'])

    # Firmware Releases
    op.create_table('firmware_releases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('release_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('hardware_model', sa.String(100), nullable=False, server_default='ESP32'),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('min_compatible_version', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_firmware_releases_version', 'firmware_releases', ['version'])

    # Deployments
    op.create_table('deployments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('firmware_release_id', sa.String(36), sa.ForeignKey('firmware_releases.id'), nullable=False),
        sa.Column('target_selection', sa.JSON(), nullable=False),
        sa.Column('rollout_strategy', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='created'),
        sa.Column('current_stage', sa.Integer(), nullable=True),
        sa.Column('total_devices', sa.Integer(), server_default='0'),
        sa.Column('successful_devices', sa.Integer(), server_default='0'),
        sa.Column('failed_devices', sa.Integer(), server_default='0'),
        sa.Column('max_failure_percentage', sa.Integer(), server_default='20'),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Device Deployment Attempts
    op.create_table('device_deployment_attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('deployment_id', sa.String(36), sa.ForeignKey('deployments.id'), nullable=False),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('attempt_number', sa.Integer(), server_default='1'),
        sa.Column('stage_number', sa.Integer(), nullable=True),
        sa.Column('command_id', sa.String(36), unique=True, nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('deployment_id', 'device_id', 'attempt_number', name='uq_deployment_device_attempt'),
    )
    op.create_index('ix_dda_deployment_id', 'device_deployment_attempts', ['deployment_id'])
    op.create_index('ix_dda_device_id', 'device_deployment_attempts', ['device_id'])

    # Device Telemetry
    op.create_table('device_telemetry',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('uptime_seconds', sa.Integer(), nullable=True),
        sa.Column('free_heap_bytes', sa.Integer(), nullable=True),
        sa.Column('wifi_rssi', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('firmware_version', sa.String(50), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_device_telemetry_device_id', 'device_telemetry', ['device_id'])
    op.create_index('ix_device_telemetry_recorded_at', 'device_telemetry', ['recorded_at'])

    # Device Events
    op.create_table('device_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('device_id', sa.String(36), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_device_events_device_id', 'device_events', ['device_id'])
    op.create_index('ix_device_events_event_type', 'device_events', ['event_type'])
    op.create_index('ix_device_events_created_at', 'device_events', ['created_at'])

    # Audit Logs
    op.create_table('audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=True),
        sa.Column('resource_id', sa.String(36), nullable=True),
        sa.Column('details', sa.JSON(), server_default='{}'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('device_events')
    op.drop_table('device_telemetry')
    op.drop_table('device_deployment_attempts')
    op.drop_table('deployments')
    op.drop_table('firmware_releases')
    op.drop_table('devices')
    op.drop_table('users')
