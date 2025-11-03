# admin_views.py
import enum
from typing import Any
from markupsafe import Markup

from starlette_admin.contrib.sqla import ModelView
from starlette.requests import Request
from starlette_admin import fields as F
# (!!!) 移除了所有錯誤的 import (selectinload, joinedload) (!!!)

from models import (
    Vehicle, Maintenance, Inspection, Fee, Disposal, Attachment, Employee, 
    VehicleAssetLog, 
    AssetType, AssetStatus, VehicleType, VehicleStatus, 
    MaintenanceCategory, InspectionKind, FeeType, AttachmentEntity
)

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
    "retired": "已報廢", # (!!!) 修正 "Pedro" 錯字 (!!!)
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

# (!!!) 為 EnumField 的 choices 建立中文選項 (!!!)
VEHICLE_TYPE_CHOICES = [(v.value, VEHICLE_TYPE_MAP.get(v.value, v.value)) for v in VehicleType]
VEHICLE_STATUS_CHOICES = [(v.value, VEHICLE_STATUS_MAP.get(v.value, v.value)) for v in VehicleStatus]
ASSET_TYPE_CHOICES = [(v.value, ASSET_TYPE_MAP.get(v.value, v.value)) for v in AssetType]
ASSET_STATUS_CHOICES = [(v.value, ASSET_STATUS_MAP.get(v.value, v.value)) for v in AssetStatus]
MAINTENANCE_CATEGORY_CHOICES = [(v.value, MAINTENANCE_CATEGORY_MAP.get(v.value, v.value)) for v in MaintenanceCategory]
INSPECTION_KIND_CHOICES = [(v.value, INSPECTION_KIND_MAP.get(v.value, v.value)) for v in InspectionKind]
FEE_TYPE_CHOICES = [(v.value, FEE_TYPE_MAP.get(v.value, v.value)) for v in FeeType]
ATTACHMENT_ENTITY_CHOICES = [(v.value, ATTACHMENT_ENTITY_MAP.get(v.value, v.value)) for v in AttachmentEntity]


# --- 格式化函式 (保持不變) ---
def _get_enum_value(value: Any) -> str:
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)

# (!!!) 1. 新增關聯欄位的 Formatter (!!!)
def format_user_name(user_obj: Employee) -> str:
    """ 將 Employee 物件轉為姓名 (處理 None) """
    if user_obj is None:
        return "-null-"
    return str(user_obj) # (這會呼叫 models.py 中的 __str__)

def format_vehicle_plate(vehicle_obj: Vehicle) -> str:
    """ 將 Vehicle 物件轉為車牌 (處理 None) """
    if vehicle_obj is None:
        return "-null-"
    return str(vehicle_obj) # (這會呼叫 models.py 中的 __str__)

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

# --- Admin Views ---

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
        F.HasMany("vehicles", label="主要車輛", identity="vehicle"),
    ]

class VehicleAdmin(ModelView):
    identity = "vehicle"
    name = "車輛"
    label = "車輛管理"
    icon = "fa-solid fa-car"
    
    fields = [
        F.StringField("plate_no", label="車牌號碼"),
        F.StringField("company", label="所屬公司"),
        F.EnumField("vehicle_type", enum=VehicleType, label="車輛類型"), # (!!!) 2. 列表頁改回 EnumField (!!!)
        F.HasOne("user", label="主要使用人", identity="employee"),
        F.StringField("model", label="型號"),
        F.DateField("manufacture_date", label="出廠年月"),
        F.IntegerField("current_mileage", label="目前最新公里數"),
        F.IntegerField("maintenance_interval", label="保養基準(km)"),
        F.EnumField("status", enum=VehicleStatus, label="狀態"), # (!!!) 2. 列表頁改回 EnumField (!!!)
    ]
    
    # (!!!) 3. 重新加回 list_formatters (!!!)
    list_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
        "user": format_user_name, # (!!!) 3. 加入關聯欄位 formatter (!!!)
    }
    
    detail_formatters = {
        "vehicle_type": format_vehicle_type,
        "status": format_vehicle_status,
        "id": format_uuid_as_str,
        "user": format_user_name, # (!!!) 3. 詳情頁也加入 (!!!)
    }

    searchable_fields = ["plate_no", "make", "model", "company"]

    fields_for_form = [
        F.StringField("plate_no", label="車牌號碼"),
        F.StringField("company", label="所屬公司"),
        F.EnumField("vehicle_type", enum=VehicleType, label="車輛類型", choices=VEHICLE_TYPE_CHOICES),
        F.EnumField("status", enum=VehicleStatus, label="狀態", choices=VEHICLE_STATUS_CHOICES),
        F.HasOne("user", label="主要使用人", identity="employee"),
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
        F.EnumField("vehicle_type", enum=VehicleType, label="車輛類型", choices=VEHICLE_TYPE_CHOICES),
        F.EnumField("status", enum=VehicleStatus, label="狀態", choices=VEHICLE_STATUS_CHOICES),
        F.HasOne("user", label="主要使用人", identity="employee"), 
        F.StringField("make", label="品牌"),
        F.StringField("model", label="型號"),
        F.DateField("manufacture_date", label="出廠年月"),
    ]

    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID") 
    ]

