import io
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
import pandas as pd

from app.export_center.export_center_facade import EnterpriseExportCenter
from app.export_center.models.export_models import BrandingConfig, EmailDistributionPayload, ReportTheme
from app.export_center.services.email_service import EmailDistributionService
from app.export_center.services.export_history_service import ExportHistoryService
from app.pipeline.intelligence_pipeline import PowerPilotIntelligencePipeline

router = APIRouter(prefix="/api/v1/export-center", tags=["Export & Distribution Center"])
pipeline = PowerPilotIntelligencePipeline()
email_service = EmailDistributionService()


@router.post("/cleaned-data")
def export_cleaned_data(file: UploadFile = File(...), format: str = Query("csv")):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)
        content = EnterpriseExportCenter.export_cleaned_data(df, result, fmt=format)

        media_type = "text/csv" if format.lower() == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "csv" if format.lower() == "csv" else "xlsx"
        filename = f"Cleaned_{file.filename.replace('.csv', '')}.{ext}"

        return Response(content=content, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting cleaned data: {str(e)}")


@router.post("/pdf")
def export_pdf_report(
    file: UploadFile = File(...),
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        branding = BrandingConfig(company_name=company_name, prepared_for=prepared_for)
        pdf_bytes = EnterpriseExportCenter.export_pdf_report(result, branding=branding)

        filename = f"PowerPilot_Executive_Report_{file.filename.replace('.csv', '')}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting PDF report: {str(e)}")


@router.post("/docx")
def export_docx_report(
    file: UploadFile = File(...),
    company_name: str = Query("Enterprise Organization"),
    prepared_for: str = Query("Executive Leadership Team"),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        branding = BrandingConfig(company_name=company_name, prepared_for=prepared_for)
        docx_bytes = EnterpriseExportCenter.export_docx_report(result, branding=branding)

        filename = f"PowerPilot_Executive_Report_{file.filename.replace('.csv', '')}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting Word report: {str(e)}")


@router.post("/html")
def export_html_report(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        html_bytes = EnterpriseExportCenter.export_html_report(result)
        filename = f"PowerPilot_Interactive_Report_{file.filename.replace('.csv', '')}.html"
        return Response(content=html_bytes, media_type="text/html", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting HTML report: {str(e)}")


@router.post("/json")
def export_master_json(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        json_bytes = EnterpriseExportCenter.export_json(result)
        filename = f"PowerPilot_Intelligence_{file.filename.replace('.csv', '')}.json"
        return Response(content=json_bytes, media_type="application/json", headers={"Content-Disposition": f"attachment; filename={filename}"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting Master JSON: {str(e)}")


@router.post("/data-dictionary")
def export_data_dictionary(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        xlsx_bytes = EnterpriseExportCenter.export_data_dictionary(result)
        filename = f"PowerPilot_Data_Dictionary_{file.filename.replace('.csv', '')}.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting Data Dictionary: {str(e)}")


@router.post("/email")
async def email_report_distribution(
    file: UploadFile = File(...),
    recipients: str = Query(..., description="Comma separated recipient email addresses"),
    subject: str = Query("PowerPilot Executive BI Report"),
    body_message: str = Query("Please find attached the executive intelligence report generated by PowerPilot."),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a valid .csv file.")
    try:
        contents = file.file.read()
        df = pd.read_csv(io.BytesIO(contents))
        result = pipeline.run_pipeline(df, dataset_name=file.filename)

        pdf_bytes = EnterpriseExportCenter.export_pdf_report(result)
        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

        payload = EmailDistributionPayload(
            recipients=recipient_list,
            subject=subject,
            body_message=body_message,
        )

        res = await email_service.send_distribution_email(payload, attachments_map={"Executive_Report.pdf": pdf_bytes})
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending email report: {str(e)}")


@router.get("/history")
def get_export_history():
    return {
        "status": "success",
        "history": ExportHistoryService.get_history(),
    }
