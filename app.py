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

# --- 修改 FastAPI 應用程式標題 ---
app = FastAPI(title="公務車管理系統")


# --- DB 連線與建表 ---
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


# --- SQLAdmin 後台 (加入中文 title) ---
admin = Admin(app=app, engine=engine, title="公務車管理後台") # <-- 加上中文標題
admin.add_view(VehicleAdmin)
admin.add_view(MaintenanceAdmin)
admin.add_view(InspectionAdmin)
admin.add_view(FeeAdmin)
admin.add_view(DisposalAdmin)
admin.add_view(AttachmentAdmin)


# --- 靜態檔案服務（提供已上傳附件下載） ---
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")

# --- 通用附件上傳 API (加入中文說明) ---
@app.post("/api/attachments/upload")
async def upload_attachment(
    entity_type: AttachmentEntity = Form(..., description="關聯的實體類型 (例如: vehicle)"),
    entity_id: str = Form(..., description="關聯紀錄的ID (UUID)"), # 目標紀錄的 UUID 字串
    file: UploadFile = File(..., description="要上傳的檔案"),
    description: str | None = Form(None, description="檔案說明 (可選)"),
):
    # 儲存檔案
    suffix = Path(file.filename).suffix
    # 建立一個更安全的唯一檔案名稱
    import uuid
    safe_name = f"{entity_type.value}_{entity_id}_{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_PATH / safe_name
    
    try:
        with open(save_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        # 處理可能的寫入錯誤
        raise HTTPException(status_code=500, detail=f"無法儲存檔案: {e}")


    # 建立附件紀錄
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    try:
        ent_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="entity_id 必須是 UUID 格式")


    with SessionLocal() as session:
        att = Attachment(
        entity_type=entity_type,
        entity_id=ent_uuid,
        file_name=file.filename, # 儲存原始檔名
        file_path=str(save_path.name), # 僅儲存檔案名稱，非完整路徑
        description=description,
        )
        session.add(att)
        session.commit()
        session.refresh(att)
        return {
        "id": str(att.id),
        "file_url": f"/uploads/{save_path.name}", # 提供相對路徑
        "file_name": att.file_name,
        }


# 健康檢查
@app.get("/health")
def health():
    return {"ok": True}