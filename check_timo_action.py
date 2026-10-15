import os
import re
import sys
import requests
from bs4 import BeautifulSoup

# Lấy cấu hình từ biến môi trường (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

STATE_FILE = "notified.txt"
URL = "https://olympic.fermat.edu.vn/wp-admin/admin-ajax.php"

HEADERS = {
    "accept": "*/*",
    "accept-language": "vi",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://olympic.fermat.edu.vn",
    "referer": "https://olympic.fermat.edu.vn/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

PAYLOAD = {
    "action": "my_special_ajax_call",
    "name": "Đồng Minh Khang",
    "birthday": "30/09/2019",
    "thi": "590",
    "phone": "",
    "option": "option1"
}

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID!")
        return
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    resp = requests.post(tg_url, json=data, timeout=10)
    resp.raise_for_status()

def main():
    # 1. Kiểm tra xem trước đó đã báo điểm chưa
    if os.path.exists(STATE_FILE):
        print("✅ Đã gửi thông báo điểm trước đó rồi (tồn tại file notified.txt). Bỏ qua!")
        sys.exit(0)

    # 2. Gọi API Fermat
    try:
        response = requests.post(URL, headers=HEADERS, data=PAYLOAD, timeout=20)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"❌ Lỗi kết nối tới Fermat: {e}")
        sys.exit(1)

    # 3. Đảm bảo phản hồi hợp lệ (tránh báo nhầm khi web sập/bảo trì)
    if "T512058" not in html_content and "ĐỒNG MINH KHANG" not in html_content.upper():
        print("⚠️ Phản hồi không chứa thông tin thí sinh T512058. Có thể web đang nghẽn hoặc bảo trì.")
        sys.exit(0)

    soup = BeautifulSoup(html_content, "html.parser")
    clean_text = soup.get_text(separator="\n", strip=True)

    # Bóc tách dòng Điểm và Giải
    diem_match = re.search(r"Điểm:\s*(.+)", clean_text, re.IGNORECASE)
    giai_match = re.search(r"Giải:\s*(.+)", clean_text, re.IGNORECASE)

    diem = diem_match.group(1).strip() if diem_match else "Không rõ"
    giai = giai_match.group(1).strip() if giai_match else "Không rõ"

    print(f"🔍 Trạng thái hiện tại -> Điểm: {diem} | Giải: {giai}")

    # 4. Kiểm tra nếu Điểm hoặc Giải đã thay đổi khác "CHƯA CÓ KẾT QUẢ"
    if "CHƯA CÓ KẾT QUẢ" not in diem.upper() or "CHƯA CÓ KẾT QUẢ" not in giai.upper():
        lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
        formatted_info = "\n".join(lines)

        msg = (
            f"🎉 <b>ĐÃ CẬP NHẬT KẾT QUẢ TIMO 2026-2027!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Thí sinh: <b>Đồng Minh Khang</b> (SBD: T512058)\n"
            f"🎯 <b>Điểm: {diem}</b>\n"
            f"🏆 <b>Giải: {giai}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 <i>Chi tiết trên hệ thống:</i>\n"
            f"<pre>{formatted_info}</pre>\n\n"
            f"👉 Tra cứu tại: https://olympic.fermat.edu.vn/"
        )
        send_telegram(msg)
        print("🎉 Đã gửi thông báo điểm về Telegram!")

        # Tạo file đánh dấu đã báo điểm để các lần chạy sau tự dừng
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(f"Đã báo kết quả: Điểm={diem}, Giải={giai}\n")
    else:
        print("⏳ Vẫn chưa có kết quả mới.")

if __name__ == "__main__":
    main()
