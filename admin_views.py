# admin_views.py

from sqladmin import ModelView
from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)
from typing import Any
from markupsafe import Markup

# --- Enum 中文翻譯字典 (不變) ---
VEHICLE_TYPE_MAP = {
    VehicleType.car: "小客車",
    VehicleType.motorcycle: "機車",
    VehicleType.van: "廂型車",
    VehicleType.truck: "貨車",
    VehicleType.ev_scooter: "電動機車",
}
VEHICLE_STATUS_MAP = {
    VehicleStatus.active: "啟用中",
    VehicleStatus.maintenance: "維修中",
    VehicleStatus.retired: "已報廢",
}
MAINTENANCE_CATEGORY_MAP = {
    MaintenanceCategory.maintenance: "定期保養",
    MaintenanceCategory.repair: "維修",
    MaintenanceCategory.carwash: "洗車",
}
INSPECTION_KIND_MAP = {
    InspectionKind.periodic: "定期檢驗",
    InspectionKind.emission: "排氣檢驗",
    InspectionKind.reinspection: "複驗",
}
FEE_TYPE_MAP = {
    FeeType.license_tax: "牌照稅",
    FeeType.fuel_fee: "燃料費",
    FeeType.parking: "停車費",
    FeeType.toll: "過路費",
    FeeType.other: "其他",
}
ATTACHMENT_ENTITY_MAP = {
    AttachmentEntity.vehicle: "車輛",
    AttachmentEntity.maintenance: "保養維M修",
    AttachmentEntity.disposal: "報廢",
    AttachmentEntity.inspection: "檢驗",
    AttachmentEntity.fee: "費用",
}

# --- 格式化函式 (不變) ---
def format_vehicle_type(value: VehicleType) -> str:
    return VEHICLE_TYPE_MAP.get(value, str(value))

def format_vehicle_status(value: VehicleStatus) -> str:
    if value == VehicleStatus.active:
        return Markup(f'<span class="badge bg-success">{VEHICLE_STATUS_MAP.get(value)}</span>')
    if value == VehicleStatus.maintenance:
        return Markup(f'<span class="badge bg-warning">{VEHICLE_STATUS_MAP.get(value)}</span>')
    if value == VehicleStatus.retired:
        return Markup(f'<span class="badge bg-danger">{VEHICLE_STATUS_MAP.get(value)}</span>')
    return VEHICLE_STATUS_MAP.get(value, str(value))

def format_maintenance_category(value: MaintenanceCategory) -> str:
    return MAINTENANCE_CATEGORY_MAP.get(value, str(value))

def format_inspection_kind(value: InspectionKind) -> str:
    return INSPECTION_KIND_MAP.get(value, str(value))

def format_fee_type(value: FeeType) -> str:
    return FEE_TYPE_MAP.get(value, str(value))

def format_attachment_entity(value: AttachmentEntity) -> str:
    return ATTACHMENT_ENTITY_MAP.get(value, str(value))

def format_attachment_link(value: str) -> Markup:
    if value:
        return Markup(f'<a href="/uploads/{value}" target="_blank">{value}</a>')
    return ""


# --- Admin Views (移除篩選器) ---

class VehicleAdmin(ModelView, model=Vehicle):
    name = "車輛"
    name_plural = "車輛管理"
    icon = "fa-solid fa-car"
    
    column_list = [
        Vehicle.plate_no, 
        Vehicle.vehicle_type, 
        Vehicle.make, 
        Vehicle.model, 
        Vehicle.year, 
        Vehicle.status
    ]
    column_formatters = {
        Vehicle.vehicle_type: format_vehicle_type,
        Vehicle.status: format_vehicle_status,
    }
    column_details_formatters = {
        Vehicle.vehicle_type: format_vehicle_type,
        Vehicle.status: format_vehicle_status,
    }
    column_searchable_list = [Vehicle.plate_no, Vehicle.make, Vehicle.model]
    
    # (!!! 修正 !!!) 註解掉 column_filters 來修復舊版本的 Bug
    # column_filters = ["vehicle_type", "status", "year"] 
    
    form_columns = [
        Vehicle.plate_no,
        Vehicle.vehicle_type,
        Vehicle.status,
        Vehicle.make,
        Vehicle.model,
        Vehicle.year,
        Vehicle.displacement_cc,
    ]


