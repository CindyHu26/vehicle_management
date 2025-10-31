# admin_views.py

from sqladmin import ModelView
from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment, Employee, 
    VehicleAssetLog, AssetType, AssetStatus,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)
from typing import Any
from markupsafe import Markup

# --- (v13) Enum 中文翻譯字典 ---
VEHICLE_TYPE_MAP = {
    "car": "小客車",
    "motorcycle": "機車",
    "van": "廂型車",
    "truck": "貨車",
    "ev_scooter": "電動機車",
}
VEHICLE_STATUS_MAP = {
    "active": "啟用中",
    "maintenance": "維修中",
    "retired": "已報廢",
}
MAINTENANCE_CATEGORY_MAP = {
    "maintenance": "定期保養",
    "repair": "維修",
    "carwash": "洗車",
    "deep_cleaning": "深度清潔",
    "ritual_cleaning": "淨車(習俗)",
}
INSPECTION_KIND_MAP = {
    "periodic": "定期檢驗",
    "emission": "排氣檢驗",
    "reinspection": "複驗",
}
FEE_TYPE_MAP = {
    "license_tax": "牌照稅",
    "fuel_fee": "加油費",
    "parking": "停車費",
    "toll": "過路費",
    "maintenance_service": "保養服務費",
    "repair_parts": "零件/維修費",
    "inspection_fee": "汽車檢驗費",
    "supplies": "用品/雜支",
    "other": "其他",
}
ATTACHMENT_ENTITY_MAP = {
    "vehicle": "車輛",
    "maintenance": "保養維修",
    "disposal": "報廢",
    "inspection": "檢驗",
    "fee": "費用",
    "employee": "員工",
    "asset_log": "資產",
}
ASSET_TYPE_MAP = {
    "key": "鑰匙",
    "dashcam": "行車紀錄器",
    "etag": "eTag",
    "other": "其他",
}
ASSET_STATUS_MAP = {
    "assigned": "已指派",
    "returned": "已收回",
    "lost": "遺失",
    "disposed": "報廢",
}


# --- 格式化函式 ---
# (!!! 修正 !!!) 增加 str(value) 轉換，提高舊版相容性
def format_vehicle_type(value: VehicleType) -> str:
    return VEHICLE_TYPE_MAP.get(str(value), str(value))
