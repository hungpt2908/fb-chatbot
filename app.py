from flask import Flask, request
import requests
import os
import google.generativeai as genai

app = Flask(__name__)

# Lấy các biến môi trường
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Cấu hình Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Khởi tạo model AI
    model = genai.GenerativeModel('gemini-1.5-flash')

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
                        
                        if text.strip().lower() in ['xin chào', 'hi', 'hello']:
                            send_button_message(sender_id)
                        else:
                            # Chuyển câu hỏi cho Gemini xử lý
                            handle_gemini_response(sender_id, text)

                    # 2. Xử lý khi khách bấm nút (Postback)
                    if messaging_event.get('postback'):
                        payload = messaging_event['postback']['payload']
                        handle_postback(sender_id, payload)
        return 'EVENT_RECEIVED', 200

def handle_gemini_response(recipient_id, text):
    if not GEMINI_API_KEY:
        send_text_message(recipient_id, "Hệ thống AI đang được bảo trì. Vui lòng liên hệ hotline nhé!")
        return

    try:
        # Nhắc AI đóng vai nhân viên tư vấn sân bóng Pickleball
        prompt = f"""Bạn là nhân viên tư vấn nhiệt tình của một cụm sân Pickleball.
        Hãy trả lời ngắn gọn, thân thiện (dưới 3 câu) cho câu hỏi sau của khách hàng: {text}"""
        
        response = model.generate_content(prompt)
        reply_text = response.text
        
        send_text_message(recipient_id, reply_text)
    except Exception as e:
        print("Lỗi khi gọi Gemini API:", e)
        send_text_message(recipient_id, "Dạ em đang bận chút xíu, anh/chị đợi em tí nhé!")

def send_button_message(recipient_id):
    headers = {'Content-Type': 'application/json'}
    params = {'access_token': PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": "Dạ em chào anh/chị, anh/chị muốn hỏi thông tin gì ạ?",
                    "buttons": [
                        {"type": "postback", "title": "Bảng giá sân", "payload": "BANG_GIA"},
                        {"type": "postback", "title": "Đặt lịch chơi", "payload": "DAT_LICH"},
                        {"type": "postback", "title": "Địa chỉ sân", "payload": "DIA_CHI"}
                    ]
                }
            }
        }
    }
    requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, headers=headers, json=data)

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
