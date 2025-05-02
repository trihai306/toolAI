# Hướng dẫn khắc phục lỗi OpenAI API

## Mô tả vấn đề

Dự án đang gặp lỗi khi kết nối đến OpenAI API:

```
Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-proj-*********. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'param': None, 'code': 'invalid_api_key'}}
```

## Nguyên nhân

Sau khi phân tích, chúng tôi xác định được các nguyên nhân:

1. **Xung đột định dạng khóa API**: Dự án đang sử dụng khóa API mới định dạng `sk-proj-...` nhưng thư viện OpenAI phiên bản cũ (v0.28.1) không hỗ trợ định dạng này và chỉ chấp nhận khóa với định dạng cũ `sk-...`.

2. **Phương thức khởi tạo OpenAI client không phù hợp**: Dự án đang sử dụng `openai.api_key = ...` thay vì phương thức mới `client = OpenAI(api_key=...)`.

3. **API mới vs thư viện cũ**: Khóa `sk-proj-...` chỉ hoạt động với thư viện OpenAI phiên bản mới (v1.x+), nhưng dự án đang sử dụng phiên bản cũ (v0.28.1).

## Giải pháp

Có ba cách để giải quyết vấn đề này:

### Giải pháp 1: Cập nhật thư viện OpenAI (Khuyến nghị)

```bash
pip install openai>=1.76.0 --upgrade
```

Sau đó sửa code để sử dụng client mới:

```python
# Thay vì:
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")
response = openai.chat.completions.create(...)

# Sử dụng:
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(...)
```

### Giải pháp 2: Tạo khóa API định dạng cũ

1. Đăng nhập vào tài khoản OpenAI: https://platform.openai.com/
2. Truy cập API Keys: https://platform.openai.com/api-keys
3. Tạo khóa API mới (định dạng cũ 'sk-...')
4. Thay thế OPENAI_API_KEY trong file .env với khóa mới

### Giải pháp 3: Chuyển đổi định dạng khóa API trong code

```python
if api_key.startswith("sk-proj-"):
    api_key = "sk-" + api_key[len("sk-proj-"):]
openai.api_key = api_key
```

**Lưu ý**: Giải pháp 3 không phải là giải pháp chính thức và có thể không hoạt động trong tương lai.

## Các file cần sửa

Các file chính trong dự án cần được cập nhật:

1. `src/ai/page_observer/html_analyzer.py`
2. `src/ai/enhanced_element_finder.py`
3. `src/ai/ai_element_finder.py`

## Cách xác nhận sửa lỗi

Chạy script `test_openai_new.py` để kiểm tra kết nối:

```bash
python test_openai_new.py
```

Nếu kết nối REST API và client v1.x đều thành công, việc sửa lỗi đã hoàn thành.

## Kết luận

Vấn đề không phải ở cấu hình môi trường hay khóa API không hợp lệ, mà là sự không tương thích giữa định dạng khóa API mới và thư viện OpenAI phiên bản cũ. Giải pháp tốt nhất là cập nhật lên thư viện mới nhất để tận dụng tất cả tính năng mới của OpenAI API. 