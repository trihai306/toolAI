# Hướng dẫn sử dụng tính năng mô phỏng người dùng thật

Tài liệu này mô tả cách sử dụng các tính năng mô phỏng hành vi người dùng thật trong hệ thống tự động hóa.

## Giới thiệu

Module mô phỏng người dùng thật giúp các thao tác tự động trên trình duyệt trở nên tự nhiên hơn, khó phát hiện hơn và tránh bị chặn bởi các hệ thống chống bot. Các hành vi được mô phỏng bao gồm:

- Di chuyển chuột theo đường cong tự nhiên
- Tốc độ gõ phím và lỗi đánh máy như người thật
- Hành vi cuộn trang tự nhiên, có dừng lại để đọc
- Thời gian phản ứng và dừng nghỉ tự nhiên
- Thao tác quét/đọc trang trước khi tương tác

## Các tính năng chính

### 1. Di chuyển chuột như người thật

Thay vì di chuyển chuột theo đường thẳng, module sẽ tạo đường cong Bezier tự nhiên, thêm độ trễ và nghỉ ngẫu nhiên, tạo hiệu ứng của một người đang di chuyển chuột.

```python
# Sử dụng trong BrowserController
browser.human_like_click("css_selector") 

# Sử dụng trong HumanLikeInteraction
browser.human_like_interaction.human_like_move_mouse(x, y, click=True)
```

### 2. Nhập liệu như người thật

Nhập văn bản với tốc độ không đều, đôi khi dừng giữa chừng, thêm lỗi đánh máy và tự sửa lỗi, tạo độ trễ khác nhau giữa các ký tự.

```python
# Sử dụng trong BrowserController
browser.human_like_type("css_selector", "text to type")

# Sử dụng trong HumanLikeInteraction
browser.human_like_interaction.human_like_type("css_selector", "text to type")
```

### 3. Cuộn trang tự nhiên

Cuộn trang với tốc độ và độ mượt khác nhau, đôi khi dừng lại để "đọc", đôi khi cuộn ngược lại một chút để tìm thông tin.

```python
# Sử dụng trong BrowserController
browser.human_like_scroll("down", distance=None, speed="medium")

# Hướng cuộn: "up", "down", "left", "right"
# Tốc độ: "slow", "medium", "fast"
```

### 4. Mô phỏng người dùng đọc/quét trang

Mô phỏng cử chỉ mắt và chuột của người dùng đang đọc hoặc quét trang web.

```python
# Sử dụng trong BrowserController
browser.human_like_scan_page(focus_area=None, read_time=5.0)

# focus_area: Khu vực tập trung (dict với x, y, width, height)
# read_time: Thời gian đọc tính bằng giây
```

### 5. Thực hiện workflow hoàn chỉnh

Thực hiện một chuỗi các thao tác với độ trễ và hành vi tự nhiên giữa các bước.

```python
# Tạo danh sách các bước
steps = [
    {"action": "view", "time": 3.0, "description": "Xem trang ban đầu"},
    {"action": "scroll", "direction": "down", "speed": "medium"},
    {"action": "find_and_click", "text": "Đăng nhập", "description": "Click nút đăng nhập"},
    {"action": "type", "selector": "#username", "value": "test@example.com", "description": "Nhập username"},
    {"action": "type", "selector": "#password", "value": "password123", "description": "Nhập password"},
    {"action": "click", "selector": "button[type='submit']", "description": "Click nút submit"},
    {"action": "wait", "time": 2.0, "description": "Đợi sau khi đăng nhập"}
]

# Thực hiện workflow
browser.execute_human_like_workflow(steps)
```

## Cài đặt profile người dùng

Bạn có thể tùy chỉnh profile của người dùng để tạo các hành vi khác nhau:

