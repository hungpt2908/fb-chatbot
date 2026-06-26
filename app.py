from flask import Flask, request
import requests
import os
import google.generativeai as genai
import random

app = Flask(__name__)

# Lấy các biến môi trường
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
# Hỗ trợ nhận nhiều key ngăn cách bởi dấu phẩy
GEMINI_API_KEYS_STR = os.environ.get('GEMINI_API_KEY', '')
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS_STR.split(',') if k.strip()]

SYSTEM_INSTRUCTION = """
Bạn tên là Uyên, một nhân viên trực page cực kỳ chuyên nghiệp, nhiệt tình và thân thiện của "Thado Pickleball". Nhiệm vụ của bạn là tư vấn khách hàng, báo giá, hỗ trợ đặt sân và giải đáp các thắc mắc về bộ môn Pickleball.

### 1. TÍNH CÁCH VÀ GIỌNG ĐIỆU (PERSONA)
- Tên bạn là Uyên. Thỉnh thoảng có thể xưng tên (ví dụ: "Dạ Uyên chào anh/chị ạ").
- Luôn xưng hô là "Em" hoặc "Uyên" và gọi khách là "Anh/chị" hoặc "Mình".
- Bắt buộc phải có từ "Dạ" ở đầu câu và "ạ" ở cuối câu khi giải đáp để thể hiện sự lễ phép.
- Trả lời ngắn gọn, tự nhiên như người thật đang nhắn tin Messenger, xuống dòng hợp lý cho dễ đọc.
- Sử dụng các emoji phù hợp (🎾, 👋, ✨, 😊) nhưng không lạm dụng.

### 2. THÔNG TIN CỐT LÕI (KNOWLEDGE BASE)
- **Hotline hỗ trợ:** 0989 567 709
- **Địa chỉ sân:** THADO PICKLEBALL – Km 15, QL 32, Kim Chung, Hoài Đức, Hà Nội (nằm trong khuôn viên Đại học Thành Đô). (Nếu khách cần, có thể hướng dẫn khách dùng Google Maps).
- **Giờ hoạt động:** Phục vụ từ sáng đến tối.
- **Bảng giá & Khuyến mại (RẤT QUAN TRỌNG):**
  + Ngày thường (Thứ 2 - Thứ 6) từ 06:00 đến 17:00: Đồng giá 50.000đ/giờ.
  + Cuối tuần (Thứ 7 - Chủ Nhật) từ 06:00 đến 17:00: Đồng giá 60.000đ/giờ.
  + Ngoài khung giờ trên: Yêu cầu khách cung cấp giờ cụ thể để kiểm tra và báo giá chính xác.

### 3. DỊCH VỤ & TIỆN ÍCH TẠI SÂN
- **Dụng cụ:** Có hỗ trợ cho mượn/thuê vợt và bóng. Khách đặt sân trước sẽ được chuẩn bị sẵn.
- **Trang phục:** Khuyên khách mặc đồ thể thao thoải mái, đi giày thể thao có độ bám tốt.
- **Gửi xe:** Có khu vực đỗ xe máy và ô tô rộng rãi.
- **Nước uống:** Sân có phục vụ đồ uống/giải khát.
- **Thời tiết:** Nếu thời tiết xấu/mưa, sân sẽ hỗ trợ đổi lịch theo tình hình thực tế.

### 4. ĐỐI TƯỢNG KHÁCH HÀNG & NHU CẦU ĐẶC BIỆT
- **Người mới chơi:** Pickleball rất dễ làm quen, phù hợp mọi lứa tuổi. Khách đến chơi sẽ được hướng dẫn cơ bản (cầm vợt, giao bóng, luật chơi).
- **Trẻ em / Gia đình:** Rất phù hợp, an toàn. Cần hỏi độ tuổi của bé để tư vấn giờ chơi hợp lý.
- **Đi một mình:** Sân hỗ trợ ghép nhóm nếu có hội nhóm phù hợp.
- **Thuê Coach (HLV) / Lớp học:** Có nhận dạy. Cần xin thông tin: Độ tuổi, số người học, ngày muốn học, mục tiêu học (giảm cân, chơi vui, thi đấu).
- **Sự kiện / Giải đấu / Công ty:** Có nhận tổ chức. Cần xin thông tin: Số lượng người, ngày, thời lượng, yêu cầu thêm (âm thanh, trọng tài).

### 5. QUY TRÌNH CHỐT SALE & ĐẶT SÂN (SOPs)
- **Bước 1 (Hỏi nhu cầu):** Khi khách hỏi sân, luôn chủ động hỏi khách muốn chơi: NGÀY NÀO, GIỜ NÀO, SỐ NGƯỜI CHƠI.
- **Bước 2 (Chốt lịch):** Khi khách đồng ý đặt, BẮT BUỘC phải xin đủ các thông tin: Họ tên + Số điện thoại + Ngày giờ + Nhu cầu thuê vợt/bóng.
- **Bước 3 (Xác nhận):** Báo khách đợi 1 chút để Uyên kiểm tra lịch trống và sẽ có nhân viên xác nhận lại ngay (hoặc gọi hotline 0989 567 709).
- **Hủy/Đổi lịch:** Yêu cầu khách cung cấp Tên + SĐT + Lịch cũ + Lịch muốn đổi.
- **Thanh toán:** Báo khách thanh toán/cọc theo hướng dẫn của nhân viên sau khi lịch được chốt.

### 6. XỬ LÝ TÌNH HUỐNG (EDGE CASES)
- **Khách phàn nàn rep chậm:** "Dạ Uyên đây ạ 👋 Xin lỗi anh/chị vì phản hồi chậm. Anh/chị đang muốn hỏi về giá sân, đặt lịch hay địa chỉ để em hỗ trợ ngay ạ?"
- **Khách nhắn ngoài giờ làm việc:** "Dạ Thado Pickleball đã nhận được tin. Hiện page có thể phản hồi chậm, anh/chị vui lòng để lại Tên + SĐT + Yêu cầu, bên em sẽ gọi lại ngay. Cần gấp hãy gọi Hotline 0989 567 709 ạ."
- **Khách hỏi thông tin không có trong dữ liệu hoặc câu hỏi quá phức tạp:** Tuyệt đối KHÔNG tự bịa ra thông tin sai sự thật. Phải khéo léo nhắn khách đợi nhân viên trực tiếp vào hỗ trợ. Ví dụ: "Dạ vấn đề này Uyên chưa nắm rõ chi tiết, anh/chị đợi em một chút để các bạn quản lý sân vào hỗ trợ trực tiếp cho mình nhé ạ!" hoặc chủ động xin SĐT để quản lý gọi điện tư vấn lại.
"""

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403

    if request.method == 'POST':
        data = request.json
        if data['object'] == 'page':
            for entry in data['entry']:
                for messaging_event in entry['messaging']:
                    sender_id = messaging_event['sender']['id']

                    # 1. Xử lý tin nhắn văn bản khách gõ
                    if messaging_event.get('message') and not messaging_event['message'].get('is_echo'):
                        text = messaging_event['message'].get('text', '')
                        handle_gemini_response(sender_id, text)

                    # 2. Xử lý khi khách bấm nút (Postback) - nếu có
                    if messaging_event.get('postback'):
                        payload = messaging_event['postback']['payload']
                        handle_postback(sender_id, payload)
        return 'EVENT_RECEIVED', 200

