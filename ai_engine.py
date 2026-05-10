import os
import io
import json
import base64
import logging
from PIL import Image
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

PROMPT = """Bạn là chuyên gia tâm lý học đường Việt Nam.
Phân tích nội dung hội thoại trong ảnh chụp màn hình tin nhắn (Zalo, Messenger, Facebook...).
Phân loại theo ĐÚNG MỘT trong 4 mức độ:
- trêu_đùa: Chế giễu nhẹ về ngoại hình/học tập, không có ý xấu rõ ràng. Mức 1/4.
- xúc_phạm: Lăng mạ, miệt thị, dùng ngôn ngữ thô tục, hạ thấp nhân phẩm. Mức 2/4.
- đe_dọa: Hăm dọa thân thể, tinh thần, hoặc đe dọa phát tán thông tin nhạy cảm. Mức 3/4.
- cô_lập: Kêu gọi tẩy chay, loại trừ nạn nhân khỏi nhóm chat/cộng đồng. Mức 4/4.

Lưu ý đặc biệt — Phát hiện "Bạo lực lạnh":
Chú ý các dấu hiệu ngầm như: mỉa mai có vẻ vô hại, dùng emoji để che giấu ý xấu,
nói đúng sự thật theo cách sỉ nhục, loại trừ ngầm không nói thẳng.

Trả về JSON thuần túy (KHÔNG có markdown, KHÔNG có ```, KHÔNG có giải thích thêm):
{
  "muc_do": "trêu_đùa | xúc_phạm | đe_dọa | cô_lập",
  "do_nghiem_trong": 1,
  "mau_sac": "xanh | vang | cam | do",
  "tom_tat": "1 câu tóm tắt vấn đề chính",
  "cau_nguy_hiem": "trích dẫn câu nguy hiểm nhất hoặc null nếu không có",
  "phan_tich": "phân tích chi tiết 2-3 câu, giải thích vì sao phân loại như vậy",
  "loi_khuyen_nan_nhan": "lời khuyên cụ thể cho học sinh bị bắt nạt",
  "loi_khuyen_giao_vien": "thông tin quan trọng cần báo giáo viên nếu can_bao_cao=true",
  "can_bao_cao": true,
  "phan_tram_tin_cay": 85
}

Quy tắc mau_sac: trêu_đùa=xanh, xúc_phạm=vang, đe_dọa=cam, cô_lập=do
Quy tắc can_bao_cao: true nếu do_nghiem_trong >= 3, ngược lại false"""


async def analyze_screenshot(image_bytes: bytes) -> dict:
    try:
        # Mở và tối ưu ảnh
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1080, 1920), Image.LANCZOS)

        # Chuyển sang JPEG
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_bytes = buf.getvalue()

        # Chuyển sang base64
        img_base64 = base64.standard_b64encode(img_bytes).decode("utf-8")

        logger.info(f"Gọi Claude API ({len(img_bytes)//1024} KB)...")

        # Gọi Claude API
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": img_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": PROMPT
                        }
                    ],
                }
            ],
        )

        raw = message.content[0].text.strip()
        logger.info(f"Claude response: {raw[:200]}")

        # Làm sạch markdown nếu có
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

        # Bổ sung các trường mặc định
        result.setdefault("muc_do", "trêu_đùa")
        result.setdefault("do_nghiem_trong", 1)
        result.setdefault("mau_sac", "xanh")
        result.setdefault("tom_tat", "Không xác định được nội dung")
        result.setdefault("phan_tich", "Không phân tích được")
        result.setdefault("loi_khuyen_nan_nhan", "Hãy lưu bằng chứng và chia sẻ với người lớn tin cậy.")
        result.setdefault("loi_khuyen_giao_vien", "")
        result.setdefault("can_bao_cao", False)
        result.setdefault("phan_tram_tin_cay", 70)
        result.setdefault("cau_nguy_hiem", None)

        logger.info(f"Kết quả: {result['muc_do']} (mức {result['do_nghiem_trong']})")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON: {e}")
        return _error_response("AI trả về định dạng không hợp lệ. Vui lòng thử lại.")
    except Exception as e:
        logger.error(f"Lỗi: {e}")
        return _error_response(str(e))


def _error_response(message: str) -> dict:
    return {
        "loi": True,
        "muc_do": "lỗi",
        "do_nghiem_trong": 0,
        "mau_sac": "xam",
        "tom_tat": "Có lỗi xảy ra",
        "phan_tich": message,
        "loi_khuyen_nan_nhan": "Vui lòng thử lại với ảnh rõ hơn.",
        "loi_khuyen_giao_vien": "",
        "can_bao_cao": False,
        "phan_tram_tin_cay": 0,
        "cau_nguy_hiem": None,
    }
