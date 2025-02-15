from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_app.routes import device_router
from fastapi_app.routes import optimization_router
app = FastAPI(title='PID Agent API')

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(device_router.router, prefix='/api/device', tags=['device'])
app.include_router(optimization_router.router, prefix='/api/optimization', tags=['optimization'])

@app.get('/health')
async def health_check():
    return {'status': 'ok'}

@app.get("/")
async def root():
    return {"message": "PID Agent API"}
