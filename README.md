# Browser Automation Manager

Công cụ tự động hóa trình duyệt với giao diện người dùng đồ họa tích hợp.

## Tính năng

- Điều khiển trình duyệt tự động thông qua lệnh tiếng Việt tự nhiên
- Giao diện người dùng trực quan và thân thiện
- Hỗ trợ nhiều trình duyệt: Chromium, Firefox, WebKit
- Chụp ảnh màn hình
- Lưu trữ lịch sử lệnh

## Cài đặt

1. Clone repository:
   ```
   git clone <repository-url>
   cd toolAI
   ```

2. Cài đặt các dependencies:
   ```
   python main.py --install
   ```

   Hoặc cài đặt thủ công:
   ```
   pip install -r requirements.txt
   pip install flask==2.0.1 werkzeug==2.0.1 pywebview==4.2.2
   pip install playwright
   playwright install
   ```

## Sử dụng

### Khởi động với GUI

```
python main.py
```

### Khởi động chế độ dòng lệnh (CLI)

```
python main.py --cli
```

### Cài đặt dependencies

```
python main.py --install
```

## Cấu trúc dự án

```
toolAI/
├── main.py               # Điểm vào chính
├── requirements.txt      # Các thư viện cần thiết
├── src/
│   ├── main.py           # Mô-đun chính
│   ├── gui_integration.py  # Tích hợp GUI
│   ├── static/           # Tài nguyên tĩnh cho giao diện
│   │   ├── css/
│   │   └── js/
│   ├── templates/        # Các template HTML
│   └── ...
└── ...
```

## Sử dụng GUI

1. Khởi động ứng dụng: `python main.py`
2. Nhấp "Khởi động trình duyệt" để bắt đầu
3. Nhập lệnh vào ô văn bản (ví dụ: "Mở Google và tìm kiếm Python")
4. Nhấp "Chạy lệnh" để thực thi

## Giải quyết vấn đề

Nếu bạn gặp lỗi:

1. Kiểm tra các thư viện đã được cài đặt đầy đủ: `python main.py --install`
2. Kiểm tra trình duyệt được cài đặt: `playwright install`
3. Xem logs trong thư mục `logs` hoặc file `browser_automation.log`

## Giấy phép

Phần mềm này được phân phối theo giấy phép MIT.