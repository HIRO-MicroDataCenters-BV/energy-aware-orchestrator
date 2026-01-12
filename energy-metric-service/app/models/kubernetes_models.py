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


# V2 Models - Enhanced App Identification

class AppPodsInfoV2(BaseModel):
    """Enhanced app information with clear app type identification."""
    app_name: str
    app_type: str = Field(..., description="Type of app: 'standard', 'custom', or 'custom-resource'")
    label_source: str = Field(..., description="Label key used to identify the app or 'EnergyAwareOrchestration CR'")
    
    # App-name label (present in both standard and custom apps)
    app_name_label: Optional[str] = Field(None, description="Value of app-name label if present (e.g., 'K8s')")
    
    # Standard K8s app fields
    app_instance: Optional[str] = Field(None, description="App instance name (for standard k8s apps)")
    app_version: Optional[str] = Field(None, description="App version (for standard k8s apps)")
    app_component: Optional[str] = Field(None, description="App component (for standard k8s apps)")
    managed_by: Optional[str] = Field(None, description="Tool managing this app (e.g., Helm, Kustomize)")
    
    # Custom app fields
    app_definition_id: Optional[str] = Field(None, description="App definition ID (for custom apps)")
    workload_type: Optional[str] = Field(None, description="Workload type: Critical, Preferred, Optional")
    
    # Custom Resource fields
    custom_resource_name: Optional[str] = Field(None, description="CR name (for custom-resource type)")
    custom_resource_namespace: Optional[str] = Field(None, description="CR namespace (for custom-resource type)")
    custom_resource_priority: Optional[str] = Field(None, description="CR priority (for custom-resource type)")
    custom_resource_phase: Optional[str] = Field(None, description="CR phase (for custom-resource type)")
    custom_resource_decision: Optional[str] = Field(None, description="CR decision action (for custom-resource type)")
    target_app_name: Optional[str] = Field(None, description="Target app name that CR references")
    target_app_kind: Optional[str] = Field(None, description="Target app kind (Deployment, Job, etc.)")
    target_app_namespace: Optional[str] = Field(None, description="Target app namespace")
    
    pods: List[PodInfo]
    pod_count: int
    namespaces: List[str] = Field(..., description="List of namespaces where this app has pods or CR is located")


class AppPodsResponseV2(BaseModel):
    """Enhanced response with app type breakdown."""
    status: str
    apps: List[AppPodsInfoV2]
    total_apps: int
    total_pods: int
    standard_apps_count: int = Field(..., description="Number of standard Kubernetes apps")
    custom_apps_count: int = Field(..., description="Number of custom apps")
    custom_resource_count: int = Field(..., description="Number of custom resources (EnergyAwareOrchestration)")
    timestamp: str


class ConnectionTestResponse(BaseModel):
    status: str
    api_server: str
    authenticated: bool
    version: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Custom Resource Models (EnergyAwareOrchestration)

class CustomResourceApplicationRef(BaseModel):
    """Application reference in EnergyAwareOrchestration CR."""
    apiVersion: Optional[str] = Field(None, alias="api_version")
    kind: str
    name: str
    namespace: Optional[str] = None

    class Config:
        populate_by_name = True


class CustomResourceSpec(BaseModel):
    """Spec section of EnergyAwareOrchestration CR."""
    energyConsumption: int = Field(..., alias="energy_consumption")
    forecastWindowDays: int = Field(..., alias="forecast_window_days")
    priority: str
    applicationRef: CustomResourceApplicationRef = Field(..., alias="application_ref")

    class Config:
        populate_by_name = True


class CustomResourceScheduledSlot(BaseModel):
    """Scheduled slot information in CR status."""
    slotNumber: Optional[int] = Field(None, alias="slot_number")
    slotStart: Optional[str] = Field(None, alias="slot_start")
    slotEnd: Optional[str] = Field(None, alias="slot_end")
    availableEnergyWatts: Optional[float] = Field(None, alias="available_energy_watts")
    requiredEnergyWatts: Optional[float] = Field(None, alias="required_energy_watts")
    confidencePercentage: Optional[float] = Field(None, alias="confidence_percentage")

    class Config:
        populate_by_name = True


class CustomResourceDecision(BaseModel):
    """Decision information in CR status."""
    action: str
    reason: str
    scheduledSlot: Optional[CustomResourceScheduledSlot] = Field(None, alias="scheduled_slot")
    nextEvaluationTime: Optional[str] = Field(None, alias="next_evaluation_time")

    class Config:
        populate_by_name = True


class CustomResourceEnergyMetrics(BaseModel):
    """Energy metrics in CR status."""
    currentSlotAvailableWatts: Optional[float] = Field(None, alias="current_slot_available_watts")
    currentSlotConsumedWatts: Optional[float] = Field(None, alias="current_slot_consumed_watts")
    requiredWatts: float = Field(..., alias="required_watts")
    sufficient: bool

    class Config:
        populate_by_name = True


class CustomResourceStatus(BaseModel):
    """Status section of EnergyAwareOrchestration CR."""
    phase: Optional[str] = None
    decision: Optional[CustomResourceDecision] = None
    energyMetrics: Optional[CustomResourceEnergyMetrics] = Field(None, alias="energy_metrics")
    lastUpdated: Optional[str] = Field(None, alias="last_updated")

    class Config:
        populate_by_name = True


class CustomResourceInfo(BaseModel):
    """Complete information about an EnergyAwareOrchestration custom resource."""
    name: str
    namespace: str
    uid: str
    created_at: str
    api_version: str
    kind: str
    generation: int
    resource_version: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}
    spec: CustomResourceSpec
    status: Optional[CustomResourceStatus] = None


class CustomResourcesResponse(BaseModel):
    """Response for listing custom resources."""
    status: str
    namespace: Optional[str] = None
    custom_resources: List[CustomResourceInfo]
    count: int
    timestamp: str


class CustomResourceResponse(BaseModel):
    """Response for a single custom resource."""
    status: str
    custom_resource: CustomResourceInfo
    timestamp: str
