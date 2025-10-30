# admin_views.py
from sqladmin import ModelView
from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)
from typing import Any
from markupsafe import Markup

# --- Enum 中文翻譯字典 ---

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
    AttachmentEntity.maintenance: "保養維修",
    AttachmentEntity.disposal: "報廢",
    AttachmentEntity.inspection: "檢驗",
    AttachmentEntity.fee: "費用",
}

# --- 格式化函式 ---

def format_vehicle_type(value: VehicleType) -> str:
    return VEHICLE_TYPE_MAP.get(value, str(value))

def format_vehicle_status(value: VehicleStatus) -> str:
    # 範例：加入顏色
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
    # 讓附件顯示為可點擊的連結
    if value:
        return Markup(f'<a href="/uploads/{value}" target="_blank">{value}</a>')
    return ""


# --- Admin Views ---

class VehicleAdmin(ModelView, model=Vehicle):
    name = "車輛"
    name_plural = "車輛管理"
    icon = "fa-solid fa-car"
    
    # 列表頁顯示的欄位
    column_list = [
        Vehicle.plate_no, 
        Vehicle.vehicle_type, 
        Vehicle.make, 
        Vehicle.model, 
        Vehicle.year, 
        Vehicle.status
    ]
    # 翻譯 Enum
    column_formatters = {
        Vehicle.vehicle_type: format_vehicle_type,
        Vehicle.status: format_vehicle_status,
    }
    # 搜尋欄位
    column_searchable_list = [Vehicle.plate_no, Vehicle.make, Vehicle.model]
    # 篩選欄位 (會自動使用 Enum)
    column_filters = [Vehicle.vehicle_type, Vehicle.status, Vehicle.year]
    # 編輯/新增頁面的欄位 (排除關聯，它們會自動顯示)
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
        Maintenance.vehicle, # 顯示關聯的車輛 (會調用 __str__)
        Maintenance.category, 
        Maintenance.performed_on, 
        Maintenance.amount, 
        Maintenance.vendor,
        Maintenance.odometer_km,
    ]
    column_formatters = {
        Maintenance.category: format_maintenance_category,
    }
    column_searchable_list = [Maintenance.vendor]
    
    # 新的寫法 (明確指定 Filter 類型):
    column_filters = [
            # Maintenance.category, # <-- 移除 (導致 AttributeError)
            # Maintenance.performed_on, # <-- 移除 (因為 DateFilter 無法 import)
            Maintenance.vehicle # <-- 只留下這個，或者將整行 column_filters 刪除
        ]


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
    column_filters = [Inspection.kind, Inspection.inspected_on, Inspection.next_due_on, Inspection.vehicle]

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
    column_filters = [Fee.fee_type, Fee.paid_on, Fee.vehicle]


class DisposalAdmin(ModelView, model=Disposal):
    name = "報廢"
    name_plural = "報廢紀錄"
    icon = "fa-solid fa-trash"
    
    column_list = [Disposal.vehicle, Disposal.disposed_on, Disposal.reason]
    column_filters = [Disposal.disposed_on, Disposal.vehicle]


class AttachmentAdmin(ModelView, model=Attachment):
    name = "附件"
    name_plural = "所有附件"
    icon = "fa-solid fa-paperclip"
    
    # 唯讀，不允許在這邊新增，應透過 API 上傳
    can_create = False
    can_edit = False
    
    column_list = [
        Attachment.entity_type, 
        Attachment.entity_id, 
        Attachment.file_name,
        Attachment.file_path,
        Attachment.uploaded_at
    ]
    
    # (新增) 明確定義詳情頁要顯示的欄位
    column_details_list = [
        Attachment.id,
        Attachment.entity_type,
        Attachment.entity_id,
        Attachment.file_name,
        Attachment.file_path,
        Attachment.description,
        Attachment.uploaded_at,
    ]
    
    # 這是您原本的設定 (列表頁)
    column_formatters = {
        Attachment.entity_type: format_attachment_entity,
        Attachment.file_path: format_attachment_link, # 讓路徑變連結
    }
    
    column_details_formatters = {
        Attachment.entity_type: format_attachment_entity,
        Attachment.file_path: format_attachment_link, # 詳情頁也需要這個
    }

    column_filters = [Attachment.entity_type]