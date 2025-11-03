# admin_views.py
import enum
from typing import Any
from markupsafe import Markup

from starlette_admin.contrib.sqla import ModelView

from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment, Employee, 
    VehicleAssetLog, AssetType, AssetStatus,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)

# --- (v13) Enum 中文翻譯字典 (這部分保持不變) ---
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


# --- 格式化函式 (!!! 修正：處理 Enum 物件 !!!) ---

def _get_enum_value(value: Any) -> str:
    """輔助函式：安全地取得 Enum 的 value，如果不是 Enum 則轉為 str"""
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)

def format_vehicle_type(value: Any) -> str:
    val_str = _get_enum_value(value)
    return VEHICLE_TYPE_MAP.get(val_str, val_str)

def format_vehicle_status(value: Any) -> str:
    val_str = _get_enum_value(value)
    if val_str == "active":
        return Markup(f'<span class="badge bg-success">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    if val_str == "maintenance":
        return Markup(f'<span class="badge bg-warning">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    if val_str == "retired":
        return Markup(f'<span class="badge bg-danger">{VEHICLE_STATUS_MAP.get(val_str)}</span>')
    return VEHICLE_STATUS_MAP.get(val_str, val_str)

def format_maintenance_category(value: Any) -> str:
    val_str = _get_enum_value(value)
    return MAINTENANCE_CATEGORY_MAP.get(val_str, val_str)

def format_inspection_kind(value: Any) -> str:
    val_str = _get_enum_value(value)
    return INSPECTION_KIND_MAP.get(val_str, val_str)

def format_fee_type(value: Any) -> str:
    val_str = _get_enum_value(value)
    return FEE_TYPE_MAP.get(val_str, val_str)

def format_attachment_entity(value: Any) -> str:
    val_str = _get_enum_value(value)
    return ATTACHMENT_ENTITY_MAP.get(val_str, val_str)

def format_attachment_link(value: Any) -> Markup:
    val_str = str(value)
    if val_str:
        return Markup(f'<a href="/uploads/{val_str}" target="_blank">{val_str}</a>')
    return ""

def format_asset_type(value: Any) -> str:
    val_str = _get_enum_value(value)
    return ASSET_TYPE_MAP.get(val_str, val_str)

def format_asset_status(value: Any) -> str:
    val_str = _get_enum_value(value)
    if val_str == "assigned":
        return Markup(f'<span class="badge bg-info">{ASSET_STATUS_MAP.get(val_str)}</span>')
    if val_str == "returned":
        return Markup(f'<span class="badge bg-secondary">{ASSET_STATUS_MAP.get(val_str)}</span>')
    return ASSET_STATUS_MAP.get(val_str, val_str)

# --- Admin Views (!!! 轉換為 starlette-admin !!!) ---

# (!!!) 
# (!!!) 我們將所有 Class 還原回「新語法」
# (!!!) (即 model=... 寫在 class(...) 括號內)
# (!!!) 這才是 starlette-admin 0.15.1 需要的語法
# (!!!)

class EmployeeAdmin(ModelView, model=Employee): # (!!!) 還原 (1/8)
    name = "employee" # 英文唯一值
    label = "員工管理" # 中文顯示
    icon = "fa-solid fa-users"
    
    # 列表頁欄位 (原 column_list)
    # 標籤會自動抓 models.py 裡的 info={"label": "..."}
    fields = [
        Employee.name, 
        Employee.phone, 
        Employee.has_car_license, 
        Employee.has_motorcycle_license
    ]
    
    # 搜尋欄位 (原 column_searchable_list)
    searchable_fields = [Employee.name]
    
    # 表單欄位 (原 form_columns)
    fields_for_form = [
        Employee.name, 
        Employee.phone, 
        Employee.has_car_license, 
        Employee.has_motorcycle_license
    ]
    

class VehicleAdmin(ModelView, model=Vehicle): # (!!!) 還原 (2/8)
    name = "vehicle"
    label = "車輛管理"
    icon = "fa-solid fa-car"
    
    # 列表頁欄位 (原 column_list)
    fields = [
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
    
    # 列表頁格式化 (原 column_formatters)
    list_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
    }
    
    # 詳情頁格式化 (原 column_details_formatters)
    detail_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
    }
    
    # 搜尋欄位 (原 column_searchable_list)
    searchable_fields = [Vehicle.plate_no, Vehicle.make, Vehicle.model, Vehicle.company]
    
    # 表單欄位 (原 form_columns)
    fields_for_form = [
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

class VehicleAssetLogAdmin(ModelView, model=VehicleAssetLog): # (!!!) 還原 (3/8)
    name = "vehicle_asset_log"
    label = "車輛資產日誌"
    icon = "fa-solid fa-key"
    
    fields = [
        VehicleAssetLog.vehicle,
        VehicleAssetLog.log_date,
        VehicleAssetLog.asset_type,
        VehicleAssetLog.description,
        VehicleAssetLog.status,
        VehicleAssetLog.user, # 保管人
    ]
    
    list_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
    }
    detail_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
    }
    
    searchable_fields = [VehicleAssetLog.description]
    
    fields_for_form = [
        VehicleAssetLog.vehicle,
        VehicleAssetLog.log_date,
        VehicleAssetLog.asset_type,
        VehicleAssetLog.description,
        VehicleAssetLog.status,
        VehicleAssetLog.user,
        VehicleAssetLog.notes,
    ]

