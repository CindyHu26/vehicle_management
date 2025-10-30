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
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    plate_no = Column(String, unique=True, nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False, default=VehicleType.car)
    make = Column(String)
    model = Column(String)
    year = Column(Integer)
    displacement_cc = Column(Integer)
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.active)
    maintenance = relationship("Maintenance", back_populates="vehicle", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="vehicle", cascade="all, delete-orphan")
    fees = relationship("Fee", back_populates="vehicle", cascade="all, delete-orphan")
    disposals = relationship("Disposal", back_populates="vehicle", cascade="all, delete-orphan")

class MaintenanceCategory(str, enum.Enum):
    maintenance = "maintenance"
    repair = "repair"
    carwash = "carwash"

class Maintenance(Base):
    __tablename__ = "maintenance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    category = Column(Enum(MaintenanceCategory), nullable=False)
    vendor = Column(String)
    performed_on = Column(Date, nullable=False)
    odometer_km = Column(Numeric(10, 1))
    amount = Column(Numeric(12, 2))
    notes = Column(Text)
    vehicle = relationship("Vehicle", back_populates="maintenance")

class InspectionKind(str, enum.Enum):
    periodic = "periodic"
    emission = "emission"
    reinspection = "reinspection"

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    kind = Column(Enum(InspectionKind), nullable=False)
    result = Column(String)
    inspected_on = Column(Date, nullable=False)
    next_due_on = Column(Date)
    notes = Column(Text)
    vehicle = relationship("Vehicle", back_populates="inspections")

class FeeType(str, enum.Enum):
    license_tax = "license_tax"
    fuel_fee = "fuel_fee"
    parking = "parking"
    toll = "toll"
    other = "other"

class Fee(Base):
    __tablename__ = "fees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    fee_type = Column(Enum(FeeType), nullable=False)
    period_start = Column(Date)
    period_end = Column(Date)
    amount = Column(Numeric(12, 2))
    paid_on = Column(Date)
    notes = Column(Text)
    vehicle = relationship("Vehicle", back_populates="fees")

class Disposal(Base):
    __tablename__ = "disposals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    disposed_on = Column(Date, nullable=False)
    reason = Column(Text)
    vehicle = relationship("Vehicle", back_populates="disposals")

class AttachmentEntity(str, enum.Enum):
    vehicle = "vehicle"
    maintenance = "maintenance"
    disposal = "disposal"

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type = Column(Enum(AttachmentEntity), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    description = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)