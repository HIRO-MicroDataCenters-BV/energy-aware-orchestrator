"""
Constants used across the application.
"""
import os
from enum import Enum


# Prometheus configuration
PROMETHEUS_BASE_URL = os.getenv(
    "PROMETHEUS_BASE_URL",
    "http://localhost:9090/api/v1"
)

PROMETHEUS_METRICS_URL = f"{PROMETHEUS_BASE_URL}/query"
PROMETHEUS_QUERY_RANGE_URL = f"{PROMETHEUS_BASE_URL}/query_range"


WORKLOAD_ACTION_TYPE_ENUM = ("Bind", "Create", "Delete", "Move", "Swap")
WORKLOAD_ACTION_STATUS_ENUM = ("pending", "successful", "failed", "partial")
POD_PARENT_TYPE_ENUM = (
    "Deployment",
    "StatefulSet",
    "ReplicaSet",
    "Job",
    "DaemonSet",
    "CronJob",
)

class WorkloadActionTypeEnum(str, Enum):
    """
    Enum for workload action types.
    """
    BIND = "Bind"
    CREATE = "Create"
    DELETE = "Delete"
    MOVE = "Move"
    SWAP = "Swap"

class WorkloadActionStatusEnum(str, Enum):
    """
    Enum for action statuses.
    """
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    PARTIAL = "partial"

class PodParentTypeEnum(str, Enum):
    """Enum for pod parent types.
    """
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    REPLICASET = "ReplicaSet"
    JOB = "Job"
    DAEMONSET = "DaemonSet"
    CRONJOB = "CronJob"
    OTHER = "Other"
