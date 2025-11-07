# import_data.py
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import settings
from models import (
    Base, Vehicle, Maintenance, Inspection, Fee, Disposal, Employee, 
    VehicleAssetLog, AssetType, AssetStatus,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType,
    ParkingLot, ParkingSpot
)
import re
from contextlib import contextmanager
from pathlib import Path

# --- 資料庫連線 ---
engine = create_engine(settings.DATABASE_URL)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# --- 快取 ---
VEHICLE_CACHE = {}
EMPLOYEE_CACHE = {}
PARKING_LOT_CACHE = {}

# (!!!) 1. 建立反向翻譯字典 (!!!)
REVERSE_VEHICLE_TYPE_MAP = {
    "小客車": VehicleType.car,
    "機車": VehicleType.motorcycle,
    "廂型車": VehicleType.van,
    "貨車": VehicleType.truck,
    "電動機車": VehicleType.ev_scooter,
}
REVERSE_VEHICLE_STATUS_MAP = {
    "啟用中": VehicleStatus.active,
    "維修中": VehicleStatus.maintenance,
    "已報廢": VehicleStatus.retired,
}
REVERSE_MAINTENANCE_MAP = {
    "定期保養": MaintenanceCategory.maintenance,
    "維修": MaintenanceCategory.repair,
    "一般洗車": MaintenanceCategory.carwash,
    "手工洗車": MaintenanceCategory.deep_cleaning,
    "淨車": MaintenanceCategory.ritual_cleaning,
}
REVERSE_INSPECTION_MAP = {
    "定期檢驗": InspectionKind.periodic,
    "排氣檢驗": InspectionKind.emission,
    "複檢": InspectionKind.reinspection,
}
REVERSE_FEE_TYPE_MAP = {
    "加油費": FeeType.fuel_fee,
    "停車費": FeeType.parking,
    "保養服務": FeeType.maintenance_service,
    "維修零件": FeeType.repair_parts,
    "檢驗費": FeeType.inspection_fee,
    "用品/雜項": FeeType.supplies,
    "E-Tag/過路費": FeeType.toll,
    "稅金": FeeType.license_tax,
    "其他": FeeType.other,
}
REVERSE_ASSET_TYPE_MAP = {
    "鑰匙": AssetType.key,
    "行車紀錄器": AssetType.dashcam,
    "E-Tag": AssetType.etag,
    "其他": AssetType.other,
}
REVERSE_ASSET_STATUS_MAP = {
    "已指派": AssetStatus.assigned,
    "已歸還": AssetStatus.returned,
    "遺失": AssetStatus.lost,
    "已報廢/處理": AssetStatus.disposed,
}


@contextmanager
def session_scope():
    """提供一個事務性的 session 範圍"""
    session = Session()
    try:
        # 每次開始事務時，清空快取
        VEHICLE_CACHE.clear()
        EMPLOYEE_CACHE.clear()
        PARKING_LOT_CACHE.clear()
        print("Session 開始，快取已清空。")
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"發生錯誤，已回滾: {e}")
        raise
    finally:
        session.close()
        Session.remove()
        print("Session 關閉。")

def load_dataframe(file_path: str | Path):
    """ 根據副檔名自動載入 CSV 或 XLSX """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"找不到檔案: {p}")
        
    if p.suffix == ".csv":
        return pd.read_csv(p, comment='#', dtype=str)
    elif p.suffix in [".xlsx", ".xls"]:
        return pd.read_excel(p, comment='#', dtype=str)
    else:
        raise ValueError(f"不支援的檔案格式: {p.suffix}")

def clean_string(text_str):
    if pd.isna(text_str) or str(text_str).lower() == 'nan':
        return None
    cleaned_text = re.sub(r'\s+', ' ', str(text_str)).strip()
    if cleaned_text == "":
        return None
    return cleaned_text

