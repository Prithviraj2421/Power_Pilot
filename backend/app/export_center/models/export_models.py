from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from app.common.metric_filter import SmartMetricFilter


class ExportFormat(str, Enum):
    CLEANED_CSV = "CLEANED_CSV"
    CLEANED_EXCEL = "CLEANED_EXCEL"
    EXECUTIVE_PDF = "EXECUTIVE_PDF"
    EXECUTIVE_DOCX = "EXECUTIVE_DOCX"
    INTERACTIVE_HTML = "INTERACTIVE_HTML"
    MASTER_JSON = "MASTER_JSON"
    DATA_DICTIONARY = "DATA_DICTIONARY"
    DAX_SCRIPT = "DAX_SCRIPT"
    DASHBOARD_LAYOUT = "DASHBOARD_LAYOUT"
    AUDIT_REPORT = "AUDIT_REPORT"


class ReportTheme(str, Enum):
    EXECUTIVE = "EXECUTIVE"
    TECHNICAL = "TECHNICAL"
    MINIMAL = "MINIMAL"
    DARK = "DARK"


@dataclass(slots=True)
class BrandingConfig:
    company_name: str = "Enterprise Organization"
    logo_url: Optional[str] = None
    prepared_by: str = "PowerPilot AI Platform"
    prepared_for: str = "Executive Leadership Team"
    theme: ReportTheme = ReportTheme.EXECUTIVE
    confidential_watermark: bool = True
    report_version: str = "v1.0.0 Enterprise"


@dataclass(slots=True, frozen=True)
class PageBudgetConfig:
    min_pages: int
    max_pages: int
    target_pages: int
    dataset_scale: str  # 'SMALL', 'MEDIUM', 'LARGE'
    include_stats: bool
    include_kpi_catalog: bool
    include_decisions: bool
    include_copilot: bool
    include_appendix: bool


@dataclass(slots=True, frozen=True)
class CleaningAuditEntry:
    operation: str
    rows_affected: int
    columns_affected: int
    status: str
    execution_time_ms: float
    description: str


@dataclass(slots=True, frozen=True)
class BusinessRuleResult:
    rule_name: str
    status: str  # 'PASSED', 'WARNING', 'FAILED'
    affected_rows: int
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    recommendation: str


@dataclass(slots=True, frozen=True)
class ExportHistoryEntry:
    entry_id: str
    dataset_name: str
    export_format: ExportFormat
    file_size_bytes: int
    duration_ms: float
    timestamp: str
    status: str
    file_path: Optional[str] = None


@dataclass(slots=True)
class EmailDistributionPayload:
    recipients: list[str]
    subject: str
    body_message: str
    attachments: list[ExportFormat] = field(default_factory=list)
    branding: BrandingConfig = field(default_factory=BrandingConfig)


# SmartMetricFilter moved to app.common.metric_filter so the intelligence engines
# can share it without app.intelligence depending on app.export_center. Re-exported
# here so existing importers keep working.
__all__ = [
    "BrandingConfig",
    "BusinessRuleResult",
    "CleaningAuditEntry",
    "EmailDistributionPayload",
    "ExportFormat",
    "ExportHistoryEntry",
    "PageBudgetConfig",
    "ReportTheme",
    "SmartMetricFilter",
]
