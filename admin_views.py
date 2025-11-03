# admin_views.py
import enum
from typing import Any
from markupsafe import Markup

from starlette_admin.contrib.sqla import ModelView
from starlette.requests import Request
from starlette_admin import fields as F  # (!!!) 匯入 fields 模組 (!!!)

# (!!!) 匯入所有 Model 和 Enum (!!!)
from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment, Employee, 
    VehicleAssetLog, 
    AssetType, AssetStatus, VehicleType, VehicleStatus, 
    MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)

# --- (v13) Enum 中文翻譯字典 (保持不變) ---
# (這些 formatter 仍將被 list_formatters / detail_formatters 使用)
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
    "retired": "已報Pedro",
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


# --- 格式化函式 (保持不變) ---

def _get_enum_value(value: Any) -> str:
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

def format_uuid_as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

# --- Admin Views (!!! 最終修正：F.*Field + formatters 字典 !!!) ---

class EmployeeAdmin(ModelView): 
    identity = "employee"
    name = "員工"
    label = "員工管理"
    icon = "fa-solid fa-users"
    
    fields = [
        F.StringField("name", label="姓名"),
        F.StringField("phone", label="電話"),
        F.BooleanField("has_car_license", label="有汽車駕照"),
        F.BooleanField("has_motorcycle_license", label="有機車駕照"),
    ]
    
    detail_formatters = {
        "id": format_uuid_as_str,
    }
    
    searchable_fields = ["name", "phone", "has_car_license", "has_motorcycle_license"]
    
    fields_for_form = [
        F.StringField("name", label="姓名"),
        F.StringField("phone", label="電話"),
        F.BooleanField("has_car_license", label="有汽車駕照"),
        F.BooleanField("has_motorcycle_license", label="有機車駕照"),
    ]

    fields_for_detail = [
        F.StringField("id", label="ID"),
        F.StringField("name", label="姓名"),
        F.StringField("phone", label="電話"),
        F.BooleanField("has_car_license", label="有汽車駕照"),
        F.BooleanField("has_motorcycle_license", label="有機車駕照"),
        F.RelationField("vehicles", label="主要車輛"),
    ]

class VehicleAdmin(ModelView):
    identity = "vehicles"
    name = "車輛"
    label = "車輛管理"
    icon = "fa-solid fa-car"
    
    fields = [
        F.StringField("plate_no", label="車牌號碼"),
        F.StringField("company", label="所屬公司"),
        F.StringField("vehicle_type", label="車輛類型"),
        F.RelationField("user", label="主要使用人"),
        F.StringField("model", label="型號"),
        F.DateField("manufacture_date", label="出廠年月"),
        F.IntegerField("current_mileage", label="目前最新公里數"),
        F.IntegerField("maintenance_interval", label="保養基準(km)"),
        F.StringField("status", label="狀態"),
    ]
    
    list_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
    }
    
    detail_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
        "id": format_uuid_as_str,
    }

    searchable_fields = ["plate_no", "make", "model", "company"]

    fields_for_form = [
        F.StringField("plate_no", label="車牌號碼"),
        F.StringField("company", label="所屬公司"),
        F.EnumField("vehicle_type", enum=VehicleType, label="車輛類型"),
        F.EnumField("status", enum=VehicleStatus, label="狀態"),
        F.RelationField("user", label="主要使用人"),
        F.StringField("make", label="品牌"),
        F.StringField("model", label="型號"),
        F.DateField("manufacture_date", label="出廠年月"),
        F.IntegerField("displacement_cc", label="排氣量(cc)"),
        F.IntegerField("current_mileage", label="目前最新公里數"),
        F.IntegerField("maintenance_interval", label="保養基準(km)"),
    ]

    fields_for_search = [
        F.StringField("plate_no", label="車牌號碼"),
        F.StringField("company", label="所屬公司"),
        F.EnumField("vehicle_type", enum=VehicleType, label="車輛類型"),
        F.EnumField("status", enum=VehicleStatus, label="狀態"),
        F.RelationField("user", label="主要使用人"), # <-- 這個會被顯示為下拉選單
        F.StringField("make", label="品牌"),
        F.StringField("model", label="型號"),
        F.DateField("manufacture_date", label="出廠年月"),
    ]

    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID") # ID 在 detail_formatters 中處理
    ]

