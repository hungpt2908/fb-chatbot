from flask import Flask, request
import requests
import os
from google import genai
from google.genai import types
import random
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

app = Flask(__name__)

# Khởi tạo bộ đếm thời gian chạy ngầm
scheduler = BackgroundScheduler()
scheduler.start()

# Lưu trữ trạng thái bám đuổi theo từng khách hàng
# Cấu trúc: { sender_id: { "job_id": "...", "followup_count": 0, "done": False } }
user_tracking = {}

# Các tin nhắn bám đuổi - mỗi lần khác nhau để tự nhiên
FOLLOWUP_MESSAGES = [
    "Mình ơi, mình còn đang cần tư vấn gì thêm không nè? 😊",
    "Mình ơi bên em cuối tuần này đang còn vài khung giờ đẹp, mình muốn em check giúp không nà? 🎾",
    "Hi mình, nếu cần hỗ trợ gì thêm cứ nhắn em nha! Chúc mình 1 ngày vui vẻ 😄",
]

# Lấy các biến môi trường
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
GEMINI_API_KEYS_STR = os.environ.get('GEMINI_API_KEY', '')
GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEYS_STR.split(',') if k.strip()]

def get_system_instruction():
    try:
        with open('instruction.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print("Lỗi đọc file instruction.txt:", e)
        return "Bạn là nhân viên tư vấn khách hàng."


def send_followup_message(recipient_id):
    """Gửi tin nhắn bám đuổi sau 3 phút im lặng (tối đa 3 lần)"""
    tracking = user_tracking.get(recipient_id)
    if not tracking or tracking.get("done"):
        return

    count = tracking.get("followup_count", 0)

    # Đã gửi đủ 3 lần → dừng lại
    if count >= 3:
        tracking["done"] = True
        return

    # Chọn tin nhắn theo lần gửi
    text = FOLLOWUP_MESSAGES[count]
    send_text_message(recipient_id, text)

    # Cập nhật số lần đã gửi
    tracking["followup_count"] = count + 1

    # Nếu chưa đủ 3 lần → hẹn giờ tiếp sau 3 phút nữa
    if tracking["followup_count"] < 3:
        run_date = datetime.now() + timedelta(minutes=3)
        job = scheduler.add_job(send_followup_message, 'date', run_date=run_date, args=[recipient_id])
        tracking["job_id"] = job.id
    else:
        tracking["done"] = True


def schedule_followup(sender_id):
    """Reset đồng hồ bám đuổi khi khách nhắn tin"""
    tracking = user_tracking.get(sender_id)

    # Hủy lịch trình cũ nếu có
    if tracking and tracking.get("job_id"):
        try:
            scheduler.remove_job(tracking["job_id"])
        except Exception:
            pass

    # Khi khách nhắn tin → reset bộ đếm, bắt đầu lại từ đầu
    user_tracking[sender_id] = {
        "job_id": None,
        "followup_count": 0,
        "done": False
    }

    # Hẹn giờ gửi tin nhắn bám đuổi lần 1 sau 3 phút
    run_date = datetime.now() + timedelta(minutes=3)
    job = scheduler.add_job(send_followup_message, 'date', run_date=run_date, args=[sender_id])
    user_tracking[sender_id]["job_id"] = job.id


def mark_done(sender_id):
    """Đánh dấu khách đã chốt đơn → dừng bám đuổi"""
    if sender_id in user_tracking:
        tracking = user_tracking[sender_id]
        tracking["done"] = True
        if tracking.get("job_id"):
            try:
                scheduler.remove_job(tracking["job_id"])
            except Exception:
                pass


@app.route('/')
def home():
    return "Bot is awake and running!", 200

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
                    schedule_followup(sender_id)

                    if messaging_event.get('message') and not messaging_event['message'].get('is_echo'):
                        text = messaging_event['message'].get('text', '')
                        if text:
                            # Phát hiện khách đã chốt đơn (đã cung cấp SĐT)
                            if any(keyword in text.lower() for keyword in ['ok em ghi nhận', 'cảm ơn', 'thank', 'ok xong', 'đã chuyển', 'đã cọc']):
                                mark_done(sender_id)
                            handle_gemini_response(sender_id, text)

                    if messaging_event.get('postback'):
                        payload = messaging_event['postback']['payload']
                        handle_postback(sender_id, payload)
        return 'EVENT_RECEIVED', 200

def handle_gemini_response(recipient_id, text):
    if not GEMINI_API_KEYS:
        send_text_message(recipient_id, "Dạ hệ thống bên em đang bảo trì, mình liên hệ hotline 0989 567 709 giúp em nha!")
        return

    try:
        selected_key = random.choice(GEMINI_API_KEYS)
        client = genai.Client(api_key=selected_key)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=get_system_instruction(),
            )
        )
        reply_text = response.text

        # Nếu AI xác nhận đã chốt đơn → dừng bám đuổi
        if any(kw in reply_text.lower() for kw in ['em ghi nhận rồi', 'giữ chỗ', 'xác nhận lại', 'đã ghi nhận']):
            mark_done(recipient_id)

        send_text_message(recipient_id, reply_text)
    except Exception as e:
        print(f"Lỗi khi gọi Gemini API với key {selected_key[:10]}...:", e)
        send_text_message(recipient_id, "Sorry mình, em bị lỗi mạng chút xíu 😅 Mình nhắn lại giúp em nha!")

def handle_postback(recipient_id, payload):
    responses = {
        "BANG_GIA": "Ngày thường 50k/h, cuối tuần 60k/h thôi mình ơi 😊 Mình muốn chơi ngày nào?",
        "DAT_LICH": "Mình muốn đặt khung giờ nào nè? Cứ nhắn em check lịch cho!",
        "DIA_CHI": "Bên em ở Km 15, QL 32, Kim Chung, Hoài Đức, HN nha (trong khuôn viên ĐH Thành Đô). Search Google Maps 'Thado Pickleball' là ra luôn mình ơi 📍"
    }
    text_response = responses.get(payload, "Mình nhắn rõ hơn giúp em nha, em chưa hiểu ý mình 😊")
    send_text_message(recipient_id, text_response)

def send_text_message(recipient_id, text):
    params = {'access_token': PAGE_ACCESS_TOKEN}
    data = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, json=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
