import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.common.metric_filter import SmartMetricFilter
from app.export_center.builders.magazine_flowables import ExecutiveGaugeCard, HeroKPICard
from app.export_center.models.export_models import BrandingConfig
from app.models.master_intelligence_result import MasterIntelligenceResult


def _enum_value(value) -> str:
    """Render a StrEnum member or a plain string uniformly, upper-cased."""
    return str(getattr(value, "value", value)).upper()


class MagazineCanvas(canvas.Canvas):
    """
    Two-pass canvas rendering an asymmetric Executive Magazine layout:
    - Cover page: Full McKinsey dark navy background with diagonal confidential watermark.
    - Inner pages: Top category header tabs, subtle divider lines, running bottom footer,
      and "Page X of Y" pagination.

    The category label shown per page is driven by story-side bookmarks
    (``self._category_by_page``) rather than a fixed page-number table, so it
    stays correct regardless of how many pages a section actually takes --
    the previous version hardcoded page 2 = summary, page 3 = schema, etc,
    which silently mislabeled every page once a section grew past one page.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.category_by_page: dict[int, str] = {}
        self._current_category = "EXECUTIVE INTELLIGENCE REPORT"

    def showPage(self):
        self.category_by_page[self._pageNumber] = self._current_category
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_magazine_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_magazine_decorations(self, page_count: int):
        self.saveState()

        if self._pageNumber == 1:
            self.setFillColor(colors.HexColor("#0B0F19"))
            self.rect(0, 0, 612, 792, fill=1, stroke=0)

            self.setFillColor(colors.HexColor("#3B82F6"))
            self.rect(0, 780, 612, 12, fill=1, stroke=0)

            self.setFont("Helvetica-Bold", 44)
            self.setFillColor(colors.HexColor("#111827"))
            self.saveState()
            self.translate(306, 396)
            self.rotate(45)
            self.drawCentredString(0, 0, "CONFIDENTIAL BOARD REPORT")
            self.restoreState()

            self.restoreState()
            return

        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1E3A8A"))

        cat_text = self.category_by_page.get(self._pageNumber, "EXECUTIVE INTELLIGENCE REPORT")
        self.drawString(36, 765, f"POWERPILOT MAGAZINE | {cat_text}")
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.75)
        self.line(36, 755, 612 - 36, 755)

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))
        self.drawString(36, 20, "CONFIDENTIAL & PROPRIETARY — FOR BOARD DIRECTORS ONLY")

        footer_pg = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 36, 20, footer_pg)

        self.restoreState()


class _CategoryMarker(Flowable):
    """A zero-size flowable that stamps the running header for every page it
    (or the content after it) lands on.

    Platypus flowables don't know their own page number in advance -- a section
    can run one page or several depending on how much real content it has, so a
    fixed {page_number: label} table (the previous version's approach) silently
    mislabels the header the moment a section's length changes. This instead
    writes the label onto the live canvas the moment this section starts
    drawing; MagazineCanvas.showPage() snapshots whatever label is current at
    each page break, so every page gets the label that was actually true for it.
    """

    def __init__(self, label: str) -> None:
        self._label = label

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        self.canv._current_category = self._label


class PdfExportBuilder:
    """
    Master Builder generating McKinsey / Apple Executive Magazine PDF Reports.

    Every figure below is read from the computed analysis. Earlier revisions of
    this builder hardcoded several numbers that looked computed but weren't --
    a flat "98.4% HIGH" confidence regardless of the dataset, fixed 98.5 / 96.2 /
    99.1 quality sub-scores, and a cleaning summary that read attributes
    (`missing_values_handled`, `duplicates_removed`) that don't exist on
    DataPreparationReport and silently fell back to `0`. None of that survives
    here: a number appears only if the pipeline actually produced it.
    """

    # -- styles ---------------------------------------------------------

    @classmethod
    def _styles(cls) -> dict[str, ParagraphStyle]:
        base = getSampleStyleSheet()
        return {
            "cover_title": ParagraphStyle(
                "CoverTitle", parent=base["Title"], fontName="Helvetica-Bold",
                fontSize=28, leading=34, textColor=colors.white, alignment=0,
            ),
            "h1": ParagraphStyle(
                "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
                fontSize=18, leading=22, textColor=colors.HexColor("#1E3A8A"),
                spaceBefore=10, spaceAfter=6,
            ),
            "h2": ParagraphStyle(
                "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
                fontSize=12.5, leading=16, textColor=colors.HexColor("#0F172A"),
                spaceBefore=14, spaceAfter=6,
            ),
            "body": ParagraphStyle(
                "Body", parent=base["Normal"], fontName="Helvetica",
                fontSize=9.5, leading=14, textColor=colors.HexColor("#334155"),
                spaceAfter=8,
            ),
            "callout": ParagraphStyle(
                "Callout", parent=base["Normal"], fontName="Helvetica-Oblique",
                fontSize=9.5, leading=14, textColor=colors.HexColor("#1E3A8A"),
                leftIndent=10, spaceAfter=6,
            ),
            "bullet": ParagraphStyle(
                "Bullet", parent=base["Normal"], fontName="Helvetica",
                fontSize=9, leading=13.5, textColor=colors.HexColor("#334155"),
                leftIndent=12, bulletIndent=0, spaceAfter=7,
            ),
            "mono": ParagraphStyle(
                "Mono", parent=base["Normal"], fontName="Courier",
                fontSize=8.5, leading=12, textColor=colors.HexColor("#1E3A8A"),
                leftIndent=12, spaceAfter=10, backColor=colors.HexColor("#F0F9FF"),
                borderPadding=6,
            ),
            "small_grey": ParagraphStyle(
                "SmallGrey", parent=base["Normal"], fontName="Helvetica",
                fontSize=8, leading=11.5, textColor=colors.HexColor("#6B7280"),
            ),
        }

    @staticmethod
    def _severity_color(severity: str) -> str:
        return {
            "CRITICAL": "#DC2626", "HIGH": "#EA580C",
            "MEDIUM": "#D97706", "LOW": "#65A30D",
        }.get(severity.upper(), "#6B7280")

    @classmethod
    def _table(cls, data: list[list[str]], col_widths: list[float]) -> Table:
        # Plain strings don't wrap in a ReportLab Table -- a value like
        # "DUPLICATE_IDENTIFIER" or "STANDARDIZE_DATES_ISO8601" that doesn't
        # fit the column width overflows and visibly overlaps the next
        # column's text instead of wrapping onto a second line. Wrapping every
        # body cell in a Paragraph gives it real word-wrap.
        cell_style = ParagraphStyle(
            "TableCell", fontName="Helvetica", fontSize=8, leading=10.5,
            textColor=colors.HexColor("#334155"), wordWrap="CJK",
        )
        header_style = ParagraphStyle(
            "TableHeader", fontName="Helvetica-Bold", fontSize=8.5,
            leading=11, textColor=colors.whitesmoke,
        )
        wrapped = [[Paragraph(str(cell), header_style) for cell in data[0]]]
        for row in data[1:]:
            wrapped.append([Paragraph(str(cell), cell_style) for cell in row])

        table = Table(wrapped, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ]
            )
        )
        return table

    # -- section builders -------------------------------------------------

    @classmethod
    def _build_cover(cls, story: list, result: MasterIntelligenceResult, branding: BrandingConfig, st: dict) -> None:
        profile = result.dataset_profile
        q_report = result.quality_report
        overall_score = q_report.overall_score if q_report else 0.0
        grade = q_report.grade.value if q_report else "N/A"
        domain = _enum_value(profile.detected_domain)
        confidence_pct = profile.domain_confidence * 100

        story.append(Spacer(1, 80))
        story.append(Paragraph(f"<b>{branding.company_name.upper()}</b>", st["cover_title"]))
        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                f"<font color='#3B82F6' size='14'><b>EXECUTIVE INTELLIGENCE REPORT</b></font><br/>"
                f"<font color='#9CA3AF' size='10'>Dataset: {profile.dataset_name} | Domain: {domain} | {branding.report_version}</font>",
                ParagraphStyle("CoverSub", parent=st["body"], leading=18, textColor=colors.white),
            )
        )
        story.append(Spacer(1, 40))

        # A dataset the classifier could not confidently place shows that
        # honestly instead of a number that would otherwise read as 0% quality.
        confidence_label = f"{confidence_pct:.0f}% Confidence" if domain != "UNKNOWN" else "Not classified"
        story.append(
            Table(
                [[
                    HeroKPICard("QUALITY GRADE", f"Grade {grade}", f"{overall_score:.1f}% Score",
                                accent_color="#10B981", bg_color="#111827", width=160, height=75),
                    HeroKPICard("DOMAIN", domain, confidence_label,
                                accent_color="#3B82F6", bg_color="#111827", width=160, height=75),
                    HeroKPICard("TOTAL ROWS", f"{profile.total_rows:,}", f"{profile.total_columns} Columns",
                                accent_color="#8B5CF6", bg_color="#111827", width=160, height=75),
                ]],
                colWidths=[175, 175, 175],
            )
        )
        story.append(Spacer(1, 60))
        story.append(
            Paragraph(
                f"<font color='#9CA3AF' size='9'>"
                f"<b>PREPARED FOR:</b> {branding.prepared_for}<br/>"
                f"<b>PREPARED BY:</b> {branding.prepared_by}<br/>"
                f"<b>CLASSIFICATION:</b> BOARD CONFIDENTIAL &amp; PROPRIETARY"
                f"</font>",
                st["body"],
            )
        )
        story.append(PageBreak())

    @classmethod
    def _build_briefing(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        profile = result.dataset_profile
        q_report = result.quality_report
        overall_score = q_report.overall_score if q_report else 0.0
        grade = q_report.grade.value if q_report else "N/A"
        domain = _enum_value(profile.detected_domain)

        story.append(Paragraph("Executive Briefing", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        kpi_count = len(result.kpi_report.primary_kpis) if result.kpi_report else 0
        decision_count = len(result.decision_report.primary_decisions) if result.decision_report else 0
        insight_count = len(result.insight_report.insights) if result.insight_report else 0

        story.append(
            Table(
                [[
                    HeroKPICard("OVERALL QUALITY", f"{overall_score:.1f}%", f"Grade {grade}", accent_color="#10B981", width=165, height=75),
                    HeroKPICard("PRIMARY KPIS", str(kpi_count), "Recommended DAX", accent_color="#3B82F6", width=165, height=75),
                    HeroKPICard("STRATEGIC ACTIONS", str(decision_count), "High Confidence", accent_color="#F59E0B", width=165, height=75),
                ]],
                colWidths=[175, 175, 175],
            )
        )
        story.append(Spacer(1, 16))

        # Real narrative from the Insight Engine's executive summary, rather
        # than four generic template sentences describing pipeline mechanics.
        summary = result.insight_report.executive_summary if result.insight_report else None
        if summary and summary.overview:
            story.append(Paragraph("<b>OVERVIEW</b>", st["h2"]))
            story.append(Paragraph(summary.overview, st["body"]))
            if summary.data_quality_summary:
                story.append(Paragraph(summary.data_quality_summary, st["body"]))

            for heading, items in (
                ("KEY FINDINGS", summary.major_findings),
                ("TOP RISKS", summary.top_risks),
                ("OPPORTUNITIES", summary.key_opportunities),
                ("RECOMMENDED ACTIONS", summary.recommended_actions),
            ):
                if items:
                    story.append(Paragraph(f"<b>{heading}</b>", st["h2"]))
                    for item in items:
                        story.append(Paragraph(f"&bull; {item}", st["bullet"]))
        else:
            story.append(
                Paragraph(
                    f"'{profile.dataset_name}' was evaluated across {profile.total_rows:,} rows and "
                    f"{profile.total_columns} columns. {kpi_count} KPI(s), {decision_count} strategic "
                    f"decision(s) and {insight_count} insight(s) were generated for the {domain} domain.",
                    st["body"],
                )
            )
        story.append(PageBreak())

    @classmethod
    def _build_schema(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        profile = result.dataset_profile
        story.append(Paragraph("Dataset Schema", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=12))

        business_cols = SmartMetricFilter.filter_business_columns([c.name for c in profile.columns])
        id_cols = [c.name for c in profile.columns if SmartMetricFilter.is_identifier_column(c.name)]

        story.append(
            Paragraph(
                f"<b>{len(business_cols)}</b> business metric column(s) identified, excluding "
                f"<b>{len(id_cols)}</b> technical identifier column(s). Full schema for all "
                f"<b>{len(profile.columns)}</b> columns follows.",
                st["body"],
            )
        )

        # Every column, not the first 10 -- a table that runs long splits
        # across pages on its own (repeatRows=1 keeps the header on each).
        schema_data = [["Column", "Type", "Semantic", "Nullable", "Unique", "Sample Values"]]
        for col in profile.columns:
            semantic = _enum_value(col.semantic_type) if col.semantic_type else "UNCLASSIFIED"
            samples = ", ".join(str(s) for s in col.sample_values[:2])
            schema_data.append([
                col.name,
                _enum_value(col.physical_type),
                semantic,
                "Yes" if col.nullable else "No",
                "Yes" if col.unique else "No",
                samples,
            ])
        story.append(cls._table(schema_data, col_widths=[95, 65, 80, 48, 42, 200]))
        story.append(PageBreak())

    @classmethod
    def _build_quality(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        q_report = result.quality_report
        story.append(Paragraph("Data Quality Audit", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        if not q_report:
            story.append(Paragraph("No quality assessment is available for this dataset.", st["body"]))
            story.append(PageBreak())
            return

        # Real per-dimension averages across every column's ColumnQualityScore
        # -- the fixed 98.5 / 96.2 / 99.1 this replaced never changed no matter
        # what was actually in the dataset.
        scores = q_report.column_scores
        avg = lambda attr: (sum(getattr(s, attr) for s in scores) / len(scores)) if scores else q_report.overall_score

        story.append(Paragraph("<b>Quality Scorecard</b> (averaged across all columns)", st["h2"]))
        story.append(ExecutiveGaugeCard("Overall Quality Score", q_report.overall_score, width=530, height=28))
        story.append(Spacer(1, 8))
        story.append(ExecutiveGaugeCard("Completeness", avg("completeness"), width=530, height=28))
        story.append(Spacer(1, 8))
        story.append(ExecutiveGaugeCard("Consistency", avg("consistency"), width=530, height=28))
        story.append(Spacer(1, 8))
        story.append(ExecutiveGaugeCard("Validity", avg("validity"), width=530, height=28))
        story.append(Spacer(1, 8))
        story.append(ExecutiveGaugeCard("Uniqueness", avg("uniqueness"), width=530, height=28))
        story.append(Spacer(1, 16))
        story.append(Paragraph(f"<b>Verdict:</b> {q_report.grade_explanation}", st["callout"]))

        # The actual detected issues, not a hardcoded "0 -> 0".
        if q_report.detected_issues:
            story.append(Paragraph(f"<b>Detected Issues ({q_report.total_issues_count})</b>", st["h2"]))
            issue_data = [["Column", "Issue", "Affected", "Severity", "Recommended Treatment"]]
            for issue in q_report.detected_issues:
                issue_data.append([
                    issue.column,
                    issue.issue_type,
                    f"{issue.affected_count} ({issue.affected_percentage:.1f}%)",
                    _enum_value(issue.severity),
                    issue.recommended_treatment,
                ])
            story.append(cls._table(issue_data, col_widths=[75, 90, 70, 60, 235]))
        else:
            story.append(Paragraph("No data quality issues were detected.", st["body"]))
        story.append(PageBreak())

    @classmethod
    def _build_cleaning(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        prep = result.preparation_report
        story.append(Paragraph("Cleaning Audit Trail", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        if not prep:
            story.append(Paragraph("No preparation report is available for this dataset.", st["body"]))
            story.append(PageBreak())
            return

        summary_data = [
            ["Metric", "Value"],
            ["Rows before cleaning", f"{prep.original_rows:,}"],
            ["Rows after cleaning", f"{prep.cleaned_rows:,}"],
            ["Rows removed", f"{prep.rows_removed:,}"],
            ["Cleaning actions performed", str(prep.total_actions_count)],
        ]
        story.append(cls._table(summary_data, col_widths=[250, 280]))
        story.append(Spacer(1, 14))

        if prep.audit_trail:
            story.append(Paragraph("<b>Actions Taken</b>", st["h2"]))
            trail_data = [["Column", "Action", "Before", "After", "Rows Affected"]]
            for entry in prep.audit_trail:
                trail_data.append([
                    entry.column_name, entry.action_type,
                    entry.before_sample, entry.after_sample,
                    str(entry.rows_affected),
                ])
            story.append(cls._table(trail_data, col_widths=[85, 110, 120, 120, 95]))

        if prep.summary_notes:
            story.append(Spacer(1, 12))
            for note in prep.summary_notes:
                story.append(Paragraph(f"&bull; {note}", st["bullet"]))
        story.append(PageBreak())

    @classmethod
    def _build_intelligence(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        """Trends, correlations and business anomalies. Absent from the report
        entirely before this -- the richest part of the analysis went unread."""
        report = result.data_intelligence_report
        story.append(Paragraph("Statistical Intelligence", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        if not report or not (report.trends or report.correlations or report.business_anomalies):
            story.append(Paragraph("No statistical findings were generated for this dataset.", st["body"]))
            story.append(PageBreak())
            return

        if report.trends:
            story.append(Paragraph("<b>Trends</b>", st["h2"]))
            for t in report.trends:
                story.append(
                    Paragraph(
                        f"&bull; <b>{t.metric_column}</b> is {t.direction} over {t.time_column} "
                        f"({t.growth_rate_pct:+.1f}% change, {t.confidence * 100:.0f}% confidence)",
                        st["bullet"],
                    )
                )

        if report.correlations:
            story.append(Paragraph("<b>Correlations</b>", st["h2"]))
            for c in report.correlations:
                story.append(
                    Paragraph(
                        f"&bull; <b>{c.column_a}</b> vs <b>{c.column_b}</b>: {c.coefficient:+.2f} "
                        f"({c.correlation_type.replace('_', ' ')})",
                        st["bullet"],
                    )
                )

        if report.business_anomalies:
            story.append(Paragraph("<b>Business Anomalies</b>", st["h2"]))
            for a in report.business_anomalies:
                color = cls._severity_color(a.severity)
                story.append(
                    Paragraph(
                        f"&bull; <font color='{color}'><b>[{_enum_value(a.severity)}]</b></font> "
                        f"<b>{a.anomaly_title}</b> on {a.affected_entity}: {a.metric_name} observed "
                        f"{a.observed_value:,.2f} vs expected {a.expected_value:,.2f} "
                        f"({a.deviation_pct:+.1f}%)",
                        st["bullet"],
                    )
                )
        story.append(PageBreak())

    @classmethod
    def _build_insights(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        report = result.insight_report
        story.append(Paragraph("Executive Insights", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        if not report or not report.insights:
            story.append(Paragraph("No insights were generated for this dataset.", st["body"]))
            story.append(PageBreak())
            return

        # Highest severity first, so the reader sees what matters most.
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        ranked = sorted(report.insights, key=lambda i: order.get(i.severity.upper(), 4))

        for insight in ranked:
            color = cls._severity_color(insight.severity)
            story.append(
                KeepTogether(
                    [
                        Paragraph(
                            f"<font color='{color}'><b>[{insight.severity.upper()}]</b></font> "
                            f"<b>{insight.title}</b> <font color='#9CA3AF' size='8'>({insight.category})</font>",
                            st["h2"],
                        ),
                        Paragraph(insight.description, st["body"]),
                        Paragraph(f"<i>Business impact:</i> {insight.business_impact}", st["callout"]),
                        Paragraph(
                            f"<i>Recommendation:</i> {insight.recommendation.action} "
                            f"({insight.recommendation.target_area})",
                            st["callout"],
                        ),
                    ]
                )
            )
        story.append(PageBreak())

    @classmethod
    def _build_relationships(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        report = result.relationship_report
        story.append(Paragraph("Entity Relationships", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=14))

        if not report or not report.all_relationships:
            story.append(Paragraph("No structural relationships were identified in this dataset.", st["body"]))
            story.append(PageBreak())
            return

        rel_data = [["Source", "Target", "Type", "Cardinality", "Confidence"]]
        for r in report.all_relationships:
            rel_data.append([
                r.source_column, r.target_column,
                r.relationship_type.replace("_", " "),
                r.cardinality.replace("_", " "),
                f"{r.confidence * 100:.0f}%",
            ])
        story.append(cls._table(rel_data, col_widths=[105, 105, 120, 105, 95]))
        story.append(PageBreak())

    @classmethod
    def _build_kpis(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        story.append(Paragraph("DAX KPI Measures", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=12))

        report = result.kpi_report
        if not report or not (report.primary_kpis or report.secondary_kpis):
            story.append(Paragraph("No KPIs were recommended for this dataset.", st["body"]))
            story.append(PageBreak())
            return

        for label, kpis in (("Primary KPIs", report.primary_kpis), ("Secondary KPIs", report.secondary_kpis)):
            if not kpis:
                continue
            story.append(Paragraph(f"<b>{label}</b>", st["h2"]))
            for kpi in kpis:  # every KPI, not a hardcoded top-5
                priority = _enum_value(kpi.priority)
                story.append(
                    KeepTogether(
                        [
                            Paragraph(f"&bull; <b>{kpi.name}</b> ({priority}) — {kpi.reason}", st["bullet"]),
                            Paragraph(kpi.formula or "No DAX formula generated.", st["mono"]),
                        ]
                    )
                )
        story.append(PageBreak())

    @classmethod
    def _build_decisions(cls, story: list, result: MasterIntelligenceResult, st: dict) -> None:
        story.append(Paragraph("Strategic Decisions", st["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=12))

        report = result.decision_report
        if not report or not report.primary_decisions:
            story.append(Paragraph("No strategic decisions were generated for this dataset.", st["body"]))
            return

        if report.executive_decision_summary:
            story.append(Paragraph(report.executive_decision_summary, st["body"]))
            story.append(Spacer(1, 8))

        for dec in report.primary_decisions:  # every decision, not a hardcoded top-4
            story.append(
                KeepTogether(
                    [
                        Paragraph(
                            f"&bull; <b>{dec.action_title}</b> "
                            f"<font color='#9CA3AF' size='8'>(urgency: {dec.urgency}, "
                            f"confidence: {dec.confidence * 100:.0f}%, ROI: {dec.expected_roi})</font>",
                            st["callout"],
                        ),
                        Paragraph(dec.description, st["body"]),
                    ]
                )
            )

        if report.scenario_options:
            story.append(Paragraph("<b>Scenario Options</b>", st["h2"]))
            for s in report.scenario_options:
                story.append(
                    Paragraph(
                        f"&bull; <b>{s.scenario_name}</b> "
                        f"(probability of success: {s.probability_of_success * 100:.0f}%): "
                        f"{s.description} — {s.projected_impact}",
                        st["bullet"],
                    )
                )

        if report.risk_matrix_summary:
            story.append(Paragraph("<b>Risk Summary</b>", st["h2"]))
            story.append(Paragraph(report.risk_matrix_summary, st["body"]))

    # -- entry point --------------------------------------------------------

    @classmethod
    def build_executive_pdf(cls, result: MasterIntelligenceResult, branding: BrandingConfig = BrandingConfig()) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=letter,
            rightMargin=36, leftMargin=36, topMargin=45, bottomMargin=40,
        )
        st = cls._styles()

        story: list = []
        cls._build_cover(story, result, branding, st)

        story.append(_CategoryMarker("EXECUTIVE BRIEFING"))
        cls._build_briefing(story, result, st)

        story.append(_CategoryMarker("DATASET SCHEMA"))
        cls._build_schema(story, result, st)

        story.append(_CategoryMarker("DATA QUALITY AUDIT"))
        cls._build_quality(story, result, st)

        story.append(_CategoryMarker("CLEANING AUDIT TRAIL"))
        cls._build_cleaning(story, result, st)

        story.append(_CategoryMarker("STATISTICAL INTELLIGENCE"))
        cls._build_intelligence(story, result, st)

        story.append(_CategoryMarker("EXECUTIVE INSIGHTS"))
        cls._build_insights(story, result, st)

        story.append(_CategoryMarker("ENTITY RELATIONSHIPS"))
        cls._build_relationships(story, result, st)

        story.append(_CategoryMarker("DAX KPI MEASURES"))
        cls._build_kpis(story, result, st)

        story.append(_CategoryMarker("STRATEGIC DECISIONS"))
        cls._build_decisions(story, result, st)

        doc.build(story, canvasmaker=MagazineCanvas)
        return buffer.getvalue()
