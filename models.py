# models.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
Column, String, Integer, Date, DateTime, Numeric, Text,
ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import enum


Base = declarative_base()

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
    vehicle_type = Column(Enum(VehicleType), nullable=False, default=VehicleType.car, info={"label": "車輛類型"})
    make = Column(String, info={"label": "品牌"})
    model = Column(String, info={"label": "型號"})
    year = Column(Integer, info={"label": "年份"})
    displacement_cc = Column(Integer, info={"label": "排氣量(cc)"})
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.active, info={"label": "狀態"})
    
    # 關聯
    maintenance = relationship("Maintenance", back_populates="vehicle", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="vehicle", cascade="all, delete-orphan")
    fees = relationship("Fee", back_populates="vehicle", cascade="all, delete-orphan")
    disposals = relationship("Disposal", back_populates="vehicle", cascade="all, delete-orphan")
    
    def __str__(self) -> str:
        # 讓下拉選單顯示車牌，而不是 <Vehicle object ...>
        return self.plate_no


class MaintenanceCategory(str, enum.Enum):
    maintenance = "maintenance"
    repair = "repair"
    carwash = "carwash"

class Maintenance(Base):
    __tablename__ = "maintenance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    category = Column(Enum(MaintenanceCategory), nullable=False, info={"label": "類別"})
    vendor = Column(String, info={"label": "廠商"})
    performed_on = Column(Date, nullable=False, info={"label": "執行日期"})
    odometer_km = Column(Numeric(10, 1), info={"label": "當時里程(km)"})
    amount = Column(Numeric(12, 2), info={"label": "金額"})
    notes = Column(Text, info={"label": "備註"})
    vehicle = relationship("Vehicle", back_populates="maintenance")

class InspectionKind(str, enum.Enum):
    periodic = "periodic"
    emission = "emission"
    reinspection = "reinspection"

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    kind = Column(Enum(InspectionKind), nullable=False, info={"label": "檢驗類型"})
    result = Column(String, info={"label": "結果"})
    inspected_on = Column(Date, nullable=False, info={"label": "檢驗日期"})
    next_due_on = Column(Date, info={"label": "下次應驗日期"})
    notes = Column(Text, info={"label": "備註"})
    vehicle = relationship("Vehicle", back_populates="inspections")

class FeeType(str, enum.Enum):
    license_tax = "license_tax"
    fuel_fee = "fuel_fee"
    parking = "parking"
    toll = "toll"
    other = "other"

class Fee(Base):
    __tablename__ = "fees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    fee_type = Column(Enum(FeeType), nullable=False, info={"label": "費用類型"})
    period_start = Column(Date, info={"label": "費用區間(起)"})
    period_end = Column(Date, info={"label": "費用區間(迄)"})
    amount = Column(Numeric(12, 2), info={"label": "金額"})
    paid_on = Column(Date, info={"label": "繳費日期"})
    notes = Column(Text, info={"label": "備註"})
    vehicle = relationship("Vehicle", back_populates="fees")

class Disposal(Base):
    __tablename__ = "disposals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, info={"label": "車輛"})
    disposed_on = Column(Date, nullable=False, info={"label": "報廢日期"})
    reason = Column(Text, info={"label": "報廢原因"})
    vehicle = relationship("Vehicle", back_populates="disposals")

class AttachmentEntity(str, enum.Enum):
    vehicle = "vehicle"
    maintenance = "maintenance"
    disposal = "disposal"
    inspection = "inspection" # 您可以新增
    fee = "fee"             # 您可以新增

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, info={"label": "ID"})
    entity_type = Column(Enum(AttachmentEntity), nullable=False, info={"label": "關聯類型"})
    entity_id = Column(UUID(as_uuid=True), nullable=False, info={"label": "關聯ID"})
    file_name = Column(String, nullable=False, info={"label": "原始檔名"})
    file_path = Column(String, nullable=False, info={"label": "儲存路徑"})
    description = Column(Text, info={"label": "檔案說明"})
    uploaded_at = Column(DateTime, default=datetime.utcnow, info={"label": "上傳時間"})