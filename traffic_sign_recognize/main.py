from routers.router import router
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

#实例化
app = FastAPI()
#静态文件路径
app.mount("/static", StaticFiles(directory="static"), name="static")
#路由
app.include_router(router)
#启动项目
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)