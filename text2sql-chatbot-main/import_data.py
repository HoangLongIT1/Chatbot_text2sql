import pandas as pd
from sqlalchemy import create_engine
import os

# --- CẤU HÌNH ---

DB_USER = 'postgres'
DB_PASS = 'your_password_here' 
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_NAME = 'baogia_db'
CSV_FILE = 'Lich_Su_Bao_Gia.csv' 

# Connection String cho Postgres
DB_URI = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def process_and_import():
    print("Đang đọc file csv...")
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file '{CSV_FILE}'. Hãy kiểm tra lại tên file.")
        return

    column_mapping = {
        'Mã Dự Án': 'project_id',
        'Tên Dự Án': 'project_name',
        'Loại Công Trình': 'building_type',
        'Địa Điểm': 'location',
        'Tổng Diện Tích (m2)': 'total_area',
        'Tổng Khối Lượng (Tấn)': 'total_weight',
        'Đơn Giá (VND/kg)': 'unit_price',
        'Tổng Giá Trị (VNĐ)': 'total_value',
        'Thời Gian Thi Công (Ngày)': 'construction_duration',
        'Ngày Báo Giá': 'quotation_date',
        'Kết Quả': 'result'
    }
    df.rename(columns=column_mapping, inplace=True)

    print("Đang làm sạch dữ liệu...")
    
    # Chuyển về dạng số thực (float)
    if 'total_value' in df.columns:
        df['total_value'] = df['total_value'].astype(str).str.replace(',', '').astype(float)
    
    if 'quotation_date' in df.columns:
        df['quotation_date'] = pd.to_datetime(df['quotation_date'], format='%d/%m/%Y', errors='coerce')

    print("Đang đẩy vào PostgreSQL...")
    
    try:
        engine = create_engine(DB_URI)
        # if_exists='replace': Xóa bảng cũ làm lại mới
        df.to_sql('lich_su_bao_gia', engine, index=False, if_exists='replace')
        print(f"Đã import {len(df)} dòng vào bảng 'lich_su_bao_gia'.")
        
        print("\n--- Dữ liệu mẫu sau khi import ---")
        print(df[['project_name', 'total_value', 'quotation_date']].head())
        
    except Exception as e:
        print(f"Lỗi kết nối Database: {e}")
        print("Kiểm tra lại mật khẩu và tên database trong phần CẤU HÌNH.")

if __name__ == "__main__":
    process_and_import()