class VehicleAssetLogAdmin(ModelView):
    identity = "vehicle_asset_log"
    name = "車輛資產"
    label = "車輛資產日誌"
    icon = "fa-solid fa-key"
    
    fields = [
        F.HasOne("vehicle", label="關聯車輛", identity="vehicle"),
        F.DateField("log_date", label="紀錄日期"),
        F.EnumField("asset_type", enum=AssetType, label="財產類型"), # (!!!) 2. 改回 EnumField (!!!)
        F.StringField("description", label="財產描述"),
        F.EnumField("status", enum=AssetStatus, label="狀態"), # (!!!) 2. 改回 EnumField (!!!)
        F.HasOne("user", label="保管人", identity="employee"),
    ]
    
    list_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
        "user": format_user_name, # (!!!) 3. 加入 (!!!)
        "vehicle": format_vehicle_plate, # (!!!) 3. 加入 (!!!)
    }
    
    detail_formatters = {
        "asset_type": format_asset_type,
        "status": format_asset_status,
        "id": format_uuid_as_str,
        "user": format_user_name,
        "vehicle": format_vehicle_plate,
    }
    
    searchable_fields = ["description", "notes"]
    
    fields_for_form = [
        F.HasOne("vehicle", label="關聯車輛", identity="vehicle"),
        F.DateField("log_date", label="紀錄日期"),
        F.EnumField("asset_type", enum=AssetType, label="財產類型", choices=ASSET_TYPE_CHOICES),
        F.StringField("description", label="財產描述"),
        F.EnumField("status", enum=AssetStatus, label="狀態", choices=ASSET_STATUS_CHOICES),
        F.HasOne("user", label="保管人", identity="employee"),
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
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("user", label="當時使用人", identity="employee"),
        F.HasOne("handler", label="行政處理人", identity="employee"),
        F.EnumField("category", enum=MaintenanceCategory, label="類別"), # (!!!) 2. 改回 EnumField (!!!)
        F.DateField("performed_on", label="執行日期"),
        F.DateField("return_date", label="牽車(回)日期"),
        F.IntegerField("odometer_km", label="當時實際里程"),
        F.FloatField("amount", label="金額"),
        F.BooleanField("is_reconciled", label="已對帳"),
    ]
    
    list_formatters = {
        "category": format_maintenance_category,
        "vehicle": format_vehicle_plate, # (!!!) 3. 加入 (!!!)
        "user": format_user_name, # (!!!) 3. 加入 (!!!)
        "handler": format_user_name, # (!!!) 3. 加入 (!!!)
    }
    
    detail_formatters = {
        "category": format_maintenance_category,
        "id": format_uuid_as_str,
        "vehicle": format_vehicle_plate,
        "user": format_user_name,
        "handler": format_user_name,
    }
    
    searchable_fields = ["vendor", "notes", "handler_notes"]
    
    fields_for_form = [
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("user", label="當時使用人(可選)", identity="employee"),
        F.HasOne("handler", label="行政處理人", identity="employee"),
        F.EnumField("category", enum=MaintenanceCategory, label="類別", choices=MAINTENANCE_CATEGORY_CHOICES),
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
    identity = "inspection"
    name = "檢驗"
    label = "檢驗紀錄"
    icon = "fa-solid fa-clipboard-check"
    
    fields = [
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("handler", label="行政處理人", identity="employee"),
        F.EnumField("kind", enum=InspectionKind, label="檢驗類型"), # (!!!) 2. 改回 EnumField (!!!)
        F.DateField("notification_date", label="接收通知日期"),
        F.DateField("deadline_date", label="最晚日期(期限)"),
        F.DateField("inspected_on", label="實際驗車日期"),
        F.StringField("result", label="結果"),
        F.FloatField("amount", label="金額"),
        F.BooleanField("is_reconciled", label="已對帳"),
    ]
    
    list_formatters = {
        "kind": format_inspection_kind,
        "vehicle": format_vehicle_plate, # (!!!) 3. 加入 (!!!)
        "handler": format_user_name, # (!!!) 3. 加入 (!!!)
    }
    
    detail_formatters = {
        "kind": format_inspection_kind,
        "id": format_uuid_as_str,
        "vehicle": format_vehicle_plate,
        "user": format_user_name, # (User 也在詳情頁)
        "handler": format_user_name,
    }
    
    fields_for_form = [
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("user", label="當時使用人(可選)", identity="employee"),
        F.HasOne("handler", label="行政處理人", identity="employee"),
        F.EnumField("kind", enum=InspectionKind, label="檢驗類型", choices=INSPECTION_KIND_CHOICES),
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
    identity = "fee"
    name = "費用"
    label = "費用請款"
    icon = "fa-solid fa-dollar-sign"
    
    fields = [
        F.HasOne("user", label="請款人", identity="employee"),
        F.HasOne("vehicle", label="車輛(可選)", identity="vehicle"),
        F.EnumField("fee_type", enum=FeeType, label="費用類型"), # (!!!) 2. 改回 EnumField (!!!)
        F.FloatField("amount", label="金額"),
        F.DateField("request_date", label="請款日期"),
        F.BooleanField("is_paid", label="已給(已付款)"),
        F.StringField("invoice_number", label="發票號碼"),
    ]
    
    list_formatters = {
        "fee_type": format_fee_type,
        "user": format_user_name, # (!!!) 3. 加入 (!!!)
        "vehicle": format_vehicle_plate, # (!!!) 3. 加入 (!!!)
    }
    
    detail_formatters = {
        "fee_type": format_fee_type,
        "id": format_uuid_as_str,
        "user": format_user_name,
        "vehicle": format_vehicle_plate,
    }
    
    fields_for_form = [
        F.HasOne("user", label="請款人", identity="employee"),
        F.HasOne("vehicle", label="車輛(可選)", identity="vehicle"),
        F.EnumField("fee_type", enum=FeeType, label="費用類型", choices=FEE_TYPE_CHOICES),
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
    identity = "disposal"
    name = "報廢"
    label = "報廢紀錄"
    icon = "fa-solid fa-trash"
    
    fields = [
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("user", label="原使用人", identity="employee"),
        F.DateField("notification_date", label="告知報廢日期"),
        F.DateField("disposed_on", label="報廢日期"),
        F.IntegerField("final_mileage", label="最終公里數"),
    ]
    
    list_formatters = {
        "vehicle": format_vehicle_plate, # (!!!) 3. 加入 (!!!)
        "user": format_user_name, # (!!!) 3. 加入 (!!!)
    }
    
    detail_formatters = {
        "id": format_uuid_as_str,
        "vehicle": format_vehicle_plate,
        "user": format_user_name,
    }
    
    fields_for_form = [
        F.HasOne("vehicle", label="車輛", identity="vehicle"),
        F.HasOne("user", label="原使用人", identity="employee"),
        F.DateField("notification_date", label="告知報廢日期"),
        F.DateField("disposed_on", label="報廢日期"),
        F.IntegerField("final_mileage", label="最終公里數"),
        F.TextAreaField("reason", label="報廢原因"),
    ]
    
    fields_for_detail = fields_for_form + [
        F.StringField("id", label="ID")
    ]

class AttachmentAdmin(ModelView):
    identity = "attachment"
    name = "附件"
    label = "所有附件"
    icon = "fa-solid fa-paperclip"
    
    def can_create(self, request: Request) -> bool:
        return False
        
    def can_edit(self, request: Request) -> bool:
        return False
    
    fields = [
        F.EnumField("entity_type", enum=AttachmentEntity, label="關聯類型"), # (!!!) 2. 改回 EnumField (!!!)
        F.StringField("entity_id", label="關聯ID"), 
        F.StringField("file_name", label="原始檔名"),
        F.StringField("file_path", label="檔案路徑"),
        F.DateTimeField("uploaded_at", label="上傳時間"),
    ]

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
        F.EnumField("entity_type", enum=AttachmentEntity, label="關聯類型", choices=ATTACHMENT_ENTITY_CHOICES),
        F.StringField("entity_id", label="關聯ID"),
        F.StringField("file_name", label="原始檔名"),
        F.StringField("file_path", label="檔案路徑"),
        F.TextAreaField("description", label="檔案說明"),
        F.DateTimeField("uploaded_at", label="上傳時間"),
    ]