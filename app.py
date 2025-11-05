# 檔案名稱: app.py
# app.py
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4
from typing import Optional
from datetime import date
from decimal import Decimal

from fastapi import (
    FastAPI, Request, Depends, Form, HTTPException, Response,
    File, UploadFile
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates 
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session, joinedload 

from models import (
    Base, Vehicle, Employee, 
    VehicleType, VehicleStatus,
    Maintenance, MaintenanceCategory, Fee, FeeType,
    Inspection, InspectionKind,
    VehicleAssetLog, AssetType, AssetStatus, Disposal,
    Attachment, AttachmentEntity
)
from config import settings, UPLOAD_PATH

# 翻譯字典
VEHICLE_TYPE_MAP = {
    "car": "小客車", "motorcycle": "機車", "van": "廂型車",
    "truck": "貨車", "ev_scooter": "電動機車",
}
VEHICLE_STATUS_MAP = {
    "active": "啟用中", "maintenance": "維修中", "retired": "已報廢",
}

MAINTENANCE_CATEGORY_MAP = {
    "maintenance": "定期保養",
    "repair": "維修",
    "carwash": "一般洗車",
    "deep_cleaning": "手工洗車",
    "ritual_cleaning": "淨車",
}

INSPECTION_KIND_MAP = {
    "periodic": "定期檢驗",
    "emission": "排氣檢驗",
    "reinspection": "複檢",
}

FEE_TYPE_MAP = {
    "fuel_fee": "加油費",
    "parking": "停車費",
    "maintenance_service": "保養服務",
    "repair_parts": "維修零件",
    "inspection_fee": "檢驗費",
    "supplies": "用品/雜項",
    "toll": "E-Tag/過路費",
    "license_tax": "稅金",
    "other": "其他",
}

# 資產類型翻譯字典
ASSET_TYPE_MAP = {
    "key": "鑰匙",
    "dashcam": "行車紀錄器",
    "etag": "E-Tag",
    "other": "其他",
}

# 資產狀態翻譯字典
ASSET_STATUS_MAP = {
    "assigned": "已指派",
    "returned": "已歸還",
    "lost": "遺失",
    "disposed": "已報廢/處理",
}

app = FastAPI(title="公務車管理系統")

# --- DB 連線與 Session ---
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 模板與靜態檔案 ---
templates = Jinja2Templates(directory="templates")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_PATH)), name="uploads")

templates.env.globals['vehicle_type_map'] = VEHICLE_TYPE_MAP
templates.env.globals['vehicle_status_map'] = VEHICLE_STATUS_MAP
templates.env.globals['maintenance_category_map'] = MAINTENANCE_CATEGORY_MAP
templates.env.globals['inspection_kind_map'] = INSPECTION_KIND_MAP
templates.env.globals['fee_type_map'] = FEE_TYPE_MAP
templates.env.globals['asset_type_map'] = ASSET_TYPE_MAP
templates.env.globals['asset_status_map'] = ASSET_STATUS_MAP

# --- 頁面路由 ---
@app.get("/")
async def get_main_page(request: Request):
    return templates.TemplateResponse(
        name="base.html",
        context={"request": request}
    )

