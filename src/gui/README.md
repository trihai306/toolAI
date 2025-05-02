# Browser Automation Manager

Giao diện quản lý trực quan cho công cụ tự động hóa trình duyệt web. Sử dụng Flask + PyWebView + Tailwind CSS để tạo một ứng dụng desktop hiện đại và dễ sử dụng.

## Tính năng

- Giao diện người dùng trực quan với Tailwind CSS
- Tự động hóa trình duyệt web thông qua giao diện đồ họa
- Chạy các lệnh nhập bằng ngôn ngữ tự nhiên
- Xem lịch sử lệnh và kết quả thực thi
- Chụp ảnh màn hình trình duyệt
- Hỗ trợ nhiều trình duyệt (Chromium, Firefox, WebKit)

## Cài đặt

1. Đảm bảo đã cài đặt Python 3.8+ và pip
2. Cài đặt các dependencies:

```bash
pip install -r requirements.txt
```

3. Cài đặt trình duyệt cho Playwright:

```bash
playwright install
```

## Sử dụng

Để khởi động ứng dụng:

```bash
python main.py
```

## Hướng dẫn sử dụng

1. Khởi động trình duyệt bằng nút "Khởi động trình duyệt"
2. Nhập lệnh tự động hóa vào ô nhập lệnh
3. Nhấn "Chạy lệnh" hoặc Ctrl+Enter để thực thi
4. Xem kết quả thực thi ở khung bên phải
5. Sử dụng nút "Chụp màn hình" để chụp ảnh trạng thái hiện tại của trình duyệt

### Ví dụ lệnh

- "Mở Google và tìm kiếm OpenAI"
- "Đăng nhập vào Facebook với tài khoản example@example.com và mật khẩu example123"
- "Truy cập youtube.com và tìm kiếm video về AI"

## Cấu trúc dự án

```
gui/
├── app.py             # Ứng dụng Flask chính
├── main.py            # Điểm khởi chạy chính sử dụng PyWebView
├── requirements.txt   # Các dependencies
├── static/            # Tài nguyên tĩnh
│   ├── css/           # CSS và Tailwind
│   └── js/            # JavaScript
└── templates/         # Templates HTML
    └── index.html     # Trang chính
```

## Công nghệ sử dụng

- **Flask**: Web framework backend
- **PyWebView**: Wrapper để tạo ứng dụng desktop
- **Tailwind CSS**: Framework CSS cho giao diện người dùng
- **Playwright**: Tự động hóa trình duyệt
