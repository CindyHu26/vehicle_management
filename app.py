# app.py
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request # (!!!) 匯入 Request
from fastapi.staticfiles import StaticFiles
from starlette_admin.contrib.sqla import Admin 

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Attachment, AttachmentEntity
# (!!!) 匯入修改後的 admin_views
from admin_views import (
    EmployeeAdmin, VehicleAdmin, VehicleAssetLogAdmin, 
    MaintenanceAdmin, InspectionAdmin, FeeAdmin, DisposalAdmin, AttachmentAdmin
)
from config import settings, UPLOAD_PATH
import uuid

app = FastAPI(
    title="公務車管理系統",
)


# --- DB 連線與建表 ---
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


# --- SQLAdmin 後台 (!!! 修改為 starlette-admin !!!) ---
# (!!!) 舊的 admin = Admin(app=app, engine=engine, title="公務車管理後台")

# (!!!) 新的
admin = Admin(
    engine,
    title="公務車管理後台",
    base_url="/admin", # 設定後台路徑
    # 可以在這裡加入簡易認證
    # auth_provider=... 
)

# (!!!) add_view 的方式相同
admin.add_view(EmployeeAdmin)
admin.add_view(VehicleAdmin)
admin.add_view(VehicleAssetLogAdmin)
admin.add_view(MaintenanceAdmin)
admin.add_view(InspectionAdmin)
admin.add_view(FeeAdmin)
admin.add_view(DisposalAdmin)
admin.add_view(AttachmentAdmin)

# (!!!) 掛載 admin
admin.mount_to(app)

# --- 靜態檔案服務（提供已上傳附件下載） ---
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")

# --- 通用附件上傳 API (加入中文說明) ---
# (!!!) 為了讓 session 能在 API 中使用，增加 Request 依賴
@app.post("/api/attachments/upload")
async def upload_attachment(
    request: Request, # (!!!) 取得 Request
    entity_type: AttachmentEntity = Form(..., description="關聯的實體類型 (例如: vehicle)"),
    entity_id: str = Form(..., description="關聯紀錄的ID (UUID)"),
    file: UploadFile = File(..., description="要上傳的檔案"),
    description: str | None = Form(None, description="檔案說明 (可選)"),
):
    # 儲存檔案
    suffix = Path(file.filename).suffix
    safe_name = f"{entity_type.value}_{entity_id}_{uuid.uuid4().hex}{suffix}"
    save_path = UPLOAD_PATH / safe_name
    
    try:
        with open(save_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法儲存檔案: {e}")

    try:
        ent_uuid = uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="entity_id 必須是 UUID 格式")

    # (!!!) starlette-admin 建議這樣取得 session
    with SessionLocal() as session:
        att = Attachment(
        entity_type=entity_type,
        entity_id=ent_uuid,
        file_name=file.filename,
        file_path=str(save_path.name),
        description=description,
        )
        session.add(att)
        session.commit()
        session.refresh(att)
        return {
        "id": str(att.id),
        "file_url": f"/uploads/{save_path.name}",
        "file_name": att.file_name,
        }


# 健康檢查
@app.get("/health")
def health():
    return {"ok": True}