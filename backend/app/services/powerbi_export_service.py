import re
from typing import Any, Optional

from app.common.powerbi_names import m_string, powerbi_table_name
from app.models.dataset_profile import DatasetProfile
from app.models.kpi_report import KPIReport
from app.models.relationship_models import RelationshipReport

_NUMERIC = ("INTEGER", "FLOAT", "DECIMAL")
_DATES = ("DATE", "DATETIME")
_STEM = re.compile(r"\.(csv|tsv|txt|xlsx|xlsm|xls)$", re.IGNORECASE)


def _ptype(column: Any) -> str:
    value = column.physical_type
    return (value.value if hasattr(value, "value") else str(value)).upper()


def _number(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.4g}"


def _measure_name(kpi_name: str) -> str:
    return kpi_name.replace(" ", "_").replace("(", "").replace(")", "").replace("%", "Pct")


class PowerBIExportService:
    """
    Service generating Power BI Desktop assets, DAX measure scripts,
    Tabular Model BIM schemas, and Power Query M transformation code.
    """

    @staticmethod
    def generate_dax_script(kpi_report: KPIReport, dataset_name: str = "Dataset") -> str:
        """
        Generate a .dax script with one measure per KPI, ready to paste into
        Power BI Desktop (Modeling > New measure) or Tabular Editor.
        """
        lines = [
            "// ===========================================================================",
            "// PowerPilot Generated DAX Measures Script",
            f"// Dataset: {dataset_name}",
            f"// Table:   {powerbi_table_name(dataset_name)}",
            f"// Domain: {kpi_report.domain.value.upper() if hasattr(kpi_report.domain, 'value') else str(kpi_report.domain).upper()}",
            f"// Total Recommended Measures: {kpi_report.total_kpis_recommended}",
            "// ===========================================================================",
            "",
        ]

        all_kpis = list(kpi_report.primary_kpis) + list(kpi_report.secondary_kpis)
        for kpi in all_kpis:
            lines.append(f"// Measure: {kpi.name}")
            lines.append(f"// Priority: {kpi.priority.value if hasattr(kpi.priority, 'value') else str(kpi.priority)}")
            lines.append(f"// Confidence: {(kpi.confidence * 100):.0f}%")
            if kpi.computed_value is not None:
                lines.append(f"// Verified value: {_number(kpi.computed_value)} (computed on the cleaned dataset)")
            if kpi.target_threshold:
                lines.append(f"// Baseline: {kpi.target_threshold}")
            if kpi.business_impact:
                lines.append(f"// Impact: {kpi.business_impact}")

            if kpi.formula:
                lines.append(f"{_measure_name(kpi.name)} = {kpi.formula}")
            else:
                lines.append("// (no formula could be derived from this dataset's columns)")
            lines.append("")

        if kpi_report.rejected_kpis:
            lines.append("// ---------------------------------------------------------------------------")
            lines.append("// Rejected KPIs: failed verification against this dataset, so NOT exported as measures")
            for kpi in kpi_report.rejected_kpis:
                lines.append(f"//   - {kpi.name}: {kpi.verification_note}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_migrated_dax_script(plan: Any, filename: str, source_description: str) -> str:
        """A .dax script holding only the measures proven from a legacy report (none that failed or were guessed)."""
        proven = sum(len(m.cell_ids) for m in plan.measures)
        lines = [
            "// ===========================================================================",
            "// PowerPilot - measures migrated from a legacy report",
            f"// Report:  {filename}",
            f"// Table:   {plan.table}",
            f"// Proven:  {proven} number(s) in the report are reproduced exactly by the measures below.",
            f"// Basis:   {source_description}",
            "// Numbers PowerPilot could not reproduce, or could not tell apart, are NOT included.",
            "// ===========================================================================",
            "",
        ]
        for measure in plan.measures:
            lines.append(f"// Measure: {measure.name}  ({measure.kind}; covers {len(measure.cell_ids)} number(s): {', '.join(measure.cell_ids[:6])}{'...' if len(measure.cell_ids) > 6 else ''})")
            for note in measure.notes:
                lines.append(f"// {note}")
            lines.append(f"{measure.name} = {measure.dax}")
            lines.append("")
        if not plan.measures:
            lines.append("// No number in the report could be proven, so there is nothing to export.")
        return "\n".join(lines)

    @staticmethod
    def generate_tabular_model_bim(
        dataset_profile: DatasetProfile,
        kpi_report: Optional[KPIReport] = None,
        relationship_report: Optional[RelationshipReport] = None,
        extra_measures: Optional[list[dict[str, Any]]] = None,
        extra_annotations: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Generate a Tabular Model .bim: one Import-mode table whose partition loads
        the CSV through Power Query, with the KPI measures attached.

        ``extra_measures`` (name, expression, description, optionally displayFolder) are added as given;
        the migration export uses them for the measures proven from a legacy report.
        """
        tbl_name = powerbi_table_name(dataset_profile.dataset_name)

        columns_bim = []
        key_assigned = False
        for col in dataset_profile.columns:
            ptype = _ptype(col)
            if ptype in _NUMERIC:
                data_type = "double" if ptype in ("FLOAT", "DECIMAL") else "int64"
            elif ptype in _DATES:
                data_type = "dateTime"
            elif ptype == "BOOLEAN":
                data_type = "boolean"
            else:
                data_type = "string"

            column: dict[str, Any] = {
                "name": col.name,
                "dataType": data_type,
                "sourceColumn": col.name,
                "summarizeBy": "sum" if ptype in _NUMERIC and not col.identifier else "none",
            }
            # A table may have exactly one key column, and it must hold unique values.
            if col.identifier and col.unique and not key_assigned:
                column["isKey"] = True
                key_assigned = True
            columns_bim.append(column)

        measures_bim = []
        if kpi_report:
            for kpi in list(kpi_report.primary_kpis) + list(kpi_report.secondary_kpis):
                if not kpi.formula:
                    continue
                measures_bim.append(
                    {
                        "name": _measure_name(kpi.name),
                        "expression": kpi.formula,
                        "description": kpi.reason,
                    }
                )

        measures_bim.extend(extra_measures or [])
        m_lines = PowerBIExportService.generate_power_query_m(dataset_profile).splitlines()

        annotations = []
        if relationship_report and relationship_report.all_relationships:
            # A single flat table cannot hold relationships (Power BI rejects a table related
            # to itself), so they are kept as a note rather than emitted as invalid joins.
            found = "; ".join(
                f"{rel.source_column} -> {rel.target_column} ({rel.cardinality})"
                for rel in relationship_report.all_relationships
            )
            annotations.append({"name": "PowerPilot_DetectedRelationships", "value": found})

        annotations.extend(extra_annotations or [])

        if kpi_report and kpi_report.rejected_kpis:
            rejected = "; ".join(f"{k.name}: {k.verification_note}" for k in kpi_report.rejected_kpis)
            annotations.append({"name": "PowerPilot_RejectedKPIs", "value": rejected})

        return {
            "name": f"PowerPilot_{tbl_name}_Model",
            "compatibilityLevel": 1500,
            "model": {
                "culture": "en-US",
                "defaultPowerBIDataSourceVersion": "powerBI_V3",
                "tables": [
                    {
                        "name": tbl_name,
                        "columns": columns_bim,
                        "partitions": [
                            {
                                "name": tbl_name,
                                "mode": "import",
                                "source": {"type": "m", "expression": m_lines},
                            }
                        ],
                        "measures": measures_bim,
                    }
                ],
                "relationships": [],
                "annotations": annotations,
            },
        }

    @staticmethod
    def generate_power_query_m(
        dataset_profile: DatasetProfile,
        file_path: Optional[str] = None,
        delimiter: str = ",",
        encoding: int = 65001,
    ) -> str:
        """
        Generate Power Query M that loads the CSV and casts every column to its detected type.

        The default path is a visible placeholder to edit, never a real user's folder.
        """
        stem = _STEM.sub("", dataset_profile.dataset_name)
        path = file_path or f"C:\\path\\to\\Cleaned_{stem}.csv"

        casts = []
        typed_columns = []
        for col in dataset_profile.columns:
            ptype = _ptype(col)
            m_type = "type text"
            if ptype == "INTEGER":
                # Cleaning fills gaps with a median, which can be fractional; Int64 would round it.
                m_type = "Int64.Type" if col.missing_count == 0 else "type number"
            elif ptype in ("FLOAT", "DECIMAL"):
                m_type = "type number"
            elif ptype in _DATES:
                m_type = "type datetime"
            elif ptype == "BOOLEAN":
                m_type = "type logical"
            casts.append(f"{{{m_string(col.name)}, {m_type}}}")
            if m_type != "type text":
                typed_columns.append(col.name)

        steps = [
            f"FilePath = {m_string(path)}",
            f"Source = Csv.Document(File.Contents(FilePath), [Delimiter={m_string(delimiter)}, "
            f"Columns={dataset_profile.total_columns}, Encoding={encoding}, QuoteStyle=QuoteStyle.Csv])",
            '#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])',
            f'#"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{", ".join(casts)}}})',
        ]
        last_step = '#"Changed Type"'
        if typed_columns:
            # A column can be detected as numeric/date while a few cells (ranges, units, junk) are
            # not; the cast turns those into error cells, so blank them instead of failing the load.
            blanks = ", ".join(f"{{{m_string(name)}, null}}" for name in typed_columns)
            steps.append(f'#"Replaced Errors" = Table.ReplaceErrorValues(#"Changed Type", {{{blanks}}})')
            last_step = '#"Replaced Errors"'

        header = (
            "// PowerPilot Generated Power Query (M) Script\n"
            "// 1. In PowerPilot's Export Center, download the Cleaned Dataset (CSV).\n"
            "// 2. Set FilePath below to where you saved it.\n"
            f"// 3. Name this query {powerbi_table_name(dataset_profile.dataset_name)} so the exported DAX measures resolve.\n"
        )
        body = ",\n".join(f"    {step}" for step in steps)
        return f"{header}let\n{body}\nin\n    {last_step}\n"
