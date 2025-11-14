"""
Pydantic models for Kubernetes API responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ContainerInfo(BaseModel):
    name: str
    image: str
    resources: Dict[str, Any] = {}


class ContainerStatus(BaseModel):
    name: str
    ready: bool
    restart_count: int
    image: str
    state: Dict[str, Any] = {}


class PodInfo(BaseModel):
    name: str
    namespace: str
    uid: str
    node_name: Optional[str]
    phase: str
    pod_ip: Optional[str]
    host_ip: Optional[str]
    start_time: Optional[str]
    created_at: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    containers: List[ContainerInfo] = []
    container_statuses: List[ContainerStatus] = []
    restart_policy: Optional[str]
    service_account: Optional[str]
    conditions: List[Dict[str, Any]] = []


class NamespaceInfo(BaseModel):
    name: str
    uid: str
    phase: str
    created_at: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class PodsResponse(BaseModel):
    status: str
    namespace: str
    pods: List[PodInfo]
    count: int
    timestamp: str


class NamespacesResponse(BaseModel):
    status: str
    namespaces: List[NamespaceInfo]
    count: int
    timestamp: str


class AllPodsResponse(BaseModel):
    status: str
    pods_by_namespace: Dict[str, List[PodInfo]]
    total_pods: int
    namespace_count: int
    timestamp: str


class AppPodsInfo(BaseModel):
    app_name: str
    app_definition_id: Optional[str] = None
    workload_type: Optional[str] = None
    pods: List[PodInfo]
    pod_count: int


class AppPodsResponse(BaseModel):
    status: str
    apps: List[AppPodsInfo]
    total_apps: int
    total_pods: int
    timestamp: str


class ConnectionTestResponse(BaseModel):
    status: str
    api_server: str
    authenticated: bool
    version: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