# (!!!) 2. 建立中文轉換 Eum 函式 (!!!)
def clean_enum(value_str, reverse_map, default=None):
    """ 
    嘗試將傳入的(中文)字串，透過 reverse_map 轉為 enum 值。
    如果失敗，則回傳 default。
    """
    cleaned_val = clean_string(value_str)
    if not cleaned_val:
        return default
    
    # 嘗試直接查找 (例如："小客車")
    if cleaned_val in reverse_map:
        return reverse_map[cleaned_val]
        
    # 嘗試查找英文 (例如：使用者直接填 "car")
    if cleaned_val in reverse_map.values():
        return cleaned_val
        
    print(f"警告：無法識別的枚舉值 '{cleaned_val}'。將使用預設值 {default}。")
    return default

# --- 輔助函式 (查找 ID) ---
def get_vehicle_id(session, plate_no):
    plate_no = clean_string(plate_no)
    if not plate_no: return None
    if plate_no in VEHICLE_CACHE:
        return VEHICLE_CACHE[plate_no]
    vehicle = session.query(Vehicle).filter(Vehicle.plate_no == plate_no).first()
    if vehicle:
        VEHICLE_CACHE[plate_no] = vehicle.id
        return vehicle.id
    else:
        return None # (!!!) 車輛「不」自動建立 (!!!)

def get_user_id(session, name):
    name = clean_string(name)
    if not name: return None
    if name in EMPLOYEE_CACHE:
        return EMPLOYEE_CACHE[name]
    employee = session.query(Employee).filter(Employee.name == name).first()
    if employee:
        EMPLOYEE_CACHE[name] = employee.id
        return employee.id
    else:
        # (!!!) 員工「自動」建立 (!!!)
        print(f"  [自動] 找不到員工 '{name}'，將自動建立新員工...")
        new_emp = Employee(name=name)
        session.add(new_emp)
        session.flush() # 立即獲取 ID
        EMPLOYEE_CACHE[name] = new_emp.id
        return new_emp.id

# (!!!) 3. 新增停車場查找函式 (!!!)
def get_parking_lot_id(session, name):
    name = clean_string(name)
    if not name: return None
    if name in PARKING_LOT_CACHE:
        return PARKING_LOT_CACHE[name]
    lot = session.query(ParkingLot).filter(ParkingLot.name == name).first()
    if lot:
        PARKING_LOT_CACHE[name] = lot.id
        return lot.id
    else:
        # (!!!) 停車場「自動」建立 (!!!)
        print(f"  [自動] 找不到停車場 '{name}'，將自動建立新停車場...")
        new_lot = ParkingLot(name=name)
        session.add(new_lot)
        session.flush() # 立即獲取 ID
        PARKING_LOT_CACHE[name] = new_lot.id
        return new_lot.id

# --- 清理資料的輔助函式 ---
def clean_date(date_obj):
    date_str = clean_string(date_obj)
    if not date_str: return None
    try:
        return pd.to_datetime(date_str).date()
    except Exception:
        print(f"警告：無法解析日期 '{date_str}'")
        return None
def clean_numeric(num_str):
    num_str = clean_string(num_str)
    if not num_str: return None
    try: return float(num_str)
    except (ValueError, TypeError): return None
def clean_int(num_str):
    num_str = clean_string(num_str)
    if not num_str: return None
    try: return int(float(num_str))
    except (ValueError, TypeError): return None
def clean_bool(val):
    val_str = clean_string(val)
    if not val_str: return False
    return val_str.strip().lower() in ['1', 'true', 'v', 'yes', 'y', '1.0']

# --- (!!!) 4. 更新所有匯入函式 (!!!) ---

