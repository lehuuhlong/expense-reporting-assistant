# Trợ Lý Báo Cáo Chi Phí

Một chatbot AI thông minh để hỗ trợ nhân viên Việt Nam trong việc báo cáo chi phí, trả lời các câu hỏi về chính sách và tính toán hoàn tiền một cách tự động. Hỗ trợ cả giao diện dòng lệnh và web, với tính năng chuyển văn bản thành giọng nói.

## 🚀 Tính năng chính

- 🤖 **Hướng dẫn chính sách AI**: Trả lời câu hỏi về chính sách chi phí công ty bằng tiếng Việt
- 💰 **Tính toán thông minh**: Tự động tính toán hoàn tiền theo đơn vị VNĐ
- 📋 **Quản lý hội thoại**: Duy trì ngữ cảnh qua nhiều lượt đối thoại
- 🔧 **Function Calling**: Gọi hàm động cho các truy vấn phức tạp
- 🧪 **Framework kiểm thử**: Hệ thống kiểm thử toàn diện
- 🌐 **Giao diện web**: Ứng dụng web Flask với UI hiện đại
- 🔊 **Text-to-Speech**: Chuyển đổi phản hồi của trợ lý thành giọng nói tiếng Việt

## 📦 Cài đặt

1. **Clone repository**:

```bash
git clone <repository-url>
cd workshop2
```

2. **Cài đặt dependencies**:

```bash
pip install -r requirements.txt

python setup_db.py
```

3. **Thiết lập environment variables**:
   Tạo file `.env` trong thư mục gốc:

```env
OPENAI_BASE_URL=OPENAI_BASE_URL
OPENAI_API_KEY=your_api_key_here
OPENAI_DEPLOYMENT=OPENAI_DEPLOYMENT
```

## 🎮 Cách sử dụng

### 1. Chạy ứng dụng web (Khuyến nghị)

```bash
python web_app.py
```

Sau đó mở trình duyệt và truy cập: http://localhost:5000

### 2. Chạy chat tương tác

```bash
python cli.py
```

### 3. Chạy demo

```bash
python demo.py
```

### 4. Chạy test

```bash
python -c "from tester import ExpenseAssistantTester; from expense_assistant import ExpenseAssistant, create_client; tester = ExpenseAssistantTester(ExpenseAssistant(create_client())); tester.run_test_suite()"
```

## 📁 Cấu trúc dự án

```
workshop2/
├── expense_assistant.py    # Core chatbot class
├── functions.py           # Helper functions và data
├── cli.py                 # Command-line interface
├── tester.py             # Testing framework
├── demo.py               # Demo functions
├── web_app.py            # Flask web application
├── text_to_speech.py     # Text-to-speech functionality
├── templates/
│   └── index.html        # Web UI template
├── static/
│   ├── css/
│   │   └── style.css     # Web styling
│   └── js/
│       └── app.js        # Frontend JavaScript
├── audio_chats/          # Directory for generated audio files
├── requirements.txt      # Dependencies
├── .env                 # Environment variables
└── README.md            # Documentation
```

## 🔧 Modules

### `expense_assistant.py`

- **ExpenseAssistant**: Class chính quản lý chatbot với hỗ trợ tiếng Việt
- **create_client()**: Tạo OpenAI client

### `functions.py`

- **calculate_reimbursement()**: Tính toán hoàn tiền theo VNĐ
- **validate_expense()**: Kiểm tra tính hợp lệ theo chính sách Việt Nam
- **search_policies()**: Tìm kiếm chính sách bằng tiếng Việt
- **format_expense_summary()**: Định dạng tóm tắt chi phí

### `cli.py`

- **run_interactive_chat()**: Chat tương tác tiếng Việt
- **quick_test()**: Test nhanh
- **quick_demo()**: Demo nhanh

### `tester.py`

- **ExpenseAssistantTester**: Framework kiểm thử toàn diện

### `demo.py`

- **run_demo()**: Demo đầy đủ tính năng
- **demonstrate_conversation_flow()**: Demo hội thoại

### `web_app.py`

- **Flask Application**: Ứng dụng web với REST API
- **Session Management**: Quản lý phiên chat
- **Vietnamese UI**: Giao diện web tiếng Việt

### `text_to_speech.py`

- **text_to_speech()**: Chuyển đổi văn bản thành giọng nói tiếng Việt và lưu file âm thanh.

### `templates/index.html`

- **Web Interface**: Giao diện chat hiện đại
- **Bootstrap 5**: Responsive design
- **Vietnamese Localization**: Hoàn toàn tiếng Việt

### `static/js/app.js`

