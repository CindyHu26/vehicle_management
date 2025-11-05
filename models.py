# models.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
Column, String, Integer, Date, DateTime, Numeric, Text,
ForeignKey, Enum, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import enum


Base = declarative_base()

# (!!!) 1. 為了讓 Vehicle.__str__ 能運作，將翻譯字典搬移到此 (!!!)
# (!!!) (這不會影響 admin_views.py，那裡會保留自己的版本) (!!!)
_VEHICLE_TYPE_MAP_FOR_MODEL = {
    "car": "小客車",
    "motorcycle": "機車",
    "van": "廂型車",
    "truck": "貨車",
    "ev_scooter": "電動機車",
}

# --- 核心模型 (員工) ---
class Employee(Base):
    __tablename__ = "employees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    name = Column(String(100), unique=True, nullable=False, info={"label": "姓名"})
    
    phone = Column(String(50), nullable=True, info={"label": "電話"})
    
    has_car_license = Column(Boolean, default=False, info={"label": "有汽車駕照"})
    has_motorcycle_license = Column(Boolean, default=False, info={"label": "有機車駕照"})
    is_handler = Column(Boolean, default=False, info={"label": "經手人"})

    def __str__(self) -> str:
        # (!!!) 2. 確保 __str__ 永遠回傳 name (!!!)
        return self.name or f"員工ID: {str(self.id)[:6]}"
    
# --- 核心模型 (車輛) ---
class VehicleType(str, enum.Enum):
    car = "car"
    motorcycle = "motorcycle"
    van = "van"
    truck = "truck"
    ev_scooter = "ev_scooter"

class VehicleStatus(str, enum.Enum):
    active = "active"
    maintenance = "maintenance"
    retired = "retired"

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    plate_no = Column(String, unique=True, nullable=False, info={"label": "車牌號碼"})
    company = Column(String(100), nullable=True, info={"label": "所屬公司/人員"}) 
    vehicle_type = Column(Enum(VehicleType), nullable=False, default=VehicleType.car, info={"label": "車輛類型"})
    make = Column(String, nullable=True, info={"label": "品牌"})
    model = Column(String, nullable=True, info={"label": "型號"})
    manufacture_date = Column(Date, nullable=True, info={"label": "出廠年月"}) 
    displacement_cc = Column(Integer, nullable=True, info={"label": "排氣量(cc)"})
    current_mileage = Column(Integer, nullable=True, info={"label": "目前最新公里數"})
    maintenance_interval = Column(Integer, nullable=True, info={"label": "保養基準(km)"})
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.active, info={"label": "狀態"})
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "主要使用人"})
    user = relationship("Employee", back_populates="vehicles") 
    
    maintenance = relationship("Maintenance", back_populates="vehicle", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="vehicle", cascade="all, delete-orphan")
    fees = relationship("Fee", back_populates="vehicle", cascade="all, delete-orphan")
    disposals = relationship("Disposal", back_populates="vehicle", cascade="all, delete-orphan")
    asset_logs = relationship("VehicleAssetLog", back_populates="vehicle", cascade="all, delete-orphan")

    def __str__(self) -> str:
        key = str(self.vehicle_type).split(".")[-1]
        vt = _VEHICLE_TYPE_MAP_FOR_MODEL.get(key, key)
        parts = [self.plate_no, vt, self.model or None]
        return " / ".join(filter(None, parts))

Employee.vehicles = relationship("Vehicle", order_by=Vehicle.id, back_populates="user")

# --- (v6) 資產日誌 ---
class AssetType(str, enum.Enum):
    key = "key"
    dashcam = "dashcam"
    etag = "etag"
    other = "other"

class AssetStatus(str, enum.Enum):
    assigned = "assigned"
    returned = "returned"
    lost = "lost"
    disposed = "disposed"

