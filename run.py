import uvicorn
from app.settings import PORT
if __name__ == "__main__":
    # 只綁本機：這是你一個人的管理台
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT)
