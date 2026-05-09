from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from ai_engine import analyze_screenshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BVHD AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "OK",
        "app": "BVHD AI - Bao Ve Hoc Duong",
        "version": "1.0.0",
        "school": "PT DTNT THPT An Giang 1",
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/analyze")
async def analyze(request: Request):
    try:
        # Thử đọc raw binary trước
        image_bytes = await request.body()

        # Nếu không có, thử đọc form
        if not image_bytes:
            form = await request.form()
            for key in form:
                value = form[key]
                if hasattr(value, "read"):
                    image_bytes = await value.read()
                    break

        if not image_bytes or len(image_bytes) == 0:
            return JSONResponse(content={"loi": True, "phan_tich": "Khong nhan duoc anh"})

        logger.info(f"Nhan anh: {len(image_bytes)//1024} KB")
        result = await analyze_screenshot(image_bytes)
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Loi: {e}")
        return JSONResponse(content={"loi": True, "phan_tich": str(e)})
