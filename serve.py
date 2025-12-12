# serve.py (FastAPI 專用版本)
import uvicorn

if __name__ == "__main__":
    # 這裡的 "app:app" 意思是指：
    # 找 app.py 檔案 (第一個 app) 裡面的 FastAPI 實例變數 (第二個 app)
    print("FastAPI 伺服器啟動中：http://127.0.0.1:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")