def import_employees(session, file_path: str | Path):
    print("--- 0. 開始匯入員工 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        name = clean_string(row.get('name'))
        if not name: continue
        existing = session.query(Employee).filter_by(name=name).first()
        if not existing:
            new_emp = Employee(
                name=name,
                phone=clean_string(row.get('phone')),
                has_car_license=clean_bool(row.get('has_car_license')),
                has_motorcycle_license=clean_bool(row.get('has_motorcycle_license')),
                is_handler=clean_bool(row.get('is_handler')) # (!!!) 已更新 (!!!)
            )
            session.add(new_emp)
            EMPLOYEE_CACHE[name] = new_emp.id 
            print(f"  [新增] 員工: {name}")
        else:
            EMPLOYEE_CACHE[name] = existing.id 
            print(f"  [跳過] 員工已存在: {name}")
    print("--- 員工匯入完成 ---")

def import_vehicles(session, file_path: str | Path):
    print("--- 1. 開始匯入車輛 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        plate_no = clean_string(row.get('plate_no'))
        if not plate_no: continue
        existing = session.query(Vehicle).filter_by(plate_no=plate_no).first()
        if not existing:
            user_name = row.get('user_name')
            user_id = get_user_id(session, user_name) 

            new_vehicle = Vehicle(
                plate_no=plate_no,
                company=clean_string(row.get('company')),
                # (!!!) 使用 clean_enum (!!!)
                vehicle_type=clean_enum(row.get('vehicle_type'), REVERSE_VEHICLE_TYPE_MAP, VehicleType.car),
                make=clean_string(row.get('make')),
                model=clean_string(row.get('model')),
                manufacture_date=clean_date(row.get('manufacture_date')),
                displacement_cc=clean_int(row.get('displacement_cc')),
                current_mileage=clean_int(row.get('current_mileage')),
                maintenance_interval=clean_int(row.get('maintenance_interval')),
                # (!!!) 使用 clean_enum (!!!)
                status=clean_enum(row.get('status'), REVERSE_VEHICLE_STATUS_MAP, VehicleStatus.active),
                user_id=user_id
            )
            session.add(new_vehicle)
            VEHICLE_CACHE[plate_no] = new_vehicle.id 
            print(f"  [新增] 車輛: {plate_no}")
        else:
            VEHICLE_CACHE[plate_no] = existing.id 
            print(f"  [跳過] 車輛已存在: {plate_no}")
    print("--- 車輛匯入完成 ---")

def import_maintenance(session, file_path: str | Path):
    print("--- 2. 開始匯入保養維修 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        vehicle_id = get_vehicle_id(session, row.get('vehicle_plate_no'))
        if not vehicle_id:
            print(f"警告: 保養紀錄 (備註: {row.get('notes')}) 因找不到車牌 '{clean_string(row.get('vehicle_plate_no'))}' 而跳過。")
            continue
        
        user_id = get_user_id(session, row.get('user_name'))
        handler_id = get_user_id(session, row.get('handler_name'))
        
        new_maint = Maintenance(
            vehicle_id=vehicle_id, 
            user_id=user_id, 
            handler_id=handler_id,
            # (!!!) 使用 clean_enum (!!!)
            category=clean_enum(row.get('category'), REVERSE_MAINTENANCE_MAP, MaintenanceCategory.maintenance),
            vendor=clean_string(row.get('vendor')),
            performed_on=clean_date(row.get('performed_on')),
            return_date=clean_date(row.get('return_date')),
            service_target_km=clean_int(row.get('service_target_km')),
            odometer_km=clean_int(row.get('odometer_km')),
            amount=clean_numeric(row.get('amount')),
            is_reconciled=clean_bool(row.get('is_reconciled')),
            notes=clean_string(row.get('notes')),
            handler_notes=clean_string(row.get('handler_notes'))
        )
        session.add(new_maint)
        
        # 自動建立費用的邏輯 (保持不變)
        amount = clean_numeric(row.get('amount'))
        if amount and amount > 0:
            fee_type = FeeType.maintenance_service
            if new_maint.category == MaintenanceCategory.repair:
                fee_type = FeeType.repair_parts
            fee_user_id = handler_id if handler_id else user_id
            if not fee_user_id:
                print(f"  [自動] 警告: {clean_string(row.get('vehicle_plate_no'))} 的費用單缺少請款人。")
            new_fee = Fee(
                vehicle_id=vehicle_id, user_id=fee_user_id,
                receive_date=new_maint.performed_on, 
                request_date=new_maint.performed_on, 
                fee_type=fee_type, amount=amount,
                is_paid=new_maint.is_reconciled, 
                notes=f"自動建立 - {row.get('category')}: {row.get('notes') or ''}"
            )
            session.add(new_fee)
            print(f"  [自動] 為 {clean_string(row.get('vehicle_plate_no'))} 建立 ${amount} 的費用單。")
            
    print("--- 保養維修匯入完成 ---")

def import_inspections(session, file_path: str | Path):
    print("--- 3. 開始匯入檢驗 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        vehicle_id = get_vehicle_id(session, row.get('vehicle_plate_no'))
        if not vehicle_id:
            print(f"警告: 檢驗紀錄 (通知日期: {row.get('notification_date')}) 因找不到車牌 '{clean_string(row.get('vehicle_plate_no'))}' 而跳過。")
            continue
            
        user_id = get_user_id(session, row.get('user_name'))
        handler_id = get_user_id(session, row.get('handler_name'))

        new_insp = Inspection(
            vehicle_id=vehicle_id, 
            user_id=user_id, 
            handler_id=handler_id,
            # (!!!) 使用 clean_enum (!!!)
            kind=clean_enum(row.get('kind'), REVERSE_INSPECTION_MAP, InspectionKind.periodic),
            result=clean_string(row.get('result')),
            notification_date=clean_date(row.get('notification_date')),
            notification_source=clean_string(row.get('notification_source')),
            deadline_date=clean_date(row.get('deadline_date')),
            inspected_on=clean_date(row.get('inspected_on')),
            return_date=clean_date(row.get('return_date')),
            next_due_on=clean_date(row.get('next_due_on')),
            amount=clean_numeric(row.get('amount')),
            is_reconciled=clean_bool(row.get('is_reconciled')),
            notes=clean_string(row.get('notes')),
            handler_notes=clean_string(row.get('handler_notes'))
        )
        session.add(new_insp)

        # 自動建立費用的邏輯 (保持不變)
        amount = clean_numeric(row.get('amount'))
        if amount and amount > 0:
            fee_user_id = handler_id if handler_id else user_id
            if not fee_user_id:
                print(f"  [自動] 警告: {clean_string(row.get('vehicle_plate_no'))} 的檢驗費用單缺少請款人。")
            new_fee = Fee(
                vehicle_id=vehicle_id, user_id=fee_user_id,
                receive_date=new_insp.inspected_on or new_insp.notification_date,
                request_date=new_insp.inspected_on or new_insp.notification_date,
                fee_type=FeeType.inspection_fee,
                amount=amount, is_paid=new_insp.is_reconciled,
                notes=f"自動建立 - 檢驗費: {row.get('kind')}"
            )
            session.add(new_fee)
            print(f"  [自動] 為 {clean_string(row.get('vehicle_plate_no'))} 建立 ${amount} 的檢驗費用單。")
            
    print("--- 檢驗匯入完成 ---")

def import_fees(session, file_path: str | Path):
    print("--- 4. 開始匯入「其他」費用 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        user_id = get_user_id(session, row.get('user_name'))
        if not user_id:
             print(f"警告：請款紀錄 (項目: {row.get('fee_type')}, 金額: {row.get('amount')}) 因找不到員工 '{clean_string(row.get('user_name'))}' 而跳過。")
             continue
        
        vehicle_id = get_vehicle_id(session, row.get('vehicle_plate_no'))
        if pd.notna(row.get('vehicle_plate_no')) and not vehicle_id:
            print(f"提醒：請款紀錄 (項目: {row.get('fee_type')}) 的車牌 '{clean_string(row.get('vehicle_plate_no'))}' 非公司車輛，將作為私車請款 (不關聯車輛)。")

        new_fee = Fee(
            vehicle_id=vehicle_id, 
            user_id=user_id,
            receive_date=clean_date(row.get('receive_date')),
            request_date=clean_date(row.get('request_date')),
            invoice_number=clean_string(row.get('invoice_number')),
            # (!!!) 使用 clean_enum (!!!)
            fee_type=clean_enum(row.get('fee_type'), REVERSE_FEE_TYPE_MAP, FeeType.other),
            amount=clean_numeric(row.get('amount')),
            is_paid=clean_bool(row.get('is_paid')),
            period_start=clean_date(row.get('period_start')), # (!!!) 已更新 (!!!)
            period_end=clean_date(row.get('period_end')),   # (!!!) 已更新 (!!!)
            notes=clean_string(row.get('notes'))
        )
        session.add(new_fee)
    print("--- 「其他」費用匯入完成 ---")

def import_disposals(session, file_path: str | Path):
    print("--- 5. 開始匯入報廢 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        vehicle_id = get_vehicle_id(session, row.get('vehicle_plate_no'))
        if not vehicle_id:
            print(f"警告: 報廢紀錄 (日期: {row.get('disposed_on')}) 因找不到車牌 '{clean_string(row.get('vehicle_plate_no'))}' 而跳過。")
            continue
            
        user_id = get_user_id(session, row.get('original_user_name'))

        new_disp = Disposal(
            vehicle_id=vehicle_id, 
            user_id=user_id,
            notification_date=clean_date(row.get('notification_date')),
            disposed_on=clean_date(row.get('disposed_on')),
            final_mileage=clean_int(row.get('final_mileage')),
            reason=clean_string(row.get('reason'))
        )
        session.add(new_disp)
        
        vehicle = session.query(Vehicle).filter_by(id=vehicle_id).first()
        if vehicle:
            vehicle.status = VehicleStatus.retired
            print(f"  [更新] 車輛 {vehicle.plate_no} 狀態為 retired")
            
    print("--- 報廢匯入完成 ---")

def import_asset_log(session, file_path: str | Path):
    print("--- 6. 開始匯入資產日誌 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        vehicle_id = get_vehicle_id(session, row.get('vehicle_plate_no'))
        if not vehicle_id:
             print(f"警告：資產紀錄 '{row.get('description')}' 因找不到車牌 '{clean_string(row.get('vehicle_plate_no'))}' 而跳過。")
             continue
            
        user_id = get_user_id(session, row.get('user_name'))

        new_log = VehicleAssetLog(
            vehicle_id=vehicle_id,
            user_id=user_id,
            log_date=clean_date(row.get('log_date')),
            # (!!!) 使用 clean_enum (!!!)
            asset_type=clean_enum(row.get('asset_type'), REVERSE_ASSET_TYPE_MAP, AssetType.other),
            description=clean_string(row.get('description')),
            status=clean_enum(row.get('status'), REVERSE_ASSET_STATUS_MAP, AssetStatus.other),
            notes=clean_string(row.get('notes'))
        )
        session.add(new_log)
    print("--- 資產日誌匯入完成 ---")

# (!!!) 5. 新增停車場匯入函式 (!!!)

def import_parking_lots(session, file_path: str | Path):
    print("--- 7. 開始匯入停車場 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        name = clean_string(row.get('name'))
        if not name: continue
        
        existing = session.query(ParkingLot).filter_by(name=name).first()
        if not existing:
            new_lot = ParkingLot(
                name=name,
                notes=clean_string(row.get('notes'))
            )
            session.add(new_lot)
            PARKING_LOT_CACHE[name] = new_lot.id
            print(f"  [新增] 停車場: {name}")
        else:
            PARKING_LOT_CACHE[name] = existing.id
            print(f"  [跳過] 停車場已存在: {name}")
    print("--- 停車場匯入完成 ---")

def import_parking_spots(session, file_path: str | Path):
    print("--- 8. 開始匯入停車位 ---")
    df = load_dataframe(file_path)
    for _, row in df.iterrows():
        lot_name = clean_string(row.get('lot_name'))
        spot_number = clean_string(row.get('spot_number'))
        
        if not lot_name or not spot_number:
            print(f"警告：停車位 (Lot: {lot_name}, Spot: {spot_number}) 因缺少名稱或車位編號而跳過。")
            continue
            
        lot_id = get_parking_lot_id(session, lot_name) # (!!!) 使用查找 (!!!)
        
        existing = session.query(ParkingSpot).filter_by(lot_id=lot_id, spot_number=spot_number).first()
        if not existing:
            new_spot = ParkingSpot(
                lot_id=lot_id,
                spot_number=spot_number,
                description=clean_string(row.get('description'))
            )
            session.add(new_spot)
            print(f"  [新增] 停車位: {lot_name} - {spot_number}")
        else:
            print(f"  [跳過] 停車位已存在: {lot_name} - {spot_number}")
    print("--- 停車位匯入完成 ---")