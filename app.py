# app.py
import os
from pathlib import Path
from uuid import UUID 
from typing import Optional 

from fastapi import (
    FastAPI, Request, Depends, Form, HTTPException, Response
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates 
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session, joinedload 

from models import (
    Base, Vehicle, Employee, 
    VehicleType, VehicleStatus
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


# --- 健康檢查 ---
@app.get("/health")
def health():
    return {"ok": True}