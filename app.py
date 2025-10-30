# app.py
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Attachment, AttachmentEntity
from admin_views import (
VehicleAdmin, MaintenanceAdmin, InspectionAdmin, FeeAdmin, DisposalAdmin, AttachmentAdmin
)
from config import settings, UPLOAD_PATH

app = FastAPI(title="Fleet MVP")


# --- DB 連線與建表 ---
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


# --- SQLAdmin 後台 ---
admin = Admin(app=app, engine=engine)
admin.add_view(VehicleAdmin)
admin.add_view(MaintenanceAdmin)
admin.add_view(InspectionAdmin)
admin.add_view(FeeAdmin)
admin.add_view(DisposalAdmin)
admin.add_view(AttachmentAdmin)


# --- 靜態檔案服務（提供已上傳附件下載） ---
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")

# --- 通用附件上傳 API ---
@app.post("/api/attachments/upload")
async def upload_attachment(
    entity_type: AttachmentEntity = Form(...),
    entity_id: str = Form(...), # 目標紀錄的 UUID 字串
    file: UploadFile = File(...),
    description: str | None = Form(None),
):
    # 儲存檔案
    suffix = Path(file.filename).suffix
    safe_name = f"{entity_type.value}_{entity_id}{suffix}"
    save_path = UPLOAD_PATH / safe_name
    with open(save_path, "wb") as f:
        f.write(await file.read())


    # 建立附件紀錄
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    import uuid
    try:
        ent_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="entity_id 必須是 UUID")


    with SessionLocal() as session:
        att = Attachment(
        entity_type=entity_type,
        entity_id=ent_uuid,
        file_name=file.filename,
        file_path=str(save_path),
        description=description,
        )
        session.add(att)
        session.commit()
        session.refresh(att)
        return {
        "id": str(att.id),
        "file_url": f"/uploads/{save_path.name}",
        }


# 健康檢查
@app.get("/health")
def health():
    return {"ok": True}