- **Frontend Logic**: JavaScript cho chat interface
- **Real-time Chat**: Tương tác thời gian thực
- **Session Management**: Quản lý phiên từ frontend
- **Audio Playback**: Xử lý phát lại âm thanh

## 💡 Ví dụ sử dụng

### Trong Python script:

```python
from expense_assistant import ExpenseAssistant, create_client

# Khởi tạo
client = create_client()
assistant = ExpenseAssistant(client)

# Sử dụng
response = assistant.get_response("Giới hạn chi phí ăn uống là bao nhiều?")
print(response['content'])
```

### Trong interactive mode:

```
👤 Bạn: Giới hạn chi phí ăn uống là bao nhiều?
🤖 Trợ lý: 📋 Giới hạn chi phí ăn uống của công ty chúng ta là 1.000.000 VNĐ/ngày cho công tác trong nước và 1.500.000 VNĐ/ngày cho công tác quốc tế...

👤 Bạn: Tính hoàn tiền cho: ăn trưa 900.000 VNĐ, taxi 600.000 VNĐ
🤖 Trợ lý: 💰 Tôi đã tính toán hoàn tiền của bạn...
```

### Trong web interface:

1. Truy cập: http://localhost:5000
2. Chọn câu hỏi mẫu hoặc gõ trực tiếp
3. Nhận phản hồi thời gian thực với function calling details
4. Nhấp vào biểu tượng loa để nghe phản hồi của trợ lý

## 🧪 Testing

Chạy test suite đầy đủ:

```python
from tester import ExpenseAssistantTester
from expense_assistant import ExpenseAssistant, create_client

client = create_client()
assistant = ExpenseAssistant(client)
tester = ExpenseAssistantTester(assistant)

# Chạy tất cả test
results = tester.run_test_suite()
```

## 📊 Chính sách mẫu (Dành cho Việt Nam)

- **Hóa đơn**: Yêu cầu hóa đơn cho chi phí trên 500.000 VNĐ
- **Ăn uống**: 1.000.000 VNĐ/ngày trong nước, 1.500.000 VNĐ/ngày quốc tế
- **Đi lại**: Cần phê duyệt trước, taxi/Grab được hoàn đầy đủ
- **Văn phòng phẩm**: 2.000.000 VNĐ/tháng mỗi nhân viên

## 🔮 Tính năng tương lai

- [ ] OCR cho hóa đơn điện tử
- [ ] Tích hợp email/Slack
- [ ] Tạo PDF báo cáo tự động
- [ ] Phân loại chi phí bằng ML
- [ ] Phát hiện gian lận
- [ ] Dashboard analytics real-time
- [ ] Mobile app iOS/Android
- [ ] Tích hợp với hệ thống ERP

## 🏆 Workshop Deliverables

✅ **Hoàn thành tất cả yêu cầu**:

1. Real-world problem & mock data schema ✅
2. Conversation flows & prompt templates ✅
3. OpenAI SDK implementation với function calling ✅
4. Interactive interface (CLI + Web) ✅
5. Testing & debugging framework ✅
6. Demo & presentation ready ✅
7. **Bonus**: Vietnamese localization ✅
8. **Bonus**: Web application với modern UI ✅
9. **Bonus**: Text-to-Speech integration ✅

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 🌐 Web Application

### Tính năng Web Interface:

- **Modern UI**: Bootstrap 5 với thiết kế responsive
- **Real-time Chat**: Chat thời gian thực với typing indicators
- **Session Management**: Quản lý phiên chat độc lập
- **Function Calling Display**: Hiển thị chi tiết các chức năng được gọi
- **Vietnamese UI**: Giao diện hoàn toàn tiếng Việt
- **Sample Questions**: Câu hỏi mẫu để bắt đầu nhanh
- **Text-to-Speech**: Nghe phản hồi của trợ lý

### API Endpoints:

- `GET /` - Trang chủ web interface
- `POST /api/start_session` - Tạo phiên chat mới
- `POST /api/chat` - Gửi tin nhắn chat
- `POST /api/text-to-speech` - Chuyển văn bản thành giọng nói
- `GET /audio/<filename>` - Phục vụ file âm thanh
- `GET /api/sample_questions` - Lấy câu hỏi mẫu
- `POST /api/clear_session` - Xóa phiên chat

## 📄 License

MIT License - xem file LICENSE để biết chi tiết.

## 🆘 Hỗ trợ

Nếu gặp vấn đề:

1. Kiểm tra file `.env`
2. Đảm bảo dependencies đã cài đặt (`pip install -r requirements.txt`)
3. Kiểm tra API key hợp lệ
4. Chạy `python web_app.py` để kiểm tra hệ thống
5. Với web app: Đảm bảo Flask và Flask-CORS đã được cài đặt
