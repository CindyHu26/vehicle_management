# app.py
import os
from pathlib import Path
from uuid import UUID 
from typing import Optional
from datetime import date
from decimal import Decimal

from fastapi import (
    FastAPI, Request, Depends, Form, HTTPException, Response
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates 
from sqlalchemy import create_engine, select, desc
from sqlalchemy.orm import sessionmaker, Session, joinedload 

from models import (
    Base, Vehicle, Employee, 
    VehicleType, VehicleStatus,
    Maintenance, MaintenanceCategory, Fee, FeeType
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

# --- 頁面路由 ---
@app.get("/")
async def get_main_page(request: Request):
    return templates.TemplateResponse(
        name="base.html",
        context={"request": request}
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
async def get_vehicles_list(request: Request, db: Session = Depends(get_db)):
    stmt = (
        select(Vehicle)
        .options(joinedload(Vehicle.user)) 
        .order_by(Vehicle.plate_no)
    )
    vehicles = db.scalars(stmt).all()
    
    return templates.TemplateResponse(
        name="fragments/vehicle_list.html",
        context={
            "request": request,
            "vehicles": vehicles
        }
    )

# --- 列表 API (員工) ---
@app.get("/employees-list")
async def get_employees_list(request: Request, db: Session = Depends(get_db)):
    stmt = select(Employee).order_by(Employee.name)
    employees = db.scalars(stmt).all()
    
    return templates.TemplateResponse(
        name="fragments/employee_list.html",
        context={
            "request": request,
            "employees": employees
        }
    )


# --- (!!!) 車輛 CRUD (!!!) ---

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
    
    # (!!!) 1. 補上缺失的 commit (!!!)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")
    
    # (!!!) 2. 補上缺失的 HX-Trigger (!!!)
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

# --- (!!!) 員工 CRUD (!!!) ---

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
    has_motorcycle_license: bool = Form(False)
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
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"資料庫錯誤: {e}")

    # (!!!) 觸發「員工」列表刷新 (!!!)
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
    db: Session = Depends(get_db)
):
    """ 取得「所有」車輛的保養列表 (片段) """
    stmt = (
        select(Maintenance)
        .options(
            joinedload(Maintenance.user), 
            joinedload(Maintenance.handler),
            joinedload(Maintenance.vehicle) # (!!!) 需要額外 join 車輛
        )
        .order_by(desc(Maintenance.performed_on)) # 依執行日期倒序
    )
    maintenance_records = db.scalars(stmt).all()

    return templates.TemplateResponse(
        name="fragments/maintenance_list_all.html", # 我們即將建立這個檔案
        context={
            "request": request,
            "maintenance_records": maintenance_records,
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

    return templates.TemplateResponse(
        name="fragments/maintenance_form.html",
        context={
            "request": request,
            "maint": maint,
            # 傳遞預選的 vehicle_id (無論是來自查詢參數還是編輯模式)
            "selected_vehicle_id": vehicle_id, 
            "all_employees": all_employees,
            "all_vehicles": all_vehicles, # 傳遞所有車輛 (僅限新增模式)
            "maintenance_categories": list(MaintenanceCategory),
        }
    )

# 保養管理主頁面
@app.get("/maintenance-management")
async def get_maintenance_page(request: Request):
    return templates.TemplateResponse(
        name="pages/maintenance_management.html",
        context={"request": request}
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

            # 費用請款人優先抓「行政處理人」，其次抓「當時使用人」
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

# --- 健康檢查 ---
@app.get("/health")
def health():
    return {"ok": True}