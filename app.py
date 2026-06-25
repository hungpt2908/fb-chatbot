from flask import Flask, request
import requests
import os

app = Flask(__name__)

# Render sẽ tự đọc các biến môi trường này
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Bước này để Facebook xác minh Webhook của bạn
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403

    if request.method == 'POST':
        # Nhận tin nhắn gửi đến
        data = request.json
        if data['object'] == 'page':
            for entry in data['entry']:
                for messaging_event in entry['messaging']:
                    sender_id = messaging_event['sender']['id']

                    # 1. Nếu khách gõ chữ
                    if messaging_event.get('message'):
                        text = messaging_event['message'].get('text', '').lower()
                        if 'xin chào' in text:
                            send_button_message(sender_id)

                    # 2. Nếu khách bấm nút (Postback)
                    if messaging_event.get('postback'):
                        payload = messaging_event['postback']['payload']
                        handle_postback(sender_id, payload)
        return 'EVENT_RECEIVED', 200

def send_button_message(recipient_id):
    # Gửi 3 nút bấm
    headers = {'Content-Type': 'application/json'}
    params = {'access_token': PAGE_ACCESS_TOKEN}
    data = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": "Anh/chị muốn hỏi thông tin nào ạ?",
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
    # Trả lời theo nút khách bấm
    responses = {
        "BANG_GIA": "Dạ, bảng giá sân bên em: Sân 5 là 300k/h, sân 7 là 500k/h ạ.",
        "DAT_LICH": "Anh/chị muốn đặt khung giờ nào ạ? Hoặc gọi Hotline: 09xx.xxx.xxx",
        "DIA_CHI": "Dạ địa chỉ sân bên em ở: Số 1, Đường ABC. Link Maps:..."
    }
    text_response = responses.get(payload, "Dạ em chưa hiểu ý anh/chị.")

    params = {'access_token': PAGE_ACCESS_TOKEN}
    data = {"recipient": {"id": recipient_id}, "message": {"text": text_response}}
    requests.post("https://graph.facebook.com/v18.0/me/messages", params=params, json=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
