# import_data.py
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import settings
from models import (
    Base, Vehicle, Maintenance, Inspection, Fee, Disposal, Employee, 
    VehicleAssetLog, AssetType, AssetStatus,
    VehicleType, VehicleStatus, MaintenanceCategory, InspectionKind, FeeType
)
import re # (!!!) 匯入 re 模組
from contextlib import contextmanager

# --- 資料庫連線 ---
engine = create_engine(settings.DATABASE_URL)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

# --- 快取 ---
VEHICLE_CACHE = {}
EMPLOYEE_CACHE = {}

@contextmanager
def session_scope():
    """提供一個事務性的 session 範圍"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"發生錯誤，已回滾: {e}")
        raise
    finally:
        session.close()
        Session.remove()

# --- (!!! 修正：強力清除函式 !!!) ---
def clean_string(text_str):
    """ 強力清除所有空白字元，包含隱藏的換行和 &nbsp; """
    if pd.isna(text_str):
        return None
    # 替換所有空白類字元 (包含 \n, \r, \t, &nbsp; 等) 為單一空格，然後去除前後空格
    cleaned_text = re.sub(r'\s+', ' ', str(text_str)).strip()
    if cleaned_text == "":
        return None
    return cleaned_text

# --- 輔助函式 (用來查找 ID) ---
def get_vehicle_id(session, plate_no):
    plate_no = clean_string(plate_no) # (!!! 修正 !!!)
    if not plate_no: return None
    
    if plate_no in VEHICLE_CACHE:
        return VEHICLE_CACHE[plate_no]
    
    vehicle = session.query(Vehicle).filter(Vehicle.plate_no == plate_no).first()
    if vehicle:
        VEHICLE_CACHE[plate_no] = vehicle.id
        return vehicle.id
    else:
        return None

def get_user_id(session, name):
    name = clean_string(name) # (!!! 修正 !!!)
    if not name: return None
    
    if name in EMPLOYEE_CACHE:
        return EMPLOYEE_CACHE[name]
        
    employee = session.query(Employee).filter(Employee.name == name).first()
    if employee:
        EMPLOYEE_CACHE[name] = employee.id
        return employee.id
    else:
        return None

# --- 清理資料的輔助函式 ---
def clean_date(date_obj):
    if pd.isna(date_obj): return None
    return date_obj
def clean_numeric(num):
    if pd.isna(num): return None
    try: return float(num)
    except (ValueError, TypeError): return None
def clean_int(num):
    if pd.isna(num): return None
    try: return int(float(num))
    except (ValueError, TypeError): return None
def clean_bool(val):
    if pd.isna(val): return False
    val_str = str(val).strip().lower() 
    return val_str in ['1', 'true', 'v', 'yes', 'y', '1.0']

# --- 匯入函式 ---

def import_employees(session):
    print("\n--- 0. 開始匯入員工 (import_employees.csv) ---")
    try:
        df = pd.read_csv("import_employees.csv", comment='#', dtype={'phone': str})
    except FileNotFoundError:
        print("錯誤：找不到 'import_employees.csv'。")
        return
    for _, row in df.iterrows():
        name = clean_string(row.get('name')) # (!!! 修正 !!!)
        if not name: continue
        
        existing = session.query(Employee).filter_by(name=name).first()
        if not existing:
            new_emp = Employee(
                name=name,
                phone=clean_string(row.get('phone')), # (!!! 修正 !!!)
                has_car_license=clean_bool(row.get('has_car_license')),
                has_motorcycle_license=clean_bool(row.get('has_motorcycle_license'))
            )
            session.add(new_emp)
            EMPLOYEE_CACHE[name] = new_emp.id 
            print(f"  [新增] 員工: {name}")
        else:
            EMPLOYEE_CACHE[name] = existing.id 
            print(f"  [跳過] 員工已存在: {name}")
    print("--- 員工匯入完成 ---")

def import_vehicles(session):
    print("\n--- 1. 開始匯入車輛 (import_vehicles.csv) ---")
    try:
        df = pd.read_csv("import_vehicles.csv", comment='#', 
                         dtype={'displacement_cc': 'Int64', 'current_mileage': 'Int64', 'maintenance_interval': 'Int64'}, 
                         parse_dates=['manufacture_date'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_vehicles.csv'。")
        return
    for _, row in df.iterrows():
        plate_no = clean_string(row.get('plate_no')) # (!!! 修正 !!!)
        if not plate_no: continue

        existing = session.query(Vehicle).filter_by(plate_no=plate_no).first()
        if not existing:
            user_name_original = row.get('user_name') # (保留原始值用於警告)
            user_id = get_user_id(session, user_name_original)
            
            if pd.notna(user_name_original) and not user_id:
                print(f"警告：車輛 {plate_no} 的主要使用人 '{clean_string(user_name_original)}' 在員工表中找不到。")

            new_vehicle = Vehicle(
                plate_no=plate_no,
                company=clean_string(row.get('company')), # (!!! 修正 !!!)
                vehicle_type=clean_string(row.get('vehicle_type', 'car')), # (!!! 修正 !!!)
                make=clean_string(row.get('make')), # (!!! 修正 !!!)
                model=clean_string(row.get('model')), # (!!! 修正 !!!)
                manufacture_date=clean_date(row.get('manufacture_date')),
                displacement_cc=clean_int(row.get('displacement_cc')),
                current_mileage=clean_int(row.get('current_mileage')),
                maintenance_interval=clean_int(row.get('maintenance_interval')),
                status=clean_string(row.get('status', 'active')), # (!!! 修正 !!!)
                user_id=user_id 
            )
            session.add(new_vehicle)
            VEHICLE_CACHE[plate_no] = new_vehicle.id 
            print(f"  [新增] 車輛: {plate_no} (公司: {new_vehicle.company})")
        else:
            VEHICLE_CACHE[plate_no] = existing.id 
            print(f"  [跳過] 車輛已存在: {plate_no}")
    print("--- 車輛匯入完成 ---")

def import_maintenance(session):
    print("\n--- 2. 開始匯入保養維修 (import_maintenance.csv) ---")
    try:
        df = pd.read_csv("import_maintenance.csv", comment='#', parse_dates=['performed_on', 'return_date'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_maintenance.csv'。")
        return
    for _, row in df.iterrows():
        vehicle_plate_no = row.get('vehicle_plate_no')
        vehicle_id = get_vehicle_id(session, vehicle_plate_no)
        
        if not vehicle_id:
            if pd.isna(vehicle_plate_no) and pd.isna(row.get('category')) and pd.isna(row.get('notes')):
                continue 
            print(f"警告: 保養紀錄 (日期: {row.get('performed_on')}, 備註: {row.get('notes')}) 因找不到車牌 '{clean_string(vehicle_plate_no)}' 而跳過。")
            continue
        
        user_name_original = row.get('user_name')
        handler_name_original = row.get('handler_name')
        user_id = get_user_id(session, user_name_original)
        handler_id = get_user_id(session, handler_name_original)
        
        if pd.notna(user_name_original) and not user_id:
             print(f"警告: 保養紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的使用人 '{clean_string(user_name_original)}' 在員工表中找不到。")
        if pd.notna(handler_name_original) and not handler_id:
             print(f"警告: 保養紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的處理人 '{clean_string(handler_name_original)}' 在員工表中找不到。")
        
        new_maint = Maintenance(
            vehicle_id=vehicle_id, 
            user_id=user_id, 
            handler_id=handler_id,
            category=clean_string(row.get('category')), # (!!! 修正 !!!)
            vendor=clean_string(row.get('vendor')), # (!!! 修正 !!!)
            performed_on=clean_date(row.get('performed_on')),
            return_date=clean_date(row.get('return_date')),
            service_target_km=clean_int(row.get('service_target_km')),
            odometer_km=clean_int(row.get('odometer_km')),
            amount=clean_numeric(row.get('amount')),
            is_reconciled=clean_bool(row.get('is_reconciled')),
            notes=clean_string(row.get('notes')), # (!!! 修正 !!!)
            handler_notes=clean_string(row.get('handler_notes')) # (!!! 修正 !!!)
        )
        session.add(new_maint)
        
        amount = clean_numeric(row.get('amount'))
        if amount and amount > 0:
            fee_type = FeeType.maintenance_service
            category_str = str(row.get('category')).lower()
            if 'repair' in category_str:
                fee_type = FeeType.repair_parts
            
            fee_user_id = handler_id if handler_id else user_id
            
            if not fee_user_id:
                print(f"  [自動] 警告: {clean_string(vehicle_plate_no)} 的費用單缺少請款人 (處理人/使用人皆為空)。")

            new_fee = Fee(
                vehicle_id=vehicle_id,
                user_id=fee_user_id,
                receive_date=clean_date(row.get('performed_on')), 
                request_date=clean_date(row.get('performed_on')), 
                fee_type=fee_type,
                amount=amount,
                is_paid=clean_bool(row.get('is_reconciled')), 
                notes=f"自動建立 - {row.get('category')}: {row.get('notes') or ''}"
            )
            session.add(new_fee)
            print(f"  [自動] 為 {clean_string(vehicle_plate_no)} 建立 ${amount} 的費用單。")
            
    print("--- 保養維修匯入完成 ---")

def import_inspections(session):
    print("\n--- 3. 開始匯入檢驗 (import_inspections.csv) ---")
    try:
        df = pd.read_csv("import_inspections.csv", comment='#', parse_dates=['notification_date', 'inspected_on', 'return_date', 'deadline_date', 'next_due_on'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_inspections.csv'。")
        return
        
    for _, row in df.iterrows():
        vehicle_plate_no = row.get('vehicle_plate_no')
        vehicle_id = get_vehicle_id(session, vehicle_plate_no)
        
        if not vehicle_id:
            if pd.isna(vehicle_plate_no) and pd.isna(row.get('notification_date')):
                continue 
            print(f"警告: 檢驗紀錄 (通知日期: {row.get('notification_date')}) 因找不到車牌 '{clean_string(vehicle_plate_no)}' 而跳過。")
            continue
            
        user_name_original = row.get('user_name')
        handler_name_original = row.get('handler_name')
        user_id = get_user_id(session, user_name_original)
        handler_id = get_user_id(session, handler_name_original)

        if pd.notna(user_name_original) and not user_id:
             print(f"警告: 檢驗紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的使用人 '{clean_string(user_name_original)}' 在員工表中找不到。")
        if pd.notna(handler_name_original) and not handler_id:
             print(f"警告: 檢驗紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的處理人 '{clean_string(handler_name_original)}' 在員工表中找不到。")

        new_insp = Inspection(
            vehicle_id=vehicle_id, 
            user_id=user_id, 
            handler_id=handler_id,
            kind=clean_string(row.get('kind')), # (!!! 修正 !!!)
            result=clean_string(row.get('result')), # (!!! 修正 !!!)
            notification_date=clean_date(row.get('notification_date')),
            notification_source=clean_string(row.get('notification_source')), # (!!! 修正 !!!)
            deadline_date=clean_date(row.get('deadline_date')),
            inspected_on=clean_date(row.get('inspected_on')),
            return_date=clean_date(row.get('return_date')),
            next_due_on=clean_date(row.get('next_due_on')),
            amount=clean_numeric(row.get('amount')),
            is_reconciled=clean_bool(row.get('is_reconciled')),
            notes=clean_string(row.get('notes')), # (!!! 修正 !!!)
            handler_notes=clean_string(row.get('handler_notes')) # (!!! 修正 !!!)
        )
        session.add(new_insp)

        amount = clean_numeric(row.get('amount'))
        if amount and amount > 0:
            fee_user_id = handler_id if handler_id else user_id
            
            if not fee_user_id:
                print(f"  [自動] 警告: {clean_string(vehicle_plate_no)} 的檢驗費用單缺少請款人 (處理人/使用人皆為空)。")

            new_fee = Fee(
                vehicle_id=vehicle_id,
                user_id=fee_user_id,
                receive_date=clean_date(row.get('inspected_on') or row.get('notification_date')),
                request_date=clean_date(row.get('inspected_on') or row.get('notification_date')),
                fee_type=FeeType.inspection_fee,
                amount=amount,
                is_paid=clean_bool(row.get('is_reconciled')),
                notes=f"自動建立 - 檢驗費: {row.get('kind')}"
            )
            session.add(new_fee)
            print(f"  [自動] 為 {clean_string(vehicle_plate_no)} 建立 ${amount} 的檢驗費用單。")
            
    print("--- 檢驗匯入完成 ---")

def import_fees(session):
    print("\n--- 4. 開始匯入「其他」費用 (import_fees.csv) ---")
    try:
        # (!!! 修正：移除 'period_start', 'period_end' !!!)
        df = pd.read_csv("import_fees.csv", comment='#', 
                         parse_dates=['receive_date', 'request_date'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_fees.csv'。")
        return

    for _, row in df.iterrows():
        user_name_original = row.get('user_name')
        user_id = get_user_id(session, user_name_original)
        
        if not user_id:
             if pd.isna(user_name_original) and pd.isna(row.get('amount')):
                 continue 
             print(f"警告：請款紀錄 (項目: {row.get('fee_type')}, 金額: {row.get('amount')}) 因找不到員工 '{clean_string(user_name_original)}' 而跳過。")
             continue
        
        vehicle_plate_no_original = row.get('vehicle_plate_no')
        vehicle_id = get_vehicle_id(session, vehicle_plate_no_original)
        
        if pd.notna(vehicle_plate_no_original) and not vehicle_id:
            print(f"提醒：請款紀錄 (項目: {row.get('fee_type')}) 的車牌 '{clean_string(vehicle_plate_no_original)}' 非公司車輛，將作為私車請款 (不關聯車輛)。")
        
        fee_type_str = str(row.get('fee_type', 'other')).lower()
        if '加油' in fee_type_str: fee_type = FeeType.fuel_fee
        elif '停車' in fee_type_str: fee_type = FeeType.parking
        elif '全聯' in fee_type_str: fee_type = FeeType.supplies
        elif '垃圾' in fee_type_str: fee_type = FeeType.supplies
        elif '鍵盤' in fee_type_str: fee_type = FeeType.supplies
        elif '郵資' in fee_type_str: fee_type = FeeType.other
        elif '餐' in fee_type_str: fee_type = FeeType.other
        elif '保養' in fee_type_str: fee_type = FeeType.maintenance_service
        elif '機油' in fee_type_str: fee_type = FeeType.maintenance_service
        elif '零件' in fee_type_str: fee_type = FeeType.repair_parts
        elif '空氣' in fee_type_str: fee_type = FeeType.repair_parts
        elif '火星' in fee_type_str: fee_type = FeeType.repair_parts
        elif '電磁' in fee_type_str: fee_type = FeeType.repair_parts
        elif '檢驗' in fee_type_str: fee_type = FeeType.inspection_fee
        elif fee_type_str in [f.value for f in FeeType]:
            fee_type = fee_type_str
        else:
            fee_type = FeeType.other

        new_fee = Fee(
            vehicle_id=vehicle_id, 
            user_id=user_id,
            receive_date=clean_date(row.get('receive_date')),
            request_date=clean_date(row.get('request_date')),
            invoice_number=clean_string(row.get('invoice_number')), # (!!! 修正 !!!)
            fee_type=fee_type,
            amount=clean_numeric(row.get('amount')),
            is_paid=clean_bool(row.get('is_paid')),
            period_start=None, 
            period_end=None, 
            notes=clean_string(row.get('notes')) # (!!! 修正 !!!)
        )
        session.add(new_fee)
    print("--- 「其他」費用匯入完成 ---")

def import_disposals(session):
    print("\n--- 5. 開始匯入報廢 (import_disposals.csv) ---")
    try:
        df = pd.read_csv("import_disposals.csv", comment='#', parse_dates=['notification_date', 'disposed_on'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_disposals.csv'。")
        return
    for _, row in df.iterrows():
        vehicle_plate_no = row.get('vehicle_plate_no')
        vehicle_id = get_vehicle_id(session, vehicle_plate_no)
        
        if not vehicle_id:
            if pd.isna(vehicle_plate_no): continue
            print(f"警告: 報廢紀錄 (日期: {row.get('disposed_on')}) 因找不到車牌 '{clean_string(vehicle_plate_no)}' 而跳過。")
            continue
            
        user_name_original = row.get('original_user_name')
        user_id = get_user_id(session, user_name_original)
        
        if pd.notna(user_name_original) and not user_id:
             print(f"警告: 報廢紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的原使用人 '{clean_string(user_name_original)}' 在員工表中找不到。")

        new_disp = Disposal(
            vehicle_id=vehicle_id, 
            user_id=user_id,
            notification_date=clean_date(row.get('notification_date')),
            disposed_on=clean_date(row.get('disposed_on')),
            final_mileage=clean_int(row.get('final_mileage')),
            reason=clean_string(row.get('reason')) # (!!! 修正 !!!)
        )
        session.add(new_disp)
        
        vehicle = session.query(Vehicle).filter_by(id=vehicle_id).first()
        if vehicle:
            vehicle.status = VehicleStatus.retired
            print(f"  [更新] 車輛 {vehicle.plate_no} 狀態為 retired")
            
    print("--- 報廢匯入完成 ---")

def import_asset_log(session):
    print("\n--- 6. 開始匯入資產日誌 (import_asset_log.csv) ---")
    try:
        df = pd.read_csv("import_asset_log.csv", comment='#', parse_dates=['log_date'])
    except FileNotFoundError:
        print("錯誤：找不到 'import_asset_log.csv'。")
        return
    for _, row in df.iterrows():
        vehicle_plate_no = row.get('vehicle_plate_no')
        vehicle_id = get_vehicle_id(session, vehicle_plate_no)
        
        if not vehicle_id:
             if pd.isna(vehicle_plate_no) and pd.isna(row.get('description')):
                 continue 
             print(f"警告：資產紀錄 '{row.get('description')}' 因找不到車牌 '{clean_string(vehicle_plate_no)}' 而跳過。")
             continue
            
        user_name_original = row.get('user_name')
        user_id = get_user_id(session, user_name_original)
        
        if pd.notna(user_name_original) and not user_id:
             print(f"警告: 資產紀錄 (車牌: {clean_string(vehicle_plate_no)}) 的保管人 '{clean_string(user_name_original)}' 在員工表中找不到。")

        new_log = VehicleAssetLog(
            vehicle_id=vehicle_id,
            user_id=user_id,
            log_date=clean_date(row.get('log_date')),
            asset_type=clean_string(row.get('asset_type')), # (!!! 修正 !!!)
            description=clean_string(row.get('description')), # (!!! 修正 !!!)
            status=clean_string(row.get('status')), # (!!! 修正 !!!)
            notes=clean_string(row.get('notes')) # (!!! 修正 !!!)
        )
        session.add(new_log)
    print("--- 資產日誌匯入完成 ---")


# --- 主執行緒 ---
if __name__ == "__main__":
    print("=== 開始執行資料匯入 (v17 - 修正隱藏字元) ===")
    
    # 匯入順序非常重要
    
    # 1. 建立員工和車輛
    with session_scope() as session:
        import_employees(session)
    
    with session_scope() as session:
        import_vehicles(session)
    
    # 2. 建立「事件」並「自動建立費用」
    with session_scope() as session:
        import_maintenance(session)

    with session_scope() as session:
        import_inspections(session)

    # 3. 建立「其他」費用 (來自 import_fees.csv)
    with session_scope() as session:
        import_fees(session)
        
    # 4. 建立報廢和資產日誌
    with session_scope() as session:
        import_disposals(session)
        
    with session_scope() as session:
        import_asset_log(session)

    print("\n=== 所有資料匯入完畢 ===")