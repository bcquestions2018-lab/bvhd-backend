import os
import io
import json
import logging
from PIL import Image
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

PROMPT = """Ban la chuyen gia tam ly hoc duong Viet Nam.
Phan tich noi dung hoi thoai trong anh chup man hinh tin nhan.
Phan loai theo DUNG MOT trong 4 muc do:
- treu_dua: Che gieu nhe, khong co y xau. Muc 1/4.
- xuc_pham: Lang ma, miet thi, ha thap nhan pham. Muc 2/4.
- de_doa: Ham doa than the, tinh than. Muc 3/4.
- co_lap: Keu goi tay chay, loai tru khoi nhom. Muc 4/4.

Tra ve JSON thuan tuy (KHONG markdown, KHONG giai thich):
{
  "muc_do": "treu_dua | xuc_pham | de_doa | co_lap",
  "do_nghiem_trong": 1,
  "mau_sac": "xanh | vang | cam | do",
  "tom_tat": "1 cau tom tat",
  "cau_nguy_hiem": "cau nguy hiem nhat hoac null",
  "phan_tich": "phan tich 2-3 cau",
  "loi_khuyen_nan_nhan": "loi khuyen cu the",
  "loi_khuyen_giao_vien": "thong tin can bao giao vien",
  "can_bao_cao": true,
  "phan_tram_tin_cay": 85
}

Quy tac mau_sac: treu_dua=xanh, xuc_pham=vang, de_doa=cam, co_lap=do
Quy tac can_bao_cao: true neu do_nghiem_trong >= 3"""


async def analyze_screenshot(image_bytes: bytes) -> dict:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1080, 1920), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_bytes = buf.getvalue()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=PROMPT),
            ],
        )

        raw = response.text.strip()
        if "```" in raw:
            parts = raw.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    raw = p
                    break

        result = json.loads(raw)
        result.setdefault("muc_do", "treu_dua")
        result.setdefault("do_nghiem_trong", 1)
        result.setdefault("mau_sac", "xanh")
        result.setdefault("tom_tat", "Khong xac dinh")
        result.setdefault("phan_tich", "Khong phan tich duoc")
        result.setdefault("loi_khuyen_nan_nhan", "Hay luu bang chung va chia se voi nguoi lon.")
        result.setdefault("loi_khuyen_giao_vien", "")
        result.setdefault("can_bao_cao", False)
        result.setdefault("phan_tram_tin_cay", 70)
        result.setdefault("cau_nguy_hiem", None)
        return result

    except Exception as e:
        logger.error(f"Loi: {e}")
        return {
            "loi": True,
            "muc_do": "loi",
            "do_nghiem_trong": 0,
            "mau_sac": "xam",
            "tom_tat": "Co loi xay ra",
            "phan_tich": str(e),
            "loi_khuyen_nan_nhan": "Vui long thu lai.",
            "loi_khuyen_giao_vien": "",
            "can_bao_cao": False,
            "phan_tram_tin_cay": 0,
            "cau_nguy_hiem": None,
        }
