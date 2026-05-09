from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
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
        form = await request.form()
        # Nhận file từ bất kỳ field nào
        file = None
        for key in form:
            value = form[key]
            if hasattr(value, 'read'):
                file = value
                break

        if file is None:
            raise HTTPException(status_code=400, detail="Khong tim thay file anh")

        image_bytes = await file.read()

        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="File rong")

        logger.info(f"Nhan anh: {len(image_bytes)//1024} KB")
        result = await analyze_screenshot(image_bytes)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Loi: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