class MaintenanceAdmin(ModelView, model=Maintenance):
    name = "保養維修"
    name_plural = "保養維修紀錄"
    icon = "fa-solid fa-wrench"
    
    column_list = [
        Maintenance.vehicle,
        Maintenance.category, 
        Maintenance.performed_on, 
        Maintenance.amount, 
        Maintenance.vendor,
        Maintenance.odometer_km,
    ]
    column_formatters = {
        Maintenance.category: format_maintenance_category,
    }
    column_details_formatters = {
        Maintenance.category: format_maintenance_category,
    }
    column_searchable_list = [Maintenance.vendor]
    
    # (!!! 修正 !!!) 註解掉 column_filters
    # column_filters = ["category", "performed_on", "vehicle"]


class InspectionAdmin(ModelView, model=Inspection):
    name = "檢驗"
    name_plural = "檢驗紀錄"
    icon = "fa-solid fa-clipboard-check"
    
    column_list = [
        Inspection.vehicle, 
        Inspection.kind, 
        Inspection.inspected_on, 
        Inspection.next_due_on, 
        Inspection.result
    ]
    column_formatters = {
        Inspection.kind: format_inspection_kind,
    }
    column_details_formatters = {
        Inspection.kind: format_inspection_kind,
    }
    
    # (!!! 修正 !!!) 註解掉 column_filters
    # column_filters = ["kind", "inspected_on", "next_due_on", "vehicle"]

class FeeAdmin(ModelView, model=Fee):
    name = "費用"
    name_plural = "稅費管理"
    icon = "fa-solid fa-dollar-sign"
    
    column_list = [
        Fee.vehicle, 
        Fee.fee_type, 
        Fee.period_start, 
        Fee.period_end, 
        Fee.amount, 
        Fee.paid_on
    ]
    column_formatters = {
        Fee.fee_type: format_fee_type,
    }
    column_details_formatters = {
        Fee.fee_type: format_fee_type,
    }
    
    # (!!! 修正 !!!) 註解掉 column_filters
    # column_filters = ["fee_type", "paid_on", "vehicle"]


class DisposalAdmin(ModelView, model=Disposal):
    name = "報廢"
    name_plural = "報廢紀錄"
    icon = "fa-solid fa-trash"
    column_list = [Disposal.vehicle, Disposal.disposed_on, Disposal.reason]
    
    # (!!! 修正 !!!) 註解掉 column_filters
    # column_filters = ["disposed_on", "vehicle"]


class AttachmentAdmin(ModelView, model=Attachment):
    name = "附件"
    name_plural = "所有附件"
    icon = "fa-solid fa-paperclip"
    
    can_create = False
    can_edit = False
    
    column_list = [
        Attachment.entity_type, 
        Attachment.entity_id, 
        Attachment.file_name,
        Attachment.file_path,
        Attachment.uploaded_at
    ]
    column_details_list = [
        Attachment.id,
        Attachment.entity_type,
        Attachment.entity_id,
        Attachment.file_name,
        Attachment.file_path,
        Attachment.description,
        Attachment.uploaded_at,
    ]
    column_formatters = {
        Attachment.entity_type: format_attachment_entity,
        Attachment.file_path: format_attachment_link,
    }
    column_details_formatters = {
        Attachment.entity_type: format_attachment_entity,
        Attachment.file_path: format_attachment_link,
    }

    # (!!! 修正 !!!) 註解掉 column_filters
    # column_filters = ["entity_type"]