class VehicleAssetLog(Base):
    __tablename__ = "vehicle_asset_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "關聯車輛"})
    vehicle = relationship("Vehicle", back_populates="asset_logs")
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "保管人"})
    user = relationship("Employee", back_populates="asset_logs")
    asset_type = Column(Enum(AssetType), nullable=False, info={"label": "財產類型"})
    description = Column(String(200), nullable=True, info={"label": "財產描述"})
    status = Column(Enum(AssetStatus), nullable=False, info={"label": "狀態"})
    log_date = Column(Date, nullable=False, info={"label": "紀錄日期"}) 
    notes = Column(Text, nullable=True, info={"label": "備註"})

Employee.asset_logs = relationship("VehicleAssetLog", back_populates="user")

# --- (v12) 保養維修 (事件) ---
class MaintenanceCategory(str, enum.Enum):
    maintenance = "maintenance"
    repair = "repair"
    carwash = "carwash"
    deep_cleaning = "deep_cleaning" # (v8)
    ritual_cleaning = "ritual_cleaning" # (v8)

class Maintenance(Base):
    __tablename__ = "maintenance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    
    # (v7) 使用人 vs 處理人
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "當時使用人(可選)"})
    user = relationship("Employee", foreign_keys=[user_id], back_populates="maintenance_user_records")
    handler_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "行政處理人"})
    handler = relationship("Employee", foreign_keys=[handler_id], back_populates="maintenance_handler_records")
    
    category = Column(Enum(MaintenanceCategory), nullable=False, info={"label": "類別"})
    vendor = Column(String, nullable=True, info={"label": "廠商"})
    
    # (v11) 日期
    performed_on = Column(Date, nullable=True, info={"label": "執行日期"}) 
    return_date = Column(Date, nullable=True, info={"label": "牽車(回)日期"})
    
    # (v9) 里程
    service_target_km = Column(Integer, nullable=True, info={"label": "表定保養里程"})
    odometer_km = Column(Integer, nullable=True, info={"label": "當時實際里程"})
    
    # (v13) 自動關聯費用
    amount = Column(Numeric(12, 2), nullable=True, info={"label": "金額(填入會自動產生費用單)"})
    is_reconciled = Column(Boolean, default=False, info={"label": "已對帳(勾選會自動標記費用單)"})
    
    # (v10) 備註
    notes = Column(Text, nullable=True, info={"label": "維修細節(附註)"})
    handler_notes = Column(Text, nullable=True, info={"label": "聯絡事宜(備註-2)"})
    
    vehicle = relationship("Vehicle", back_populates="maintenance")

Employee.maintenance_user_records = relationship("Maintenance", foreign_keys=[Maintenance.user_id], back_populates="user")
Employee.maintenance_handler_records = relationship("Maintenance", foreign_keys=[Maintenance.handler_id], back_populates="handler")

# --- (v14) 檢驗 (事件) ---
class InspectionKind(str, enum.Enum):
    periodic = "periodic"
    emission = "emission"
    reinspection = "reinspection"

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})

    # (v7) 使用人 vs 處理人
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "當時使用人(可選)"})
    user = relationship("Employee", foreign_keys=[user_id], back_populates="inspection_user_records")
    handler_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "行政處理人"})
    handler = relationship("Employee", foreign_keys=[handler_id], back_populates="inspection_handler_records")
    
    kind = Column(Enum(InspectionKind), nullable=False, info={"label": "檢驗類型"})
    result = Column(String, nullable=True, info={"label": "結果"})
    
    # (v13) 追蹤日期
    notification_date = Column(Date, nullable=True, info={"label": "接收通知日期"})
    notification_source = Column(String(100), nullable=True, info={"label": "通知方式(告知者)"})
    deadline_date = Column(Date, nullable=True, info={"label": "最晚日期(期限)"})
    
    # (v12) 執行日期 (允許留空)
    inspected_on = Column(Date, nullable=True, info={"label": "實際驗車日期"})
    return_date = Column(Date, nullable=True, info={"label": "牽車(回)日期"})
    next_due_on = Column(Date, nullable=True, info={"label": "下次應驗日期"})
    
    # (v13) 自動關聯費用
    amount = Column(Numeric(12, 2), nullable=True, info={"label": "金額(填入會自動產生費用單)"})
    is_reconciled = Column(Boolean, default=False, info={"label": "已對帳(勾選會自動標記費用單)"})
    
    # (v10) 備註
    notes = Column(Text, nullable=True, info={"label": "檢驗細節(附註)"})
    handler_notes = Column(Text, nullable=True, info={"label": "聯絡事宜(備註)"})

    vehicle = relationship("Vehicle", back_populates="inspections")

