# Hướng dẫn Xây dựng Bot tự động lấy dữ liệu lịch sân Alobo (Không can thiệp hệ thống)

Vì bạn đang dùng Python cho Chatbot (có file `app.py`, `requirements.txt`), chúng ta sẽ dùng thư viện **Playwright (Python)** để viết Bot này. Việc dùng chung Python sẽ giúp bạn dễ dàng kết hợp dữ liệu Bot lấy được vào thẳng con Chatbot mà không cần công nghệ mới.

## 1. Nguyên lý hoạt động (Cam kết chỉ Đọc - Không can thiệp)
1. Bot sẽ khởi động một trình duyệt Google Chrome ảo (chạy ngầm, không hiện giao diện).
2. Tự động truy cập `https://app.alobo.vn/` và đăng nhập bằng tài khoản của bạn (tài khoản xem lịch).
3. Sử dụng công cụ "đánh hơi" mạng (Network Interception) tích hợp trong Playwright để lắng nghe các luồng dữ liệu (Firestore stream) đi vào trình duyệt.
4. Lọc lấy các thông tin về `LockYard` (khoá sân) và `Services` (lịch đặt).
5. Phân tích dữ liệu đó và gọi API của Google Sheets để ghi dữ liệu xuống.
6. Mọi thao tác đều hoàn toàn là 1 user truy cập web bình thường, không sửa/xoá/can thiệp vào hệ thống của Alobo.

## 2. Làm thế nào để chạy 24/7 không cần bật máy tính?
Để code tự động chạy 24/24, bạn không thể để ở máy tính cá nhân (vì tắt máy/mất mạng là bot sẽ chết). Bạn cần đưa mã nguồn (bao gồm cả Chatbot và đoạn Bot Alobo này) lên một **VPS (Máy chủ ảo)** hoặc **Cloud Platform**.

**Gợi ý các lựa chọn máy chủ:**
- **Giải pháp rẻ nhất/Ổn định (Khuyên dùng):** Thuê một VPS ở Việt Nam (như Vietnix, TinoHost, HostVN). Giá khoảng 80.000đ - 120.000đ / tháng. Máy chủ này chạy Windows hoặc Ubuntu tuỳ bạn chọn, hoạt động 24/7. Bạn copy thư mục `E:\Du_An_Pick\CHATBOT` lên đó, cài Python và bật chạy là xong.
- **Giải pháp miễn phí (Cloud):** Đẩy code lên **Render.com** hoặc **Railway.app** (Nền tảng Cloud). Tuy nhiên, vì trình duyệt ảo (Playwright) tốn khá nhiều RAM, các gói miễn phí có thể bị quá tải (Out of Memory).
- **Giải pháp Google Cloud Free Tier:** Đăng ký tài khoản Google Cloud và tạo một máy ảo e2-micro (miễn phí vĩnh viễn), cài Ubuntu và chạy script Python trên đó.

## 3. Các bước cài đặt để bắt đầu ngay bây giờ

Để bắt đầu ngay trên máy của bạn (thử nghiệm trước khi đưa lên máy chủ), hãy làm theo các bước sau trong Terminal ở thư mục `E:\Du_An_Pick\CHATBOT`:

**Bước 1: Cài đặt thư viện Playwright**
```bash
pip install playwright
playwright install chromium
```

**Bước 2: Cài đặt thư viện Google Sheets**
```bash
pip install gspread oauth2client
```

**Bước 3: Cấu hình mã nguồn**
Tôi sẽ giúp bạn tạo một file tên là `alobo_scraper.py` trong thư mục này chứa mã nguồn để bot đăng nhập và bắt dữ liệu.

---
*Vui lòng xác nhận để tôi tiến hành viết file mã nguồn `alobo_scraper.py` cho bạn!*
