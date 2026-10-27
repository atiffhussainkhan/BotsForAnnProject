"""
Agent Echo (Agent 5) — Platform Operations, Security, SRE & Compliance Package (`apps/backend/platform_ops`).

Exports all unified security, kill-switch, budget guard, idempotency, UK GDPR,
encrypted backup/restore, and health/chaos-drill primitives.
"""

from .backup_manager import BackupCorruptionError, BackupManager, BackupMetadata
from .budget_guard import BudgetGuard, BudgetStatusReport, SpendEntry
from .gdpr import AuditLogEntry, GDPRComplianceManager
from .health import DrillExecutionResult, HealthAndDrillMonitor
from .idempotency import DeadLetterEntry, DispatchState, IdempotencyRecord, IdempotencyStore
from .kill_switch import (
    ConnectionBadge,
    KillSwitchController,
    PlatformMode,
    PlatformStateSnapshot,
    QueuedOutboundJob,
)
from .security import (
    CSRFProtection,
    CSRFValidationError,
    EnvelopeEncryptor,
    OAuthPKCEChallenge,
    OAuthSecurityManager,
    OAuthStateError,
    OwnerPrincipal,
    RBACGuard,
    RBACPermissionError,
    SecretScrubber,
    SecurityError,
    TamperDetectedError,
    verify_webhook_hmac,
)

__all__ = [
    "AuditLogEntry",
    "BackupCorruptionError",
    "BackupManager",
    "BackupMetadata",
    "BudgetGuard",
    "BudgetStatusReport",
    "CSRFProtection",
    "CSRFValidationError",
    "ConnectionBadge",
    "DeadLetterEntry",
    "DispatchState",
    "DrillExecutionResult",
    "EnvelopeEncryptor",
    "GDPRComplianceManager",
    "HealthAndDrillMonitor",
    "IdempotencyRecord",
    "IdempotencyStore",
    "KillSwitchController",
    "OAuthPKCEChallenge",
    "OAuthSecurityManager",
    "OAuthStateError",
    "OwnerPrincipal",
    "PlatformMode",
    "PlatformStateSnapshot",
    "QueuedOutboundJob",
    "RBACGuard",
    "RBACPermissionError",
    "SecretScrubber",
    "SecurityError",
    "SpendEntry",
    "TamperDetectedError",
    "verify_webhook_hmac",
]