class VehicleAssetLogAdmin(ModelView):
    identity = "vehicle_asset_logs"
    name = "車輛資產"
    label = "車輛資產日誌"
    icon = "fa-solid fa-key"
    
    fields = [
        F.RelationField("vehicle", label="關聯車輛"),
        F.DateField("log_date", label="紀錄日期"),
        F.StringField("asset_type", label="財產類型"),
        F.StringField("description", label="財產描述"),
        F.StringField("status", label="狀態"),
        F.RelationField("user", label="保管人"),
    ]
    
    list_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
    }
    
    detail_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
        "id": format_uuid_as_str,
    }
    
    searchable_fields = ["description", "notes"]
    
    fields_for_form = [
        F.RelationField("vehicle", label="關聯車輛"),
        F.DateField("log_date", label="紀錄日期"),
        F.EnumField("asset_type", enum=AssetType, label="財產類型"),
        F.StringField("description", label="財產描述"),
        F.EnumField("status", enum=AssetStatus, label="狀態"),
        F.RelationField("user", label="保管人"),
        F.TextAreaField("notes", label="備註"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class MaintenanceAdmin(ModelView):
    identity = "maintenance"
    name = "保養維修"
    label = "保養維修紀錄"
    icon = "fa-solid fa-wrench"
    
    fields = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("user", label="當時使用人"),
        F.RelationField("handler", label="行政處理人"),
        F.StringField("category", label="類別"),
        F.DateField("performed_on", label="執行日期"),
        F.DateField("return_date", label="牽車(回)日期"),
        F.IntegerField("odometer_km", label="當時實際里程"),
        F.FloatField("amount", label="金額"),
        F.BooleanField("is_reconciled", label="已對帳"),
    ]
    
    list_formatters = {
        "category": format_maintenance_category,
    }
    
    detail_formatters = {
        "category": format_maintenance_category,
        "id": format_uuid_as_str,
    }
    
    searchable_fields = ["vendor", "notes", "handler_notes"]
    
    fields_for_form = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("user", label="當時使用人(可選)"),
        F.RelationField("handler", label="行政處理人"),
        F.EnumField("category", enum=MaintenanceCategory, label="類別"),
        F.StringField("vendor", label="廠商"),
        F.DateField("performed_on", label="執行日期"),
        F.DateField("return_date", label="牽車(回)日期"),
        F.IntegerField("service_target_km", label="表定保養里程"),
        F.IntegerField("odometer_km", label="當時實際里程"),
        F.FloatField("amount", label="金額(填入會自動產生費用單)"),
        F.BooleanField("is_reconciled", label="已對帳(勾選會自動標記費用單)"),
        F.TextAreaField("notes", label="維修細節(附註)"),
        F.TextAreaField("handler_notes", label="聯絡事宜(備註-2)"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class InspectionAdmin(ModelView):
    identity = "inspections"
    name = "檢驗"
    label = "檢驗紀錄"
    icon = "fa-solid fa-clipboard-check"
    
    fields = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("handler", label="行政處理人"),
        F.StringField("kind", label="檢驗類型"),
        F.DateField("notification_date", label="接收通知日期"),
        F.DateField("deadline_date", label="最晚日期(期限)"),
        F.DateField("inspected_on", label="實際驗車日期"),
        F.StringField("result", label="結果"),
        F.FloatField("amount", label="金額"),
        F.BooleanField("is_reconciled", label="已對帳"),
    ]
    
    list_formatters = {
        "kind": format_inspection_kind,
    }
    
    detail_formatters = {
        "kind": format_inspection_kind,
        "id": format_uuid_as_str,
    }
    
    fields_for_form = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("user", label="當時使用人(可選)"),
        F.RelationField("handler", label="行政處理人"),
        F.EnumField("kind", enum=InspectionKind, label="檢驗類型"),
        F.StringField("result", label="結果"),
        F.DateField("notification_date", label="接收通知日期"),
        F.StringField("notification_source", label="通知方式(告知者)"),
        F.DateField("deadline_date", label="最晚日期(期限)"),
        F.DateField("inspected_on", label="實際驗車日期"),
        F.DateField("return_date", label="牽車(回)日期"),
        F.DateField("next_due_on", label="下次應驗日期"),
        F.FloatField("amount", label="金額(填入會自動產生費用單)"),
        F.BooleanField("is_reconciled", label="已對帳(勾選會自動標記費用單)"),
        F.TextAreaField("notes", label="檢驗細節(附註)"),
        F.TextAreaField("handler_notes", label="聯絡事宜(備註)"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class FeeAdmin(ModelView):
    identity = "fees"
    name = "費用"
    label = "費用請款"
    icon = "fa-solid fa-dollar-sign"
    
    fields = [
        F.RelationField("user", label="請款人"),
        F.RelationField("vehicle", label="車輛(可選)"),
        F.StringField("fee_type", label="費用類型"),
        F.FloatField("amount", label="金額"),
        F.DateField("request_date", label="請款日期"),
        F.BooleanField("is_paid", label="已給(已付款)"),
        F.StringField("invoice_number", label="發票號碼"),
    ]
    
    list_formatters = {
        "fee_type": format_fee_type,
    }
    
    detail_formatters = {
        "fee_type": format_fee_type,
        "id": format_uuid_as_str,
    }
    
    fields_for_form = [
        F.RelationField("user", label="請款人"),
        F.RelationField("vehicle", label="車輛(可選)"),
        F.EnumField("fee_type", enum=FeeType, label="費用類型"),
        F.DateField("receive_date", label="收到單據日期"),
        F.DateField("request_date", label="請款日期"),
        F.StringField("invoice_number", label="發票號碼"),
        F.FloatField("amount", label="金額"),
        F.BooleanField("is_paid", label="已給(已付款)"),
        F.DateField("period_start", label="費用區間(起)"),
        F.DateField("period_end", label="費用區間(迄)"),
        F.TextAreaField("notes", label="備註/項目"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class DisposalAdmin(ModelView):
    identity = "disposals"
    name = "報廢"
    label = "報廢紀錄"
    icon = "fa-solid fa-trash"
    
    fields = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("user", label="原使用人"),
        F.DateField("notification_date", label="告知報廢日期"),
        F.DateField("disposed_on", label="報廢日期"),
        F.IntegerField("final_mileage", label="最終公里數"),
    ]
    
    list_formatters = {}
    
    detail_formatters = {
        "id": format_uuid_as_str,
    }
    
    fields_for_form = [
        F.RelationField("vehicle", label="車輛"),
        F.RelationField("user", label="原使用人"),
        F.DateField("notification_date", label="告知報廢日期"),
        F.DateField("disposed_on", label="報廢日期"),
        F.IntegerField("final_mileage", label="最終公里數"),
        F.TextAreaField("reason", label="報廢原因"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class AttachmentAdmin(ModelView):
    identity = "attachments"
    name = "附件"
    label = "所有附件"
    icon = "fa-solid fa-paperclip"
    
    def can_create(self, request: Request) -> bool:
        return False
        
    def can_edit(self, request: Request) -> bool:
        return False
    
    fields = [
        F.StringField("entity_type", label="關聯類型"),
        F.StringField("entity_id", label="關聯ID"), 
        F.StringField("file_name", label="原始檔名"),
        F.StringField("file_path", label="檔案路徑"),
        F.DateTimeField("uploaded_at", label="上傳時間"),
    ]
    
    # (!!!) 重新加回 formatters 字典 (!!!)
    list_formatters = {
        "entity_type": format_attachment_entity,
        "file_path": format_attachment_link,
        "entity_id": format_uuid_as_str,
    }
    
    detail_formatters = {
        "entity_type": format_attachment_entity,
        "file_path": format_attachment_link,
        "entity_id": format_uuid_as_str,
        "id": format_uuid_as_str,
    }
    
    fields_for_detail = [
        F.StringField("id", label="ID"),
        F.StringField("entity_type", label="關聯類型"),
        F.StringField("entity_id", label="關聯ID"),
        F.StringField("file_name", label="原始檔名"),
        F.StringField("file_path", label="檔案路徑"),
        F.TextAreaField("description", label="檔案說明"),
        F.DateTimeField("uploaded_at", label="上傳時間"),
    ]