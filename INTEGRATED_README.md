# Hướng dẫn sử dụng Browser Automation Tool (Phiên bản tích hợp)

Ứng dụng này kết hợp công cụ tự động hóa trình duyệt với giao diện quản lý dễ sử dụng, cho phép bạn điều khiển và theo dõi các tác vụ tự động hóa thông qua giao diện web hiện đại.

## Cài đặt

1. **Cài đặt các dependencies**:

```bash
python run_integrated.py --install
```

Lệnh này sẽ cài đặt tất cả các thư viện cần thiết bao gồm:
- Thư viện cơ bản từ `requirements.txt`
- Flask và Werkzeug (phiên bản tương thích)
- PyWebView
- Playwright và các trình duyệt cần thiết

2. **Khởi động ứng dụng**:

```bash
python run_integrated.py
```

Hoặc sử dụng file batch:

```bash
start_integrated.bat
```

## Các chế độ hoạt động

### 1. Chế độ GUI (mặc định)

```bash
python run_integrated.py
```

Chế độ này kết hợp hai phần:
- **Backend**: Công cụ tự động hóa trình duyệt từ thư mục `src`
- **Frontend**: Giao diện web hiện đại sử dụng Flask và PyWebView

### 2. Chế độ CLI (Command Line)

```bash
python run_integrated.py --cli
```

Chế độ này chạy ứng dụng gốc từ thư mục `src` mà không có giao diện web.

## Sử dụng giao diện GUI

### Khởi động trình duyệt

1. Nhấp vào nút "Khởi động trình duyệt"
2. Chọn loại trình duyệt (Chromium, Firefox, hoặc WebKit)
3. Tuỳ chọn chọn chế độ headless (không hiển thị giao diện)
4. Nhấp "Lưu" để khởi động trình duyệt

### Thực thi lệnh

1. Nhập lệnh bằng ngôn ngữ tự nhiên vào ô nhập lệnh
   - Ví dụ: "Mở Google và tìm kiếm về Playwright"
   - Ví dụ: "Đăng nhập vào Facebook với tài khoản example@example.com"
2. Nhấp "Chạy lệnh" hoặc nhấn Ctrl+Enter
3. Xem kết quả thực thi trong khung bên phải

### Chụp ảnh màn hình

1. Nhấp vào nút "Chụp màn hình" để chụp ảnh trạng thái hiện tại của trình duyệt
2. Ảnh sẽ được hiển thị trong khung ảnh bên dưới

### Xem lịch sử lệnh

- Các lệnh đã thực thi sẽ được lưu trong khung "Lịch sử lệnh"
- Nhấp vào một lệnh trong lịch sử để sử dụng lại

## Xử lý lỗi

### Lỗi khi khởi động trình duyệt

Nếu gặp lỗi "Failed to start browser":

1. **Kiểm tra cài đặt Playwright**:
   ```bash
   python -m playwright install
   ```

2. **Truy cập trang debug**:
   - Từ ứng dụng chính, truy cập `/debug` (ví dụ: http://127.0.0.1:5000/debug)
   - Hoặc nhấp vào nút "Chế độ gỡ lỗi" trong trang kiểm tra

3. **Kiểm tra trang trạng thái**:
   - Truy cập `/check` (ví dụ: http://127.0.0.1:5000/check)
   - Trang này sẽ tự động kiểm tra cài đặt và hiển thị lỗi cụ thể

### Lỗi Flask hoặc PyWebView

Nếu giao diện web không hiển thị:

1. **Sử dụng chế độ CLI**:
   ```bash
   python run_integrated.py --cli
   ```

2. **Cài đặt lại dependencies**:
   ```bash
   python run_integrated.py --install
   ```

## Cấu trúc tích hợp

Ứng dụng tích hợp kết nối hai phần chính:

1. **Backend**: `src/main.py` và các module liên quan
   - BrowserController: Điều khiển trình duyệt
   - WorkflowManager: Quản lý quy trình tự động hóa
   - AIAgent: Xử lý lệnh ngôn ngữ tự nhiên

2. **Frontend**: Giao diện quản lý (Flask + PyWebView)
   - Flask: Cung cấp API và hiển thị trang web
   - PyWebView: Tạo cửa sổ desktop đóng gói
   - Tailwind CSS: Giao diện hiện đại và responsive

Module `src/gui_integration.py` đóng vai trò kết nối giữa hai phần này, cung cấp điểm truy cập chung cho cả backend và frontend.

## Xử lý vấn đề về phiên bản

Nếu gặp lỗi về phiên bản Flask hoặc Werkzeug:

```bash
python -m pip install flask==2.0.1 werkzeug==2.0.1
```

Hoặc sử dụng lệnh cài đặt tích hợp:

```bash
python run_integrated.py --install
```
