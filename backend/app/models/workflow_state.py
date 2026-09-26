from enum import Enum


class WorkflowState(Enum):
    CREATED = "CREATED"
    UPLOADED = "UPLOADED"
    ANALYZED = "ANALYZED"
    PLAN_READY = "PLAN_READY"
    CLEANED = "CLEANED"
    PROFILED = "PROFILED"
    KPI_READY = "KPI_READY"
    EXPORTED = "EXPORTED"