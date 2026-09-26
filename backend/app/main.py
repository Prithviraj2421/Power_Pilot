from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.copilot_route import router as copilot_router
from app.routes.data_quality_route import router as data_quality_router
from app.routes.export_center_route import router as export_center_router
from app.routes.intelligence_route import router as intelligence_router
from app.routes.powerbi_route import router as powerbi_router
from app.routes.upload import router as upload_router

app = FastAPI(
    title="PowerPilot API",
    version="1.0.0",
    description="Intelligent Power BI Automation Platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(data_quality_router)
app.include_router(intelligence_router)
app.include_router(powerbi_router)
app.include_router(copilot_router)
app.include_router(export_center_router)


@app.get("/")
def home():
    return {"message": "Welcome to PowerPilot"}