def format_vehicle_status(value: VehicleStatus) -> str:
    val_str = str(value)
    if val_str == "active":
        return Markup(f'<span class="badge bg-success">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    if val_str == "maintenance":
        return Markup(f'<span class="badge bg-warning">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    if val_str == "retired":
        return Markup(f'<span class="badge bg-danger">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    return VEHICLE_STATUS_MAP.get(val_str, val_str)
def format_maintenance_category(value: MaintenanceCategory) -> str:
    return MAINTENANCE_CATEGORY_MAP.get(str(value), str(value))
def format_inspection_kind(value: InspectionKind) -> str:
    return INSPECTION_KIND_MAP.get(str(value), str(value))
def format_fee_type(value: FeeType) -> str:
    return FEE_TYPE_MAP.get(str(value), str(value))
def format_attachment_entity(value: AttachmentEntity) -> str:
    return ATTACHMENT_ENTITY_MAP.get(str(value), str(value))
def format_attachment_link(value: str) -> Markup:
    if value:
        return Markup(f'<a href="/uploads/{value}" target="_blank">{value}</a>')
    return ""
def format_asset_type(value: AssetType) -> str:
    return ASSET_TYPE_MAP.get(str(value), str(value))
def format_asset_status(value: AssetStatus) -> str:
    val_str = str(value)
    if val_str == "assigned":
        return Markup(f'<span class="badge bg-info">{ASSET_STATUS_MAP.get(val_str)}</span>')
    if val_str == "returned":
        return Markup(f'<span class="badge bg-secondary">{ASSET_STATUS_MAP.get(val_str)}</span>')
    return ASSET_STATUS_MAP.get(val_str, val_str)

# --- Admin Views (移除篩選器) ---

class EmployeeAdmin(ModelView, model=Employee):
    name = "員工"
    name_plural = "員工管理"
    icon = "fa-solid fa-users"
    column_list = [Employee.name, Employee.phone, Employee.has_car_license, Employee.has_motorcycle_license]
    column_searchable_list = [Employee.name]
    form_columns = [Employee.name, Employee.phone, Employee.has_car_license, Employee.has_motorcycle_license]
    

class VehicleAdmin(ModelView, model=Vehicle):
    name = "車輛"
    name_plural = "車輛管理"
    icon = "fa-solid fa-car"
    column_list = [
        Vehicle.plate_no,
        Vehicle.company, 
        Vehicle.vehicle_type,
        Vehicle.user, 
        Vehicle.model, 
        Vehicle.manufacture_date,
        Vehicle.current_mileage,
        Vehicle.maintenance_interval,
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
    column_searchable_list = [Vehicle.plate_no, Vehicle.make, Vehicle.model, Vehicle.company]
    # column_filters = ["company", "vehicle_type", "status", "user"] 
    form_columns = [
        Vehicle.plate_no,
        Vehicle.company, 
        Vehicle.vehicle_type,
        Vehicle.status,
        Vehicle.user, 
        Vehicle.make,
        Vehicle.model,
        Vehicle.manufacture_date, 
        Vehicle.displacement_cc,
        Vehicle.current_mileage,
        Vehicle.maintenance_interval,
    ]

class VehicleAssetLogAdmin(ModelView, model=VehicleAssetLog):
    name = "車輛資產"
    name_plural = "車輛資產日誌"
    icon = "fa-solid fa-key"
    column_list = [
        VehicleAssetLog.vehicle,
        VehicleAssetLog.log_date,
        VehicleAssetLog.asset_type,
        VehicleAssetLog.description,
        VehicleAssetLog.status,
        VehicleAssetLog.user, # 保管人
    ]
    column_formatters = {
        VehicleAssetLog.asset_type: format_asset_type,
        VehicleAssetLog.status: format_asset_status,
    }
    column_details_formatters = {
        VehicleAssetLog.asset_type: format_asset_type,
        VehicleAssetLog.status: format_asset_status,
    }
    column_searchable_list = [VehicleAssetLog.description]
    # column_filters = ["vehicle", "log_date", "asset_type", "status", "user"]
    form_columns = [
        VehicleAssetLog.vehicle,
        VehicleAssetLog.log_date,
        VehicleAssetLog.asset_type,
        VehicleAssetLog.description,
        VehicleAssetLog.status,
        VehicleAssetLog.user,
        VehicleAssetLog.notes,
    ]

class MaintenanceAdmin(ModelView, model=Maintenance):
    name = "保養維修"
    name_plural = "保養維修紀錄"
    icon = "fa-solid fa-wrench"
    column_list = [
        Maintenance.vehicle,
        Maintenance.user, # 當時使用人
        Maintenance.handler, # 行政處理人
        Maintenance.category, 
        Maintenance.performed_on, 
        Maintenance.return_date,
        Maintenance.odometer_km,
        Maintenance.amount, 
        Maintenance.is_reconciled,
    ]
    column_formatters = {
        Maintenance.category: format_maintenance_category,
    }
    column_details_formatters = {
        Maintenance.category: format_maintenance_category,
    }
    column_searchable_list = [Maintenance.vendor, Maintenance.notes, Maintenance.handler_notes]
    # column_filters = ["category", "performed_on", "vehicle", "user", "handler"]
    form_columns = [
        Maintenance.vehicle,
        Maintenance.user,
        Maintenance.handler,
        Maintenance.category,
        Maintenance.vendor,
        Maintenance.performed_on,
        Maintenance.return_date,
        Maintenance.service_target_km,
        Maintenance.odometer_km,
        Maintenance.amount,
        Maintenance.is_reconciled,
        Maintenance.notes,
        Maintenance.handler_notes,
    ]

class InspectionAdmin(ModelView, model=Inspection):
    name = "檢驗"
    name_plural = "檢驗紀錄"
    icon = "fa-solid fa-clipboard-check"
    column_list = [
        Inspection.vehicle, 
        Inspection.handler,
        Inspection.kind, 
        Inspection.notification_date,
        Inspection.deadline_date,
        Inspection.inspected_on, 
        Inspection.result,
        Inspection.amount,
        Inspection.is_reconciled,
    ]
    column_formatters = {
        Inspection.kind: format_inspection_kind,
    }
    column_details_formatters = {
        Inspection.kind: format_inspection_kind,
    }
    # column_filters = ["kind", "notification_date", "deadline_date", "inspected_on", "vehicle"]
    form_columns = [
        Inspection.vehicle,
        Inspection.user,
        Inspection.handler,
        Inspection.kind,
        Inspection.result,
        Inspection.notification_date,
        Inspection.notification_source,
        Inspection.deadline_date,
        Inspection.inspected_on,
        Inspection.return_date,
        Inspection.next_due_on,
        Inspection.amount,
        Inspection.is_reconciled,
        Inspection.notes,
        Inspection.handler_notes,
    ]

class FeeAdmin(ModelView, model=Fee):
    name = "費用"
    name_plural = "費用請款"
    icon = "fa-solid fa-dollar-sign"
    column_list = [
        Fee.user,
        Fee.vehicle, 
        Fee.fee_type, 
        Fee.amount, 
        Fee.request_date,
        Fee.is_paid,
        Fee.invoice_number,
    ]
    column_formatters = {
        Fee.fee_type: format_fee_type,
    }
    column_details_formatters = {
        Fee.fee_type: format_fee_type,
    }
    # column_filters = ["fee_type", "request_date", "is_paid", "vehicle", "user"]
    form_columns = [
        Fee.user,
        Fee.vehicle,
        Fee.fee_type,
        Fee.receive_date,
        Fee.request_date,
        Fee.invoice_number,
        Fee.amount,
        Fee.is_paid,
        Fee.period_start,
        Fee.period_end,
        Fee.notes,
    ]

class DisposalAdmin(ModelView, model=Disposal):
    name = "報廢"
    name_plural = "報廢紀錄"
    icon = "fa-solid fa-trash"
    column_list = [Disposal.vehicle, Disposal.user, Disposal.notification_date, Disposal.disposed_on, Disposal.final_mileage]
    # column_filters = ["disposed_on", "vehicle", "user"]
    form_columns = [
        Disposal.vehicle,
        Disposal.user,
        Disposal.notification_date,
        Disposal.disposed_on,
        Disposal.final_mileage,
        Disposal.reason,
    ]

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
    # column_filters = ["entity_type"]