```python
# Cài đặt profile cho người dùng lớn tuổi, ít thành thạo công nghệ
elderly_profile = {
    "reading_speed": 120,  # Từ/phút
    "cursor_accuracy": 0.75,  # Độ chính xác khi di chuột
    "decision_speed": 0.6,  # Hệ số tốc độ quyết định
    "attention_span": 15,  # Thời gian chú ý liên tục (giây)
    "distraction_chance": 8,  # Xác suất bị phân tâm (%)
    "hesitation_chance": 20,  # Xác suất ngập ngừng (%)
    "double_check_chance": 30,  # Xác suất kiểm tra lại (%)
    "age_group": "55+",
    "tech_savvy": 0.5,  # Mức độ thành thạo công nghệ
    "patience": 0.8  # Mức độ kiên nhẫn
}

# Cài đặt profile
browser.set_human_profile(elderly_profile)

# Hoặc khi khởi tạo BrowserController
browser = BrowserController(
    human_like_mode=True,
    human_profile=elderly_profile
)
```

## Bật/tắt chế độ người dùng thật

```python
# Bật chế độ mô phỏng người dùng thật
browser.toggle_human_like_mode(True)

# Tắt chế độ mô phỏng người dùng thật
browser.toggle_human_like_mode(False)

# Đảo trạng thái hiện tại
browser.toggle_human_like_mode()
```

## Kiểm tra tính năng mô phỏng

Sử dụng script `tests/test_human_behavior.py` để kiểm tra các tính năng mô phỏng:

```bash
# Chạy tất cả các test
python tests/test_human_behavior.py https://example.com

# Sử dụng profile cụ thể
python tests/test_human_behavior.py https://example.com --profile elderly

# Chạy test cụ thể
python tests/test_human_behavior.py https://example.com --test click
python tests/test_human_behavior.py https://example.com --test type
python tests/test_human_behavior.py https://example.com --test scroll
python tests/test_human_behavior.py https://example.com --test form
python tests/test_human_behavior.py https://example.com --test workflow
python tests/test_human_behavior.py https://example.com --test browsing
```

## Các profile người dùng có sẵn

Script `tests/test_human_behavior.py` cung cấp các profile người dùng có sẵn:

1. **elderly** - Người dùng lớn tuổi, ít thành thạo công nghệ
2. **young_professional** - Người dùng trẻ, chuyên nghiệp, thành thạo công nghệ
3. **casual_user** - Người dùng thông thường
4. **impatient_user** - Người dùng thiếu kiên nhẫn, thao tác nhanh
5. **precise_user** - Người dùng cẩn thận, chính xác

## Tích hợp với auto_handle_page

Tính năng mô phỏng người dùng thật đã được tích hợp với phương thức `auto_handle_page`:

```python
# Sử dụng chế độ mô phỏng người dùng thật
browser.auto_handle_page(goal="đăng nhập", credentials={"username": "user", "password": "pass"}, use_human_like=True)

# Không sử dụng chế độ mô phỏng người dùng thật
browser.auto_handle_page(goal="đăng nhập", credentials={"username": "user", "password": "pass"}, use_human_like=False)
```

## Lưu ý quan trọng

1. Chế độ mô phỏng người dùng thật sẽ làm thao tác chậm hơn để đảm bảo tính tự nhiên
2. Các thao tác có thể không hoàn hảo 100% tùy thuộc vào độ phức tạp của trang web
3. Nên kết hợp với các tính năng stealth khác để tối ưu hiệu quả chống bot
4. Điều chỉnh các thông số trong `user_profile` để phù hợp với từng trang web cụ thể

## Xử lý lỗi

Khi sử dụng chế độ mô phỏng người dùng thật, nếu gặp lỗi, hệ thống sẽ tự động fallback về các phương thức thông thường. Bạn có thể kiểm tra log để xem chi tiết:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Tối ưu hóa

- Tăng/giảm `cursor_accuracy` để điều chỉnh độ chính xác của chuột
- Điều chỉnh `typing_speed_min` và `typing_speed_max` để thay đổi tốc độ gõ
- Thay đổi `action_delay_min` và `action_delay_max` để điều chỉnh thời gian giữa các thao tác
- Các thông số này có thể được điều chỉnh trong file `human_like_utils.py`
