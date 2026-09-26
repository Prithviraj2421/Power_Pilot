# PowerPilot — Automated Power BI & Data Intelligence Platform

> **PowerPilot** is an enterprise-grade, modern business intelligence platform built to transform raw CSV datasets into executive Power BI dashboards, DAX measures, Tabular Model `.bim` schemas, strategic decision recommendations, and grounded conversational AI copilot insights.

---

## Key Platform Features

- **10-Stage Intelligence Engine**:
  1. **Schema Profiler**: Physical type detection (`INTEGER`, `FLOAT`, `BOOLEAN`, `DATETIME`, `CATEGORICAL`, `TEXT`).
  2. **Entity Detector**: Semantic classification (`CUSTOMER`, `PRODUCT`, `REVENUE`, `PROFIT`, `COST`, `QUANTITY`, `DATE`, `REGION`, `EMPLOYEE`, `IDENTIFIER`).
  3. **Domain Classifier**: Domain ranking across Retail, Finance, HR, Healthcare, Marketing, and Logistics.
  4. **Business Profiler**: Dimension & measure taxonomy, executive briefing generation.
  5. **Data Intelligence**: Quality metrics, Pearson correlation matrices, trend slopes, and IQR outlier detection.
  6. **Insight Engine**: Categorized insights with risk severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and recommendations.
  7. **Relationship Engine**: Primary Key, Foreign Key, Parent-Child Hierarchy, and Semantic Link detection.
  8. **KPI Recommendation Engine**: Executable DAX formula generation and target benchmarks.
  9. **Dashboard Recommendation Engine**: Multi-tab executive BI specs and visual widget placement.
  10. **Strategic Decision Engine**: Action recommendations, expected ROI, risk level, and scenario probability modeling.

- **AI Copilot & Conversational BI**:
  - Grounded natural language Q&A against dataset intelligence without hallucinations.
  - Sub-50ms query turns with supporting proof-point evidence cards.

- **Power BI Export Studio**:
  - **One-Click DAX Script Export (`.dax`)**: Formatted DAX measures ready for Power BI Desktop.
  - **Tabular Model Schema Export (`.bim`)**: Microsoft Analysis Services Tabular Model schema for Tabular Editor.
  - **Power Query (M) Code Export (`.m`)**: M-code for data type transformations.
  - **Live Web REST API Connector**: `http://localhost:8000/api/v1/intelligence/analyze-csv`.

---

## System Architecture

```text
PowerPilot/
├── backend/
│   ├── app/
│   │   ├── intelligence/         # 10 Intelligence Engines & Copilot Engine
│   │   ├── models/               # Dataclass models (Schema, KPI, Relationship, Decision)
│   │   ├── pipeline/             # PowerPilotIntelligencePipeline master runner
│   │   ├── routes/               # FastAPI route handlers (intelligence, powerbi, copilot)
│   │   ├── services/             # PowerBIExportService & business logic
│   │   └── common/               # Enums, constants, and structured logger
│   └── tests/                    # 206 pytest unit and integration test cases
└── frontend/
    ├── src/
    │   ├── api/                  # Axios API client (60s timeout, error interceptors)
    │   ├── components/           # UI library (Button, Card, Modal, Tabs, MetricCard, Toast)
    │   ├── features/             # Business features (dashboard, insights, kpis, relationships, decision, copilot, powerbi)
    │   ├── hooks/                # Custom React hooks (useApi, useFileUpload, useToast)
    │   ├── pages/                # HomePage, WorkspacePage, SettingsPage, NotFoundPage
    │   ├── store/                # Zustand stores (useAppStore, useUploadStore, useAnalysisStore)
    │   └── types/                # 100% typed domain model definitions
    └── dist/                     # Vite production build output
```

---

## Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm

### 1. Start the Backend API (FastAPI)
```powershell
cd e:\PowerPilot\backend
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
```
- API Server: `http://localhost:8000`
- Interactive Swagger Documentation: `http://localhost:8000/docs`

### 2. Start the Frontend Application (Vite)
```powershell
cd e:\PowerPilot\frontend
npm run dev
```
- Web Application: `http://localhost:3000` (or `http://localhost:5173`)

### 3. Run Automated Test Suites
```powershell
# Backend Pytest Suite
cd e:\PowerPilot\backend
& ".venv\Scripts\python.exe" -m pytest tests/ -v

# Frontend TypeScript Type Check
cd e:\PowerPilot\frontend
npx tsc --noEmit

# Frontend Production Build
npm run build
```

---

## License
PowerPilot Enterprise License.