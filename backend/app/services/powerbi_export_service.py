import json
from typing import Any, Optional

from app.models.dataset_profile import DatasetProfile
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport


class PowerBIExportService:
    """
    Service generating Power BI Desktop assets, DAX measure scripts,
    Tabular Model BIM schemas, and Power Query M transformation code.
    """

    @staticmethod
    def generate_dax_script(kpi_report: KPIReport, dataset_name: str = "Dataset") -> str:
        """
        Generate a formatted, executable .dax script containing all KPI measures.
        """
        lines = [
            f"// ===========================================================================",
            f"// PowerPilot Generated DAX Measures Script",
            f"// Dataset: {dataset_name}",
            f"// Domain: {kpi_report.domain.value.upper() if hasattr(kpi_report.domain, 'value') else str(kpi_report.domain).upper()}",
            f"// Total Recommended Measures: {kpi_report.total_kpis_recommended}",
            f"// ===========================================================================",
            "",
        ]

        all_kpis = list(kpi_report.primary_kpis) + list(kpi_report.secondary_kpis)
        for kpi in all_kpis:
            lines.append(f"// Measure: {kpi.name}")
            lines.append(f"// Priority: {kpi.priority.value if hasattr(kpi.priority, 'value') else str(kpi.priority)}")
            lines.append(f"// Confidence: {(kpi.confidence * 100):.0f}%")
            if kpi.target_threshold:
                lines.append(f"// Benchmark Target: {kpi.target_threshold}")
            if kpi.business_impact:
                lines.append(f"// Impact: {kpi.business_impact}")
            
            clean_name = kpi.name.replace(" ", "_").replace("(", "").replace(")", "").replace("%", "Pct")
            formula = kpi.formula if kpi.formula else f"SUM('{dataset_name}'[{clean_name}])"
            lines.append(f"{clean_name} = {formula}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_tabular_model_bim(
        dataset_profile: DatasetProfile,
        kpi_report: Optional[KPIReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
    ) -> dict[str, Any]:
        """
        Generate a valid Microsoft Analysis Services Tabular Model .bim JSON schema.
        """
        tbl_name = dataset_profile.dataset_name.replace(".csv", "").replace(" ", "_")

        columns_bim = []
        for col in dataset_profile.columns:
            ptype_str = col.physical_type.value.upper() if hasattr(col.physical_type, "value") else str(col.physical_type).upper()
            data_type = "String"
            if ptype_str in ("INTEGER", "FLOAT", "DECIMAL"):
                data_type = "Double" if ptype_str == "FLOAT" else "Int64"
            elif ptype_str in ("DATE", "DATETIME"):
                data_type = "DateTime"
            elif ptype_str == "BOOLEAN":
                data_type = "Boolean"

            columns_bim.append(
                {
                    "name": col.name,
                    "dataType": data_type,
                    "sourceColumn": col.name,
                    "isKey": col.identifier,
                    "summarizeBy": "none" if col.identifier else "default",
                }
            )

        measures_bim = []
        if kpi_report:
            all_kpis = list(kpi_report.primary_kpis) + list(kpi_report.secondary_kpis)
            for kpi in all_kpis:
                clean_name = kpi.name.replace(" ", "_").replace("(", "").replace(")", "").replace("%", "Pct")
                measures_bim.append(
                    {
                        "name": clean_name,
                        "expression": kpi.formula if kpi.formula else f"SUM('{tbl_name}'[{clean_name}])",
                        "description": kpi.reason,
                    }
                )

        relationships_bim = []
        if relationship_report:
            for rel in relationship_report.all_relationships:
                relationships_bim.append(
                    {
                        "name": f"rel_{rel.source_column}_{rel.target_column}",
                        "fromTable": tbl_name,
                        "fromColumn": rel.source_column,
                        "toTable": tbl_name,
                        "toColumn": rel.target_column,
                        "cardinality": rel.cardinality.lower(),
                        "isActive": True,
                    }
                )

        bim_structure = {
            "name": f"PowerPilot_{tbl_name}_Model",
            "compatibilityLevel": 1500,
            "model": {
                "culture": "en-US",
                "tables": [
                    {
                        "name": tbl_name,
                        "columns": columns_bim,
                        "measures": measures_bim,
                    }
                ],
                "relationships": relationships_bim,
            },
        }

        return bim_structure

    @staticmethod
    def generate_power_query_m(dataset_profile: DatasetProfile) -> str:
        """
        Generate Power Query M code for dataset importing and column type casting.
        """
        tbl_name = dataset_profile.dataset_name.replace(".csv", "")

        type_transformations = []
        for col in dataset_profile.columns:
            ptype_str = col.physical_type.value.upper() if hasattr(col.physical_type, "value") else str(col.physical_type).upper()
            m_type = "type text"
            if ptype_str in ("INTEGER", "DECIMAL"):
                m_type = "Int64.Type"
            elif ptype_str == "FLOAT":
                m_type = "type number"
            elif ptype_str in ("DATE", "DATETIME"):
                m_type = "type datetime"
            elif ptype_str == "BOOLEAN":
                m_type = "type logical"
            
            type_transformations.append(f'{{"{col.name}", {m_type}}}')

        m_types_str = ", ".join(type_transformations)

        m_code = f"""// PowerPilot Generated Power Query (M) Script
// NOTE: Change the file path below to match where your CSV file is stored on your computer.
let
    Source = Csv.Document(File.Contents("C:\\Users\\Admin\\Downloads\\{dataset_profile.dataset_name}"), [Delimiter=",", Columns={dataset_profile.total_columns}, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{m_types_str}}})
in
    #"Changed Type"
"""
        return m_code