# 新增「車輛管理」的主頁面路由
@app.get("/vehicle-management")
async def get_vehicle_management_page(
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    渲染「車輛管理」的主頁面，包含篩選器。
    """
    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    
    return templates.TemplateResponse(
        name="pages/vehicle_management.html", # 我們將在步驟 3 建立這個新檔案
        context={
            "request": request,
            "all_employees": all_employees,
            "all_vehicle_types": list(VehicleType),
            "all_vehicle_statuses": list(VehicleStatus),
            "query_params": request.query_params # 傳遞查詢參數
        }
    )

@app.get("/vehicle/{vehicle_id}")
async def get_vehicle_detail_page(
    request: Request, 
    vehicle_id: UUID, 
    db: Session = Depends(get_db)
):
    """
    渲染「單一車輛詳情」的主頁面。
    這個頁面將作為儀表板，用來載入相關的子項目 (如保養、檢驗等)。
    """
    stmt = (
        select(Vehicle)
        .options(joinedload(Vehicle.user)) 
        .where(Vehicle.id == vehicle_id)
    )
    vehicle = db.scalar(stmt)
    
    if not vehicle:
        raise HTTPException(status_code=404, detail="找不到該車輛")

    return templates.TemplateResponse(
        name="pages/vehicle_detail_page.html", # 我們即將建立這個新模板
        context={
            "request": request,
            "vehicle": vehicle,
        }
    )

# --- 列表 API (車輛) ---
@app.get("/vehicles-list")
async def get_vehicles_list(
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    取得車輛列表 (片段)，支援篩選和排序。
    """
    query_params = request.query_params
    
    # 1. 建立基礎查詢
    stmt = (
        select(Vehicle)
        .options(joinedload(Vehicle.user)) 
    )
    
    # 2. 處理篩選
    filter_user_id = query_params.get("filter_user_id")
    filter_vehicle_type = query_params.get("filter_vehicle_type")
    filter_status = query_params.get("filter_status")
    
    if filter_user_id:
        stmt = stmt.where(Vehicle.user_id == UUID(filter_user_id))
    if filter_vehicle_type:
        stmt = stmt.where(Vehicle.vehicle_type == filter_vehicle_type)
    if filter_status:
        stmt = stmt.where(Vehicle.status == filter_status)

    # 3. 處理排序
    sort_by = query_params.get("sort_by", "plate_no") # 預設依車牌排序
    sort_order = query_params.get("sort_order", "asc") # 預設升冪
    
    sort_column = getattr(Vehicle, sort_by, Vehicle.plate_no)
    
    if sort_order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(sort_column)

    vehicles = db.scalars(stmt).all()
    
    return templates.TemplateResponse(
        name="fragments/vehicle_list.html",
        context={
            "request": request,
            "vehicles": vehicles,
            "query_params": query_params,
            "current_sort_by": sort_by,
            "current_sort_order": sort_order
        }
    )

# --- 車輛 CRUD ---
@app.get("/vehicle/new")
@app.get("/vehicle/{vehicle_id}/edit")
async def get_vehicle_form(
    request: Request, 
    vehicle_id: Optional[UUID] = None, 
    db: Session = Depends(get_db)
):
    vehicle = None
    if vehicle_id:
        vehicle = db.get(Vehicle, vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")

    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    
    return templates.TemplateResponse(
        name="fragments/vehicle_form.html",
        context={
            "request": request,
            "vehicle": vehicle, 
            "all_employees": all_employees,
            "vehicle_types": list(VehicleType), 
            "vehicle_statuses": list(VehicleStatus), 
        }
    )

@app.post("/vehicle/new")
@app.post("/vehicle/{vehicle_id}/edit")
async def create_or_update_vehicle(
    request: Request,
    vehicle_id: Optional[UUID] = None, 
    db: Session = Depends(get_db),
    plate_no: str = Form(...),
    user_id: Optional[str] = Form(None), 
    vehicle_type: VehicleType = Form(...),
    status: VehicleStatus = Form(...),
    company: Optional[str] = Form(None),
    make: Optional[str] = Form(None),
    model: Optional[str] = Form(None)
):
    user_uuid = None
    if user_id:
        try:
            user_uuid = UUID(user_id) 
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid User ID format")

    if vehicle_id:
        vehicle = db.get(Vehicle, vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail="Vehicle not found")
    else:
        existing = db.scalar(select(Vehicle).where(Vehicle.plate_no == plate_no))
        if existing:
            raise HTTPException(status_code=400, detail="車牌號碼已存在")
        vehicle = Vehicle()
        db.add(vehicle)

    # 更新欄位
    vehicle.plate_no = plate_no
    vehicle.user_id = user_uuid
    vehicle.vehicle_type = vehicle_type
    vehicle.status = status
    vehicle.company = company
    vehicle.make = make
    vehicle.model = model
    
    # 1. 補上缺失的 commit
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")
    
    # 2. 補上缺失的 HX-Trigger
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshVehicleList"}
    )

@app.delete("/vehicle/{vehicle_id}/delete")
async def delete_vehicle(
    vehicle_id: UUID,                 
    request: Request,
    db: Session = Depends(get_db)     
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        return Response(status_code=200)

    try:
        db.delete(vehicle)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")
    
    return Response(status_code=200)

# 「員工管理」的主頁面路由
@app.get("/employee-management")
async def get_employee_management_page(
    request: Request, 
    db: Session = Depends(get_db)
):
    """
    渲染「員工管理」的主頁面，包含篩選器。
    """
    return templates.TemplateResponse(
        name="pages/employee_management.html", # 我們將在步驟 3 建立這個新檔案
        context={
            "request": request,
            "query_params": request.query_params # 傳遞查詢參數
        }
    )

# --- 列表 API (員工) ---
@app.get("/employees-list")
async def get_employees_list(
    request: Request, 
    db: Session = Depends(get_db)
):
    # 2. 修改此函式以支援篩選
    query_params = request.query_params

    # 1. 建立基礎查詢
    stmt = select(Employee)
    
    # 2. 處理篩選
    filter_has_car_license = query_params.get("filter_has_car_license")
    filter_has_motorcycle_license = query_params.get("filter_has_motorcycle_license")
    filter_is_handler = query_params.get("filter_is_handler")

    if filter_has_car_license == "yes":
        stmt = stmt.where(Employee.has_car_license == True)
    elif filter_has_car_license == "no":
        stmt = stmt.where(Employee.has_car_license == False)

    if filter_has_motorcycle_license == "yes":
        stmt = stmt.where(Employee.has_motorcycle_license == True)
    elif filter_has_motorcycle_license == "no":
        stmt = stmt.where(Employee.has_motorcycle_license == False)

    if filter_is_handler == "yes":
        stmt = stmt.where(Employee.is_handler == True)
    elif filter_is_handler == "no":
        stmt = stmt.where(Employee.is_handler == False)

    # 3. 預設排序
    stmt = stmt.order_by(Employee.name)
    
    employees = db.scalars(stmt).all()
    
    return templates.TemplateResponse(
        name="fragments/employee_list.html",
        context={
            "request": request,
            "employees": employees,
            "query_params": query_params # 傳遞篩選參數
        }
    )

# --- 員工 CRUD ---
@app.get("/employee/new")
@app.get("/employee/{employee_id}/edit")
async def get_employee_form(
    request: Request,
    employee_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    employee = None
    if employee_id:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

    return templates.TemplateResponse(
        name="fragments/employee_form.html",
        context={
            "request": request,
            "employee": employee
        }
    )

@app.post("/employee/new")
@app.post("/employee/{employee_id}/edit")
async def create_or_update_employee(
    request: Request,
    employee_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    has_car_license: bool = Form(False),
    has_motorcycle_license: bool = Form(False),
    is_handler: bool = Form(False)
):
    if employee_id:
        employee = db.get(Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
    else:
        existing = db.scalar(select(Employee).where(Employee.name == name))
        if existing:
            raise HTTPException(status_code=400, detail="員工姓名已存在")
        employee = Employee()
        db.add(employee)

    # 更新欄位
    employee.name = name
    employee.phone = phone
    employee.has_car_license = has_car_license
    employee.has_motorcycle_license = has_motorcycle_license
    employee.is_handler = is_handler
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發「員工」列表刷新
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshEmployeeList"}
    )

@app.delete("/employee/{employee_id}/delete")
async def delete_employee(
    employee_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    employee = db.get(Employee, employee_id)
    if not employee:
        return Response(status_code=200)

    try:
        db.delete(employee)
        db.commit()
    except Exception as e:
        db.rollback()
        if "violates foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="無法刪除：此員工仍有關聯的車輛或紀錄。")
        raise HTTPException(status_code=500, detail=f"刪除失敗: {e}")
    
    return Response(status_code=200)

@app.get("/vehicle/{vehicle_id}/maintenance-list")
async def get_maintenance_list(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得單一車輛的保養列表 (片段) """
    stmt = (
        select(Maintenance)
        .where(Maintenance.vehicle_id == vehicle_id)
        .options(
            joinedload(Maintenance.user), 
            joinedload(Maintenance.handler)
        )
        .order_by(desc(Maintenance.performed_on)) # 依執行日期倒序
    )
    maintenance_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/maintenance_list.html",
        context={
            "request": request,
            "maintenance_records": maintenance_records,
            "vehicle_id": vehicle_id # 傳遞 vehicle_id 供「新增」按鈕使用
        }
    )

@app.get("/maintenance-list-all")
async def get_maintenance_list_all(
    request: Request,
    db: Session = Depends(get_db) # (!!!) 修正 1：從 get.db 改為 get_db (!!!)
):
    """ 取得「所有」車輛的保養列表 (片段) - 支援篩選和排序 """
    
    query_params = request.query_params
    
    # 1. (!!!) 建立基礎查詢 (!!!)
    stmt = (
        select(Maintenance)
        .options(
            joinedload(Maintenance.user), 
            joinedload(Maintenance.handler),
            joinedload(Maintenance.vehicle)
        )
    )
    
    # 2. (!!!) 處理篩選 (!!!)
    filter_vehicle_id = query_params.get("filter_vehicle_id")
    filter_user_id = query_params.get("filter_user_id")
    filter_category = query_params.get("filter_category")
    
    if filter_vehicle_id:
        stmt = stmt.where(Maintenance.vehicle_id == UUID(filter_vehicle_id))
    if filter_user_id:
            stmt = stmt.where(Maintenance.user_id == UUID(filter_user_id))
    if filter_category:
        stmt = stmt.where(Maintenance.category == filter_category)
        
    # 3. (!!!) 處理排序 (!!!)
    sort_by = query_params.get("sort_by", "performed_on")
    sort_order = query_params.get("sort_order", "desc")
    
    sort_column = getattr(Maintenance, sort_by, Maintenance.performed_on)
    
    if sort_order == "desc":
        stmt = stmt.order_by(desc(sort_column))
    else:
        stmt = stmt.order_by(sort_column)

    maintenance_records = db.scalars(stmt).all()

    # 4. (!!!) 傳回參數，供排序按鈕保持狀態 (!!!)
    return templates.TemplateResponse(
        name="fragments/maintenance_list_all.html",
        context={
            "request": request,
            "maintenance_records": maintenance_records,
            "query_params": query_params,
            "current_sort_by": sort_by,
            "current_sort_order": sort_order
        }
    )

@app.get("/maintenance/new")
@app.get("/maintenance/{maint_id}/edit")
async def get_maintenance_form(
    request: Request,
    vehicle_id: Optional[UUID] = None,
    maint_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """ 取得保養紀錄的「新增」或「編輯」表單 (Modal) """
    maint = None
    all_vehicles = None
    if maint_id:
        maint = db.get(Maintenance, maint_id)
        if not maint:
            raise HTTPException(status_code=404, detail="Maintenance record not found")
        vehicle_id = maint.vehicle_id # 編輯模式下，從紀錄取得 vehicle_id
    else:
        # 新增模式，需要載入所有車輛
        all_vehicles = db.scalars(select(Vehicle).order_by(Vehicle.plate_no)).all()

    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    all_handlers = db.scalars(
            select(Employee).where(Employee.is_handler == True).order_by(Employee.name)
        ).all()

    return templates.TemplateResponse(
        name="fragments/maintenance_form.html",
        context={
            "request": request,
            "maint": maint,
            # 傳遞預選的 vehicle_id (無論是來自查詢參數還是編輯模式)
            "selected_vehicle_id": vehicle_id, 
            "all_employees": all_employees,
            "all_handlers": all_handlers,
            "all_vehicles": all_vehicles, # 傳遞所有車輛 (僅限新增模式)
            "maintenance_categories": list(MaintenanceCategory),
        }
    )

# 保養管理主頁面
@app.get("/maintenance-management")
async def get_maintenance_page(
    request: Request,
    db: Session = Depends(get_db) # (!!!) 修正 2：從 get.db 改為 get_db (!!!)
):
    """ 
    渲染「保養管理 (全列表)」的主頁面。
    傳遞篩選器所需的資料
    """
    all_vehicles = db.scalars(select(Vehicle).order_by(Vehicle.plate_no)).all()
    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    
    return templates.TemplateResponse(
        name="pages/maintenance_management.html",
        context={
            "request": request,
            "all_vehicles": all_vehicles,
            "all_employees": all_employees,
            "all_categories": list(MaintenanceCategory),
            "query_params": request.query_params # 傳遞空參數，供初始載入
        }
    )

@app.post("/maintenance/new")
@app.post("/maintenance/{maint_id}/edit")
async def create_or_update_maintenance(
    request: Request,
    db: Session = Depends(get_db),
    maint_id: Optional[UUID] = None,
    vehicle_id: Optional[UUID] = Form(None),
    category: MaintenanceCategory = Form(...),
    performed_on: Optional[date] = Form(None),
    return_date: Optional[date] = Form(None),
    user_id: Optional[str] = Form(None),
    handler_id: Optional[str] = Form(None),
    vendor: Optional[str] = Form(None),
    odometer_km: Optional[int] = Form(None),
    service_target_km: Optional[int] = Form(None),
    amount: Optional[Decimal] = Form(None),
    is_reconciled: bool = Form(False),
    notes: Optional[str] = Form(None),
    handler_notes: Optional[str] = Form(None)
):
    """ 處理保養紀錄的「新增」或「儲存」 """

    # 轉換 UUID
    user_uuid = UUID(user_id) if user_id else None
    handler_uuid = UUID(handler_id) if handler_id else None

    if maint_id:
        # 編輯模式
        maint = db.get(Maintenance, maint_id)
        if not maint:
            raise HTTPException(status_code=404, detail="Maintenance record not found")
    else:
        if not vehicle_id:
            raise HTTPException(status_code=400, detail="必須選擇一輛車")
        # 新增模式
        maint = Maintenance()
        maint.vehicle_id = vehicle_id
        db.add(maint)

    # 更新欄位
    maint.category = category
    maint.performed_on = performed_on
    maint.return_date = return_date
    maint.user_id = user_uuid
    maint.handler_id = handler_uuid
    maint.vendor = vendor
    maint.odometer_km = odometer_km
    maint.service_target_km = service_target_km
    maint.amount = amount
    maint.is_reconciled = is_reconciled
    maint.notes = notes
    maint.handler_notes = handler_notes

    try:
        # 如果有填金額，自動建立一筆費用
        if amount and amount > 0:
            fee_type = FeeType.maintenance_service
            if category == MaintenanceCategory.repair:
                fee_type = FeeType.repair_parts

            # 費用請款人優先抓「經手人」，其次抓「當時使用人」
            fee_user_id = handler_uuid if handler_uuid else user_uuid

            new_fee = Fee(
                vehicle_id=maint.vehicle_id,
                user_id=fee_user_id,
                receive_date=performed_on, 
                request_date=performed_on, 
                fee_type=fee_type,
                amount=amount,
                is_paid=is_reconciled, 
                notes=f"自動建立 - {MAINTENANCE_CATEGORY_MAP.get(category.value, category.value)}: {notes or ''}"
            )
            db.add(new_fee)

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發保養列表刷新 (用於車輛詳情頁)
    # 觸發全域保養列表刷新 (用於新頁面)
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshMaintenanceList, refreshMaintenanceListAll"}
    )

@app.delete("/maintenance/{maint_id}/delete")
async def delete_maintenance(
    maint_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除一筆保養紀錄 """
    maint = db.get(Maintenance, maint_id)
    if not maint:
        return Response(status_code=200) # 已被刪除，直接返回成功

    try:
        db.delete(maint)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")

    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshMaintenanceList, refreshMaintenanceListAll"}
    )

# --- 檢驗紀錄 CRUD ---

@app.get("/inspection-management")
async def get_inspection_page(request: Request):
    """ 渲染「檢驗管理 (全列表)」的主頁面 """
    return templates.TemplateResponse(
        name="pages/inspection_management.html",
        context={"request": request}
    )

@app.get("/inspection-list-all")
async def get_inspection_list_all(
    request: Request,
    db: Session = Depends(get_db)
):
    """ 取得「所有」車輛的檢驗列表 (片段) """
    stmt = (
        select(Inspection)
        .options(
            joinedload(Inspection.user), 
            joinedload(Inspection.handler),
            joinedload(Inspection.vehicle)
        )
        .order_by(desc(Inspection.inspected_on), desc(Inspection.notification_date))
    )
    inspection_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/inspection_list_all.html",
        context={
            "request": request,
            "inspection_records": inspection_records,
        }
    )

@app.get("/vehicle/{vehicle_id}/inspection-list")
async def get_inspection_list(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得「單一車輛」的檢驗列表 (片段) """
    stmt = (
        select(Inspection)
        .where(Inspection.vehicle_id == vehicle_id)
        .options(
            joinedload(Inspection.user), 
            joinedload(Inspection.handler)
        )
        .order_by(desc(Inspection.inspected_on), desc(Inspection.notification_date))
    )
    inspection_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/inspection_list.html",
        context={
            "request": request,
            "inspection_records": inspection_records,
            "vehicle_id": vehicle_id
        }
    )

@app.get("/inspection/new")
@app.get("/inspection/{insp_id}/edit")
async def get_inspection_form(
    request: Request,
    vehicle_id: Optional[UUID] = None,
    insp_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """ 取得檢驗紀錄的「新增」或「編輯」表單 (Modal) """
    insp = None
    all_vehicles = None
    if insp_id:
        # 編輯模式
        insp = db.get(Inspection, insp_id)
        if not insp:
            raise HTTPException(status_code=404, detail="Inspection record not found")
        vehicle_id = insp.vehicle_id
    else:
        # 新增模式
        all_vehicles = db.scalars(select(Vehicle).order_by(Vehicle.plate_no)).all()

    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()
    all_handlers = db.scalars(
            select(Employee).where(Employee.is_handler == True).order_by(Employee.name)
        ).all()

    return templates.TemplateResponse(
        name="fragments/inspection_form.html",
        context={
            "request": request,
            "insp": insp,
            "selected_vehicle_id": vehicle_id, 
            "all_employees": all_employees,
            "all_handlers": all_handlers,
            "all_vehicles": all_vehicles,
            "inspection_kinds": list(InspectionKind),
        }
    )

@app.post("/inspection/new")
@app.post("/inspection/{insp_id}/edit")
async def create_or_update_inspection(
    request: Request,
    db: Session = Depends(get_db),
    insp_id: Optional[UUID] = None,
    # --- (!!!) 接收表單欄位 (!!!) ---
    vehicle_id: Optional[UUID] = Form(None), 
    kind: InspectionKind = Form(...),
    notification_date: Optional[date] = Form(None),
    deadline_date: Optional[date] = Form(None),
    inspected_on: Optional[date] = Form(None),
    return_date: Optional[date] = Form(None),
    user_id: Optional[str] = Form(None),
    handler_id: Optional[str] = Form(None),
    amount: Optional[Decimal] = Form(None),
    is_reconciled: bool = Form(False),
    result: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    handler_notes: Optional[str] = Form(None),
    notification_source: Optional[str] = Form(None),
    next_due_on: Optional[date] = Form(None)
):
    """ 處理檢驗紀錄的「新增」或「儲存」 """

    user_uuid = UUID(user_id) if user_id else None
    handler_uuid = UUID(handler_id) if handler_id else None

    if insp_id:
        # 編輯模式
        insp = db.get(Inspection, insp_id)
        if not insp:
            raise HTTPException(status_code=404, detail="Inspection record not found")
    else:
        # 新增模式
        if not vehicle_id:
             raise HTTPException(status_code=400, detail="必須選擇一輛車")
        insp = Inspection()
        insp.vehicle_id = vehicle_id
        db.add(insp)

    # 更新欄位
    insp.kind = kind
    insp.notification_date = notification_date
    insp.deadline_date = deadline_date
    insp.inspected_on = inspected_on
    insp.return_date = return_date
    insp.user_id = user_uuid
    insp.handler_id = handler_uuid
    insp.amount = amount
    insp.is_reconciled = is_reconciled
    insp.result = result
    insp.notes = notes
    insp.handler_notes = handler_notes
    insp.notification_source = notification_source
    insp.next_due_on = next_due_on

    try:
        # (!!!) 自動建立費用 (!!!)
        if amount and amount > 0:
            fee_user_id = handler_uuid if handler_uuid else user_uuid

            new_fee = Fee(
                vehicle_id=insp.vehicle_id,
                user_id=fee_user_id,
                receive_date=inspected_on or notification_date,
                request_date=inspected_on or notification_date,
                fee_type=FeeType.inspection_fee,
                amount=amount,
                is_paid=is_reconciled,
                notes=f"自動建立 - 檢驗費: {INSPECTION_KIND_MAP.get(kind.value, kind.value)}"
            )
            db.add(new_fee)

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發列表刷新
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshInspectionList, refreshInspectionListAll"}
    )

@app.delete("/inspection/{insp_id}/delete")
async def delete_inspection(
    insp_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除一筆檢驗紀錄 """
    insp = db.get(Inspection, insp_id)
    if not insp:
        return Response(status_code=200)

    try:
        db.delete(insp)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")

    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshInspectionList, refreshInspectionListAll"}
    )

# --- 費用紀錄 CRUD ---
@app.get("/fee-management")
async def get_fee_page(request: Request):
    """ 渲染「費用管理 (全列表)」的主頁面 """
    return templates.TemplateResponse(
        name="pages/fee_management.html",
        context={"request": request}
    )

@app.get("/fee-list-all")
async def get_fee_list_all(
    request: Request,
    db: Session = Depends(get_db)
):
    """ 取得「所有」車輛/人員的費用列表 (片段) """
    stmt = (
        select(Fee)
        .options(
            joinedload(Fee.user), # 請款人
            joinedload(Fee.vehicle) # 關聯車輛
        )
        .order_by(desc(Fee.receive_date), desc(Fee.request_date))
    )
    fee_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/fee_list_all.html",
        context={
            "request": request,
            "fee_records": fee_records,
        }
    )

@app.get("/vehicle/{vehicle_id}/fee-list")
async def get_fee_list(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得「單一車輛」的費用列表 (片段) """
    stmt = (
        select(Fee)
        .where(Fee.vehicle_id == vehicle_id)
        .options(
            joinedload(Fee.user) # 請款人
        )
        .order_by(desc(Fee.receive_date), desc(Fee.request_date))
    )
    fee_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/fee_list.html",
        context={
            "request": request,
            "fee_records": fee_records,
            "vehicle_id": vehicle_id
        }
    )

@app.get("/fee/new")
@app.get("/fee/{fee_id}/edit")
async def get_fee_form(
    request: Request,
    vehicle_id: Optional[UUID] = None, # 來自車輛詳情頁
    fee_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """ 取得費用紀錄的「新增」或「編輯」表單 (Modal) """
    fee = None
    all_vehicles = None
    if fee_id:
        # 編輯模式
        fee = db.get(Fee, fee_id)
        if not fee:
            raise HTTPException(status_code=404, detail="Fee record not found")
        vehicle_id = fee.vehicle_id # 從紀錄取得 vehicle_id

    # 費用表單「永遠」需要所有車輛和員工
    all_vehicles = db.scalars(select(Vehicle).order_by(Vehicle.plate_no)).all()
    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()

    return templates.TemplateResponse(
        name="fragments/fee_form.html",
        context={
            "request": request,
            "fee": fee,
            "selected_vehicle_id": vehicle_id, 
            "all_employees": all_employees,
            "all_vehicles": all_vehicles,
            "fee_types": list(FeeType),
        }
    )

@app.post("/fee/new")
@app.post("/fee/{fee_id}/edit")
async def create_or_update_fee(
    request: Request,
    db: Session = Depends(get_db),
    fee_id: Optional[UUID] = None,
    # --- 接收表單欄位 ---
    # 費用模型的 vehicle_id 和 user_id 允許為 None
    vehicle_id: Optional[str] = Form(None), 
    user_id: Optional[str] = Form(None), 

    fee_type: FeeType = Form(...),
    amount: Optional[Decimal] = Form(None),
    receive_date: Optional[date] = Form(None),
    request_date: Optional[date] = Form(None),
    is_paid: bool = Form(False),
    invoice_number: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    """ 處理費用紀錄的「新增」或「儲存」 """

    vehicle_uuid = UUID(vehicle_id) if vehicle_id else None
    user_uuid = UUID(user_id) if user_id else None

    if fee_id:
        # 編輯模式
        fee = db.get(Fee, fee_id)
        if not fee:
            raise HTTPException(status_code=404, detail="Fee record not found")
    else:
        # 新增模式
        fee = Fee()
        db.add(fee)

    # 更新欄位
    fee.vehicle_id = vehicle_uuid
    fee.user_id = user_uuid
    fee.fee_type = fee_type
    fee.amount = amount
    fee.receive_date = receive_date
    fee.request_date = request_date
    fee.is_paid = is_paid
    fee.invoice_number = invoice_number
    fee.notes = notes

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發列表刷新
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshFeeList, refreshFeeListAll"}
    )

@app.delete("/fee/{fee_id}/delete")
async def delete_fee(
    fee_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除一筆費用紀錄 """
    fee = db.get(Fee, fee_id)
    if not fee:
        return Response(status_code=200)

    try:
        db.delete(fee)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")

    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshFeeList, refreshFeeListAll"}
    )
@app.get("/vehicle/{vehicle_id}/asset-log-list")
async def get_asset_log_list(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得「單一車輛」的資產日誌 (片段) """
    stmt = (
        select(VehicleAssetLog)
        .where(VehicleAssetLog.vehicle_id == vehicle_id)
        .options(joinedload(VehicleAssetLog.user))
        .order_by(desc(VehicleAssetLog.log_date))
    )
    asset_logs = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/asset_log_list.html",
        context={
            "request": request,
            "asset_logs": asset_logs,
            "vehicle_id": vehicle_id
        }
    )

@app.get("/asset-log/new")
@app.get("/asset-log/{log_id}/edit")
async def get_asset_log_form(
    request: Request,
    vehicle_id: Optional[UUID] = None, # 來自車輛詳情頁
    log_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """ 取得資產日誌的「新增」或「編輯」表單 (Modal) """
    log = None
    if log_id:
        log = db.get(VehicleAssetLog, log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Asset log not found")
        vehicle_id = log.vehicle_id # 編輯時鎖定 vehicle_id

    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()

    return templates.TemplateResponse(
        name="fragments/asset_log_form.html",
        context={
            "request": request,
            "log": log,
            "vehicle_id": vehicle_id, # 必須傳入，用於 POST
            "all_employees": all_employees,
            "asset_types": list(AssetType),
            "asset_statuses": list(AssetStatus),
        }
    )

@app.post("/asset-log/new")
@app.post("/asset-log/{log_id}/edit")
async def create_or_update_asset_log(
    request: Request,
    db: Session = Depends(get_db),
    log_id: Optional[UUID] = None,
    vehicle_id: UUID = Form(...), # 隱藏欄位
    user_id: Optional[str] = Form(None),
    asset_type: AssetType = Form(...),
    description: Optional[str] = Form(None),
    status: AssetStatus = Form(...),
    log_date: date = Form(...),
    notes: Optional[str] = Form(None)
):
    """ 處理資產日誌的「新增」或「儲存」 """

    user_uuid = UUID(user_id) if user_id else None

    if log_id:
        log = db.get(VehicleAssetLog, log_id)
        if not log:
            raise HTTPException(status_code=404, detail="Asset log not found")
    else:
        log = VehicleAssetLog()
        log.vehicle_id = vehicle_id
        db.add(log)

    # 更新欄位
    log.user_id = user_uuid
    log.asset_type = asset_type
    log.description = description
    log.status = status
    log.log_date = log_date
    log.notes = notes

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshAssetLogList"}
    )

@app.delete("/asset-log/{log_id}/delete")
async def delete_asset_log(
    log_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除一筆資產日誌 """
    log = db.get(VehicleAssetLog, log_id)
    if log:
        try:
            db.delete(log)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")

    return Response(status_code=200)


# --- (!!!) 任務 5 (Part B)：報廢管理 (!!!) ---
# 報廢管理比較特殊，一台車只有一筆紀錄，所以我們不
# 做列表，而是直接做「Get/Create/Update/Delete」

@app.get("/vehicle/{vehicle_id}/disposal-form")
async def get_disposal_form(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得「單一車輛」的報廢表單 (片段) """
    # 一台車只會有一筆報廢紀錄
    stmt = select(Disposal).where(Disposal.vehicle_id == vehicle_id)
    disposal = db.scalar(stmt)

    all_employees = db.scalars(select(Employee).order_by(Employee.name)).all()

    return templates.TemplateResponse(
        name="fragments/disposal_form.html",
        context={
            "request": request,
            "disposal": disposal,
            "vehicle_id": vehicle_id,
            "all_employees": all_employees
        }
    )

@app.post("/vehicle/{vehicle_id}/disposal-form")
async def create_or_update_disposal(
    request: Request,
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    # --- 接收表單欄位 ---
    user_id: Optional[str] = Form(None), # 原使用人
    disposed_on: date = Form(...),
    notification_date: Optional[date] = Form(None),
    final_mileage: Optional[int] = Form(None),
    reason: Optional[str] = Form(None)
):
    """ 儲存報廢紀錄，並更新車輛狀態 """

    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="找不到車輛")

    stmt = select(Disposal).where(Disposal.vehicle_id == vehicle_id)
    disposal = db.scalar(stmt)

    if not disposal:
        disposal = Disposal()
        disposal.vehicle_id = vehicle_id
        db.add(disposal)

    # 更新欄位
    disposal.user_id = UUID(user_id) if user_id else None
    disposal.disposed_on = disposed_on
    disposal.notification_date = notification_date
    disposal.final_mileage = final_mileage
    disposal.reason = reason

    # (!!!) 重要：同時更新車輛狀態 (!!!)
    vehicle.status = VehicleStatus.retired

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發「車輛列表」和「車輛詳情頁」刷新
    return Response(
        status_code=200,
        headers={
            "HX-Trigger": "refreshDisposalForm, refreshVehicleList, refreshVehicleDetailPage"
        }
    )

@app.delete("/disposal/{disp_id}/delete")
async def delete_disposal(
    disp_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除報廢紀錄 (取消報廢)，並更新車輛狀態 """
    disposal = db.get(Disposal, disp_id)
    if not disposal:
        return Response(status_code=200)

    vehicle = db.get(Vehicle, disposal.vehicle_id)

    try:
        if vehicle:
            # (!!!) 重要：將車輛狀態改回「啟用中」 (!!!)
            vehicle.status = VehicleStatus.active

        db.delete(disposal)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除失敗: {e}")

    # 觸發「車輛列表」和「車輛詳情頁」刷新
    return Response(
        status_code=200,
        headers={
            "HX-Trigger": "refreshDisposalForm, refreshVehicleList, refreshVehicleDetailPage"
        }
    )

# --- 附件管理 CRUD ---
@app.get("/attachments/manage/{entity_type}/{entity_id}")
async def get_attachments_manager(
    request: Request,
    entity_type: AttachmentEntity,
    entity_id: UUID,
    db: Session = Depends(get_db)
):
    """ 取得附件管理器的 Modal 彈窗 (包含列表和上傳表單) """

    # 查詢關聯的附件
    stmt = (
        select(Attachment)
        .where(
            (Attachment.entity_type == entity_type) &
            (Attachment.entity_id == entity_id)
        )
        .order_by(Attachment.uploaded_at.desc())
    )
    attachments = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/attachments_manager.html",
        context={
            "request": request,
            "attachments": attachments,
            "entity_type": entity_type,
            "entity_id": entity_id
        }
    )

@app.post("/attachment/upload")
async def upload_attachment(
    request: Request,
    db: Session = Depends(get_db),
    entity_type: AttachmentEntity = Form(...),
    entity_id: UUID = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """ 處理檔案上傳 """

    if not file:
        raise HTTPException(status_code=400, detail="沒有提供檔案")

    # 產生一個安全的檔案名稱
    # 格式: [entity_id]_[uuid].[extension]
    ext = Path(file.filename).suffix
    safe_filename = f"{entity_id}_{uuid4()}{ext}"
    file_path = UPLOAD_PATH / safe_filename

    # 儲存實體檔案
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"無法儲存檔案: {e}")
    finally:
        file.file.close()

    # 建立資料庫紀錄
    new_attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_name=file.filename, # 儲存原始檔名
        file_path=f"/uploads/{safe_filename}", # 儲存相對 URL 路徑
        description=description
    )
    db.add(new_attachment)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # (可選) 嘗試刪除已上傳的實體檔案
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # 觸發附件列表刷新
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshAttachmentsList"}
    )

@app.delete("/attachment/{attachment_id}/delete")
async def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db)
):
    """ 刪除一筆附件 (包含實體檔案) """

    att = db.get(Attachment, attachment_id)
    if not att:
        return Response(status_code=200) # 已被刪除

    # 1. 刪除實體檔案
    try:
        # 從 /uploads/filename.ext 取得 filename.ext
        file_name_on_disk = Path(att.file_path).name
        file_path = UPLOAD_PATH / file_name_on_disk

        if file_path.exists():
            file_path.unlink()
        else:
            print(f"警告：找不到要刪除的檔案 {file_path}")

    except Exception as e:
        print(f"刪除實體檔案失敗: {e}")
        # 注意：我們不中斷，即使檔案刪除失敗，還是要刪除資料庫紀錄

    # 2. 刪除資料庫紀錄
    try:
        db.delete(att)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"刪除資料庫紀錄失敗: {e}")

    # 觸發附件列表刷新
    return Response(
        status_code=200,
        headers={"HX-Trigger": "refreshAttachmentsList"}
    )

# --- 健康檢查 ---
@app.get("/health")
def health():
    return {"ok": True}