Employee.inspection_user_records = relationship("Inspection", foreign_keys=[Inspection.user_id], back_populates="user")
Employee.inspection_handler_records = relationship("Inspection", foreign_keys=[Inspection.handler_id], back_populates="handler")

# --- (v7) 費用/請款 (帳單) ---
class FeeType(str, enum.Enum):
    # (v7) 擴充
    fuel_fee = "fuel_fee"
    parking = "parking"
    maintenance_service = "maintenance_service"
    repair_parts = "repair_parts"
    inspection_fee = "inspection_fee"
    supplies = "supplies"
    toll = "toll"
    license_tax = "license_tax"
    other = "other"

class Fee(Base):
    __tablename__ = "fees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    
    # (v7) 關聯
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=True, info={"label": "車輛(可選)"})
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "請款人"})
    
    # (v7) 新增欄位
    receive_date = Column(Date, nullable=True, info={"label": "收到單據日期"})
    request_date = Column(Date, nullable=True, info={"label": "請款日期"})
    invoice_number = Column(String(100), nullable=True, info={"label": "發票號碼"})
    
    fee_type = Column(Enum(FeeType), nullable=False, info={"label": "費用類型"})
    amount = Column(Numeric(12, 2), nullable=True, info={"label": "金額"})
    
    # (v7) 新增欄位
    is_paid = Column(Boolean, default=False, info={"label": "已給(已請款)"})
    
    period_start = Column(Date, nullable=True, info={"label": "費用區間(起)"})
    period_end = Column(Date, nullable=True, info={"label": "費用區間(迄)"})
    notes = Column(Text, nullable=True, info={"label": "備註/項目"})
    
    vehicle = relationship("Vehicle", back_populates="fees")
    user = relationship("Employee", foreign_keys=[user_id], back_populates="fee_records")

Employee.fee_records = relationship("Fee", foreign_keys=[Fee.user_id], back_populates="user")

# --- (v6) 報廢 ---
class Disposal(Base):
    __tablename__ = "disposals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    
    # (v5) 原使用人
    user_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True, info={"label": "原使用人"})
    user = relationship("Employee", back_populates="disposal_records")
    
    # (v6) 新增欄V欄位
    notification_date = Column(Date, nullable=True, info={"label": "告知報廢日期"})
    disposed_on = Column(Date, nullable=False, info={"label": "報廢日期"})
    final_mileage = Column(Integer, nullable=True, info={"label": "最終公里數"})
    
    reason = Column(Text, nullable=True, info={"label": "報廢原因"})
    vehicle = relationship("Vehicle", back_populates="disposals")

Employee.disposal_records = relationship("Disposal", back_populates="user")

# --- 附件 (v6) ---
class AttachmentEntity(str, enum.Enum):
    vehicle = "vehicle"
    maintenance = "maintenance"
    disposal = "disposal"
    inspection = "inspection" 
    fee = "fee"
    employee = "employee"
    asset_log = "asset_log"

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    entity_type = Column(Enum(AttachmentEntity), nullable=False, info={"label": "關聯類型"})
    entity_id = Column(UUID(as_uuid=True), nullable=False, info={"label": "關聯ID"})
    file_name = Column(String, nullable=False, info={"label": "原始檔名"})
    file_path = Column(String, nullable=False, info={"label": "儲存路徑"})
    description = Column(Text, nullable=True, info={"label": "檔案說明"})
    uploaded_at = Column(DateTime, default=datetime.utcnow, info={"label": "上傳時間"})