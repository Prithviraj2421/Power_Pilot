from app.export_center.models.export_models import BrandingConfig
from app.models.master_intelligence_result import MasterIntelligenceResult


class HtmlExportBuilder:
    """
    Builder generating standalone interactive executive HTML reports.
    """

    @staticmethod
    def build_executive_html(result: MasterIntelligenceResult, branding: BrandingConfig = BrandingConfig()) -> bytes:
        dataset_name = result.dataset_profile.dataset_name
        domain = result.dataset_profile.detected_domain.upper()
        grade = result.quality_report.grade.value if result.quality_report else "A"
        score = result.quality_report.overall_score if result.quality_report else 95.0

        summary_obj = result.insight_report.executive_summary if result.insight_report else None
        exec_summary = (
            getattr(summary_obj, "overview", getattr(summary_obj, "headline", "Executive Intelligence Analysis Complete."))
            if summary_obj
            else "Executive Intelligence Analysis Complete."
        )

        key_findings = (
            getattr(summary_obj, "major_findings", getattr(summary_obj, "key_findings", ()))
            if summary_obj
            else ()
        )

        insights_list = result.insight_report.insights if result.insight_report else []
        kpis_list = result.kpi_report.primary_kpis if result.kpi_report else []
        decisions_list = result.decision_report.primary_decisions if result.decision_report else []

        findings_html = "".join(f"<li>{f}</li>" for f in key_findings)
        insights_html = "".join(
            f"""
            <div class="card">
                <div class="badge badge-{i.severity.lower() if hasattr(i, 'severity') and i.severity else 'primary'}">{i.severity if hasattr(i, 'severity') and i.severity else 'MEDIUM'}</div>
                <h3>{i.title}</h3>
                <p>{i.description}</p>
                <div class="impact"><strong>Impact:</strong> {i.business_impact}</div>
            </div>
            """
            for i in insights_list[:6]
        )

        kpis_html = "".join(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">{k.name}</div>
                <div class="kpi-code"><code>{k.formula}</code></div>
                <div class="kpi-target">Target: {k.target_threshold or 'N/A'}</div>
            </div>
            """
            for k in kpis_list[:6]
        )

        decisions_html = "".join(
            f"""
            <div class="card">
                <div class="badge badge-success">Confidence: {getattr(d, 'confidence', 0.85) * 100:.0f}%</div>
                <h3>{getattr(d, 'action_title', getattr(d, 'title', 'Decision Action'))}</h3>
                <p>{d.description}</p>
                <p><strong>Expected ROI:</strong> {getattr(d, 'expected_roi', 'High Impact')}</p>
            </div>
            """
            for d in decisions_list[:4]
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PowerPilot Executive Report - {dataset_name}</title>
    <style>
        :root {{
            --primary: #3B82F6;
            --background: #0B0F19;
            --surface: #111827;
            --border: #1F2937;
            --text: #F3F4F6;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--background);
            color: var(--text);
            margin: 0;
            padding: 0;
            display: flex;
        }}
        .sidebar {{
            width: 260px;
            background: var(--surface);
            border-right: 1px solid var(--border);
            height: 100vh;
            position: fixed;
            padding: 24px;
            box-sizing: border-box;
        }}
        .brand {{
            font-size: 20px;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 30px;
        }}
        .nav-item {{
            display: block;
            color: #9CA3AF;
            text-decoration: none;
            padding: 10px 14px;
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 14px;
            font-weight: 500;
        }}
        .nav-item:hover, .nav-item.active {{
            background: var(--primary);
            color: #FFF;
        }}
        .main-content {{
            margin-left: 260px;
            padding: 40px;
            max-width: 1100px;
            width: 100%;
        }}
        .header-box {{
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 30px;
            border-radius: 16px;
            margin-bottom: 30px;
        }}
        .score-pill {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid var(--success);
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 700;
            display: inline-block;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            padding: 20px;
            border-radius: 12px;
        }}
        .kpi-card {{
            background: #1F2937;
            padding: 16px;
            border-radius: 10px;
            margin-bottom: 12px;
        }}
        .kpi-code {{
            background: #0B0F19;
            padding: 8px;
            border-radius: 6px;
            font-family: monospace;
            color: #93C5FD;
            font-size: 12px;
            margin: 8px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            float: right;
        }}
        .badge-critical, .badge-danger {{ background: rgba(239, 68, 68, 0.2); color: var(--danger); }}
        .badge-high, .badge-warning {{ background: rgba(245, 158, 11, 0.2); color: var(--warning); }}
        .badge-primary {{ background: rgba(59, 130, 246, 0.2); color: var(--primary); }}
        .badge-success {{ background: rgba(16, 185, 129, 0.2); color: var(--success); }}
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="brand">PowerPilot BI</div>
        <a href="#summary" class="nav-item active">Executive Summary</a>
        <a href="#quality" class="nav-item">Data Quality Audit</a>
        <a href="#insights" class="nav-item">Strategic Insights</a>
        <a href="#kpis" class="nav-item">DAX KPI Studio</a>
        <a href="#decisions" class="nav-item">Decision Matrix</a>
    </div>

    <div class="main-content">
        <div class="header-box" id="summary">
            <span class="score-pill">Quality Score: {score:.1f}% (Grade {grade})</span>
            <h1 style="margin: 16px 0 8px 0;">{branding.company_name} - {domain} Report</h1>
            <p style="color: #9CA3AF; margin: 0;">Dataset: <strong>{dataset_name}</strong> | Prepared for: {branding.prepared_for}</p>
            <h3 style="margin-top: 24px; color: #3B82F6;">{exec_summary}</h3>
            <ul>{findings_html}</ul>
        </div>

        <h2 id="insights">Strategic Business Insights</h2>
        <div class="grid">{insights_html}</div>

        <h2 id="kpis">Executable DAX KPI Formulas</h2>
        <div>{kpis_html}</div>

        <h2 id="decisions">Executive Decision Recommendations</h2>
        <div class="grid">{decisions_html}</div>
    </div>
</body>
</html>
"""
        return html_content.encode("utf-8")
