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
# Lưu trữ ID của lịch trình theo từng khách hàng
user_jobs = {}

# Lấy các biến môi trường
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
# Hỗ trợ nhận nhiều key ngăn cách bởi dấu phẩy
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
    """Gửi tin nhắn chăm sóc khách hàng sau 30 phút im lặng"""
    text = "Dạ Thado Pickleball đang có khung giờ chơi ưu đãi chỉ từ 50.000đ/giờ. Anh/chị muốn em kiểm tra sân trống trong hôm nay hoặc cuối tuần này không ạ? Chỉ cần gửi giúp em ngày + giờ muốn chơi, bên em kiểm tra ngay cho mình."
    send_text_message(recipient_id, text)
    if recipient_id in user_jobs:
        del user_jobs[recipient_id]

def schedule_followup(sender_id):
    """Cài đặt đồng hồ đếm ngược 30 phút"""
    if sender_id in user_jobs:
        try:
            scheduler.remove_job(user_jobs[sender_id])
        except Exception:
            pass
    run_date = datetime.now() + timedelta(minutes=30)
    job = scheduler.add_job(send_followup_message, 'date', run_date=run_date, args=[sender_id])
    user_jobs[sender_id] = job.id

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
                            handle_gemini_response(sender_id, text)

                    if messaging_event.get('postback'):
                        payload = messaging_event['postback']['payload']
                        handle_postback(sender_id, payload)
        return 'EVENT_RECEIVED', 200

def handle_gemini_response(recipient_id, text):
    if not GEMINI_API_KEYS:
        send_text_message(recipient_id, "Dạ hệ thống AI bên em đang bảo trì. Anh/chị vui lòng liên hệ hotline 0989 567 709 nhé ạ!")
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