class MaintenanceAdmin(ModelView, model=Maintenance): # (!!!) 還原 (4/8)
    name = "maintenance"
    label = "保養維修紀錄"
    icon = "fa-solid fa-wrench"
    
    fields = [
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
    
    list_formatters = {
        "category": format_maintenance_category,
    }
    detail_formatters = {
        "category": format_maintenance_category,
    }
    
    searchable_fields = [Maintenance.vendor, Maintenance.notes, Maintenance.handler_notes]
    
    fields_for_form = [
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

class InspectionAdmin(ModelView, model=Inspection): # (!!!) 還原 (5/8)
    name = "inspection"
    label = "檢驗紀錄"
    icon = "fa-solid fa-clipboard-check"
    
    fields = [
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
    
    list_formatters = {
        "kind": format_inspection_kind,
    }
    detail_formatters = {
        "kind": format_inspection_kind,
    }
    
    fields_for_form = [
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

class FeeAdmin(ModelView, model=Fee): # (!!!) 還原 (6/8)
    name = "fee"
    label = "費用請款"
    icon = "fa-solid fa-dollar-sign"
    
    fields = [
        Fee.user,
        Fee.vehicle, 
        Fee.fee_type, 
        Fee.amount, 
        Fee.request_date,
        Fee.is_paid,
        Fee.invoice_number,
    ]
    
    list_formatters = {
        "fee_type": format_fee_type,
    }
    detail_formatters = {
        "fee_type": format_fee_type, # (!!!) 修正打字錯誤
    }
    
    fields_for_form = [
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

class DisposalAdmin(ModelView, model=Disposal): # (!!!) 還原 (7/8)
    name = "disposal"
    label = "報廢紀錄"
    icon = "fa-solid fa-trash"
    
    fields = [
        Disposal.vehicle, 
        Disposal.user, 
        Disposal.notification_date, 
        Disposal.disposed_on, 
        Disposal.final_mileage
    ]
    
    fields_for_form = [
        Disposal.vehicle,
        Disposal.user,
        Disposal.notification_date,
        Disposal.disposed_on,
        Disposal.final_mileage,
        Disposal.reason,
    ]

class AttachmentAdmin(ModelView, model=Attachment): # (!!!) 還原 (8/8)
    name = "attachment"
    label = "所有附件"
    icon = "fa-solid fa-paperclip"
    
    can_create = False
    can_edit = False
    
    # 列表頁 (原 column_list)
    fields = [
        Attachment.entity_type, 
        Attachment.entity_id, 
        Attachment.file_name,
        Attachment.file_path,
        Attachment.uploaded_at
    ]
    
    # 詳情頁 (原 column_details_list)
    fields_for_detail = [
        Attachment.id,
        Attachment.entity_type,
        Attachment.entity_id,
        Attachment.file_name,
        Attachment.file_path,
        Attachment.description,
        Attachment.uploaded_at,
    ]
    
    # 列表頁格式化
    list_formatters = {
        "entity_type": format_attachment_entity,
        "file_path": format_attachment_link,
    }
    
    # 詳情頁格式化
    detail_formatters = {
        "entity_type": format_attachment_entity,
        "file_path": format_attachment_link,
    }