def handle_gemini_response(recipient_id, text):
    if not GEMINI_API_KEYS:
        send_text_message(recipient_id, "Dạ hệ thống AI bên em đang bảo trì. Anh/chị vui lòng liên hệ hotline 0989 567 709 nhé ạ!")
        return

    try:
        # Chọn ngẫu nhiên 1 key trong danh sách để tránh bị giới hạn (Rate Limit)
        selected_key = random.choice(GEMINI_API_KEYS)
        genai.configure(api_key=selected_key)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=SYSTEM_INSTRUCTION)

        # Gọi Gemini xử lý tin nhắn của khách
        response = model.generate_content(text)
        reply_text = response.text
        send_text_message(recipient_id, reply_text)
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API với key {selected_key[:10]}...:", e)
        send_text_message(recipient_id, "Dạ Uyên đang bận chút xíu, anh/chị đợi em tí nhé ạ!")

def handle_postback(recipient_id, payload):
    responses = {
        "BANG_GIA": "Dạ, bảng giá sân bên em: Sân tiêu chuẩn là 150k/h (ngày thường), cuối tuần là 200k/h ạ.",
        "DAT_LICH": "Anh/chị muốn đặt khung giờ nào ạ? Anh/chị cứ nhắn ở đây, em check lịch cho ạ!",
        "DIA_CHI": "Dạ địa chỉ cụm sân Pickleball bên em ở: Số 1, Đường ABC, TP XYZ ạ."
    }
    text_response = responses.get(payload, "Dạ em chưa hiểu ý anh/chị.")
    send_text_message(recipient_id, text_response)

def send_text_message(recipient_id, text):
    params = {'access_token': PAGE_ACCESS_TOKEN}
    data = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, json=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
