import sys
import google.generativeai as genai

if len(sys.argv) < 2:
    print("Vui lòng cung cấp API key")
    sys.exit(1)

api_key = sys.argv[1].strip()
print(f"Đang kiểm tra API Key: {api_key[:10]}...")

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Xin chào, bạn có nghe rõ không?")
    print("✅ THÀNH CÔNG: API hoạt động tốt! Trả lời từ AI:", response.text)
except Exception as e:
    print("❌ LỖI KẾT NỐI:", e)
