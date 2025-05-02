"""
Test Human-like Behavior
Script kiểm tra các tính năng mô phỏng hành vi người dùng thật
"""

import sys
import time
import random
import logging
import argparse
from pathlib import Path

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_human_behavior")

# Thêm thư mục cha vào sys.path để import các module
sys.path.append(str(Path(__file__).parent))

from automation.browser_controller import BrowserController
from automation.stealth_utils import StealthConfig


def create_test_profiles():
    """Tạo các profile người dùng khác nhau để test"""
    profiles = {
        "elderly": {
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
        },
        "young_professional": {
            "reading_speed": 300,
            "cursor_accuracy": 0.95,
            "decision_speed": 1.2,
            "attention_span": 40,
            "distraction_chance": 3,
            "hesitation_chance": 5,
            "double_check_chance": 15,
            "age_group": "25-34",
            "tech_savvy": 0.9,
            "patience": 0.7
        },
        "casual_user": {
            "reading_speed": 200,
            "cursor_accuracy": 0.85,
            "decision_speed": 0.9,
            "attention_span": 25,
            "distraction_chance": 6,
            "hesitation_chance": 10,
            "double_check_chance": 20,
            "age_group": "35-44",
            "tech_savvy": 0.7,
            "patience": 0.8
        },
        "impatient_user": {
            "reading_speed": 350,
            "cursor_accuracy": 0.8,
            "decision_speed": 1.5,
            "attention_span": 10,
            "distraction_chance": 2,
            "hesitation_chance": 5,
            "double_check_chance": 5,
            "age_group": "18-24",
            "tech_savvy": 0.85,
            "patience": 0.4
        },
        "precise_user": {
            "reading_speed": 250,
            "cursor_accuracy": 0.98,
            "decision_speed": 0.8,
            "attention_span": 45,
            "distraction_chance": 1,
            "hesitation_chance": 2,
            "double_check_chance": 40,
            "age_group": "35-44",
            "tech_savvy": 0.95,
            "patience": 0.9
        }
    }
    return profiles


def test_click_behavior(browser, url, selector_or_text, is_text=False):
    """Kiểm tra hành vi click"""
    logger.info(f"Kiểm tra hành vi click tại {url}")
    
    # Điều hướng đến URL test
    browser.navigate_to(url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Tự động xử lý popup (nếu có)
    if hasattr(browser, 'overlay_handler') and browser.overlay_handler:
        browser.overlay_handler.close_overlay(close_all=True)
    
    # Mô phỏng người dùng quét trang
    if hasattr(browser, 'human_like_interaction') and browser.human_like_interaction:
        logger.info("Mô phỏng người dùng đang quét trang...")
        browser.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 5))
        
    # Thực hiện click
    if is_text:
        logger.info(f"Tìm và click phần tử có text: {selector_or_text}")
        result = browser.human_like_interaction.find_and_click_visible_element(selector_or_text)
    else:
        logger.info(f"Click phần tử với selector: {selector_or_text}")
        result = browser.human_like_click(selector_or_text)
    
    if result:
        logger.info("Đã click thành công")
    else:
        logger.warning("Không thể click phần tử")
    
    # Đợi để xem kết quả sau khi click
    time.sleep(3)
    
    return result


def test_typing_behavior(browser, url, selector_or_text, text_to_type, is_text=False):
    """Kiểm tra hành vi gõ phím"""
    logger.info(f"Kiểm tra hành vi gõ phím tại {url}")
    
    # Điều hướng đến URL test
    browser.navigate_to(url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Tự động xử lý popup (nếu có)
    if hasattr(browser, 'overlay_handler') and browser.overlay_handler:
        browser.overlay_handler.close_overlay(close_all=True)
    
    # Mô phỏng người dùng quét trang
    if hasattr(browser, 'human_like_interaction') and browser.human_like_interaction:
        logger.info("Mô phỏng người dùng đang quét trang...")
        browser.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 5))
    
    # Tìm và click vào field trước khi nhập
    if is_text:
        logger.info(f"Tìm field có text: {selector_or_text}")
        browser.human_like_interaction.find_and_click_visible_element(selector_or_text)
        time.sleep(1)
        result = browser.human_like_interaction.human_like_type("", text_to_type)
    else:
        logger.info(f"Nhập văn bản vào field với selector: {selector_or_text}")
        result = browser.human_like_type(selector_or_text, text_to_type)
    
    if result:
        logger.info("Đã nhập văn bản thành công")
    else:
        logger.warning("Không thể nhập văn bản")
    
    # Đợi để xem kết quả sau khi nhập
    time.sleep(3)
    
    return result


def test_scroll_behavior(browser, url):
    """Kiểm tra hành vi cuộn trang"""
    logger.info(f"Kiểm tra hành vi cuộn trang tại {url}")
    
    # Điều hướng đến URL test
    browser.navigate_to(url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Tự động xử lý popup (nếu có)
    if hasattr(browser, 'overlay_handler') and browser.overlay_handler:
        browser.overlay_handler.close_overlay(close_all=True)
    
    # Mô phỏng người dùng quét trang
    if hasattr(browser, 'human_like_interaction') and browser.human_like_interaction:
        logger.info("Mô phỏng người dùng đang quét trang trước khi cuộn...")
        browser.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 5))
    
    # Cuộn xuống
    logger.info("Cuộn xuống...")
    browser.human_like_scroll("down")
    time.sleep(2)
    
    # Cuộn xuống với tốc độ chậm
    logger.info("Cuộn xuống với tốc độ chậm...")
    browser.human_like_scroll("down", None, "slow")
    time.sleep(2)
    
    # Đọc/quét nội dung sau cuộn
    if hasattr(browser, 'human_like_interaction') and browser.human_like_interaction:
        logger.info("Mô phỏng người dùng đọc nội dung sau khi cuộn...")
        browser.human_like_interaction.scan_page_like_human(read_time=random.uniform(3, 6))
    
    # Cuộn lên
    logger.info("Cuộn lên...")
    browser.human_like_scroll("up")
    time.sleep(2)
    
    # Cuộn sang phải (nếu trang có scroll ngang)
    try:
        logger.info("Cuộn sang phải...")
        browser.human_like_scroll("right")
        time.sleep(1)
        
        logger.info("Cuộn sang trái...")
        browser.human_like_scroll("left")
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Không thể cuộn ngang: {e}")
    
    logger.info("Hoàn thành kiểm tra hành vi cuộn trang")
    return True


def test_workflow(browser, url):
    """Kiểm tra một workflow hoàn chỉnh"""
    logger.info(f"Kiểm tra workflow tại {url}")
    
    # Điều hướng đến URL test
    browser.navigate_to(url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Tạo workflow
    steps = [
        {"action": "view", "time": random.uniform(2, 4), "description": "Xem trang ban đầu"},
        {"action": "scroll", "direction": "down", "speed": "medium", "description": "Cuộn xuống để xem thêm"},
        {"action": "wait", "time": random.uniform(1, 2), "description": "Đợi một chút sau khi cuộn"},
        {"action": "view", "time": random.uniform(1, 3), "description": "Xem nội dung mới"}
    ]
    
    # Thêm hành động click và type nếu có form trên trang
    try:
        # Kiểm tra xem có form search không
        has_search = browser.page.evaluate("""() => {
            const searchBoxes = document.querySelectorAll('input[type="search"], input[name*="search"], input[placeholder*="search"], input[placeholder*="tìm"]');
            return searchBoxes.length > 0;
        }""")
        
        if has_search:
            logger.info("Tìm thấy form tìm kiếm, thêm bước tìm kiếm vào workflow")
            # Thêm bước tìm kiếm vào workflow
            steps.append({"action": "find_and_click", "text": "search", "description": "Tìm và click vào ô tìm kiếm"})
            steps.append({"action": "type", "value": "human like behavior", "description": "Nhập từ khóa tìm kiếm"})
            steps.append({"action": "wait", "time": random.uniform(0.5, 1), "description": "Đợi một chút sau khi nhập"})
            
            # Kiểm tra xem có nút tìm kiếm không
            has_search_button = browser.page.evaluate("""() => {
                const searchButtons = document.querySelectorAll('button[type="submit"], input[type="submit"], button[name*="search"], button[aria-label*="search"]');
                return searchButtons.length > 0;
            }""")
            
            if has_search_button:
                steps.append({"action": "find_and_click", "text": "search", "description": "Click nút tìm kiếm"})
            else:
                steps.append({"action": "wait", "time": 0.5, "description": "Đợi trước khi nhấn Enter"})
                steps.append({"action": "press_key", "key": "Enter", "description": "Nhấn Enter để tìm kiếm"})
            
            steps.append({"action": "wait", "time": 3, "description": "Đợi kết quả tìm kiếm"})
            steps.append({"action": "view", "time": random.uniform(2, 4), "description": "Xem kết quả tìm kiếm"})
        
        # Kiểm tra xem có form đăng nhập không
        has_login = browser.page.evaluate("""() => {
            const loginForms = document.querySelectorAll('form[action*="login"], form[id*="login"], form[class*="login"]');
            const loginInputs = document.querySelectorAll('input[type="email"], input[name="email"], input[name="username"]');
            return loginForms.length > 0 || loginInputs.length > 0;
        }""")
        
        if has_login:
            logger.info("Tìm thấy form đăng nhập, thêm bước đăng nhập vào workflow")
            # Thêm bước đăng nhập vào workflow
            steps.append({"action": "find_and_click", "text": "email", "description": "Tìm và click vào ô email/username"})
            steps.append({"action": "type", "value": "test@example.com", "description": "Nhập email"})
            steps.append({"action": "wait", "time": random.uniform(0.5, 1), "description": "Đợi một chút sau khi nhập email"})
            
            # Tìm ô mật khẩu
            steps.append({"action": "find_and_click", "text": "password", "description": "Tìm và click vào ô mật khẩu"})
            steps.append({"action": "type", "value": "TestPassword123", "description": "Nhập mật khẩu"})
            steps.append({"action": "wait", "time": random.uniform(0.5, 1), "description": "Đợi một chút sau khi nhập mật khẩu"})
            
            # Tìm nút đăng nhập
            steps.append({"action": "find_and_click", "text": "login", "description": "Click nút đăng nhập"})
            steps.append({"action": "wait", "time": 3, "description": "Đợi sau khi đăng nhập"})
    except Exception as e:
        logger.warning(f"Lỗi khi kiểm tra form trên trang: {e}")
    
    # Thêm bước cuộn và đọc cuối cùng
    steps.append({"action": "scroll", "direction": "down", "speed": "medium", "description": "Cuộn xuống lần cuối"})
    steps.append({"action": "view", "time": random.uniform(2, 3), "description": "Xem nội dung cuối cùng"})
    
    # Thực hiện workflow
    result = browser.execute_human_like_workflow(steps)
    
    if result:
        logger.info("Đã thực hiện workflow thành công")
    else:
        logger.warning("Không thể thực hiện workflow")
    
    return result


def test_form_filling(browser, url, form_data=None):
    """Kiểm tra việc điền form"""
    logger.info(f"Kiểm tra điền form tại {url}")
    
    # Điều hướng đến URL test
    browser.navigate_to(url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Dữ liệu form mặc định
    if form_data is None:
        form_data = {
            "name": "Nguyen Van A",
            "email": "test@example.com",
            "phone": "0912345678",
            "message": "Đây là tin nhắn kiểm tra tính năng mô phỏng người dùng thật khi điền form. Chương trình tự động hóa này sẽ mô phỏng người dùng đang điền form một cách tự nhiên, với tốc độ gõ và lỗi đánh máy như người thật.",
            "subject": "Kiểm tra mô phỏng người dùng"
        }
    
    # Tìm các trường form
    found_fields = browser.page.evaluate("""() => {
        const fields = {
            name: null,
            email: null,
            phone: null,
            message: null,
            subject: null
        };
        
        // Tìm theo nhiều pattern
        // Name field
        fields.name = document.querySelector('input[name="name"], input[id="name"], input[placeholder*="name"], input[placeholder*="tên"]');
        
        // Email field
        fields.email = document.querySelector('input[type="email"], input[name="email"], input[id="email"], input[placeholder*="email"]');
        
        // Phone field
        fields.phone = document.querySelector('input[type="tel"], input[name="phone"], input[id="phone"], input[placeholder*="phone"], input[placeholder*="điện thoại"], input[placeholder*="số điện thoại"]');
        
        // Subject field
        fields.subject = document.querySelector('input[name="subject"], input[id="subject"], input[placeholder*="subject"], input[placeholder*="tiêu đề"], input[placeholder*="chủ đề"]');
        
        // Message field
        fields.message = document.querySelector('textarea, textarea[name="message"], textarea[id="message"], textarea[placeholder*="message"], textarea[placeholder*="tin nhắn"], textarea[placeholder*="nội dung"]');
        
        // Chuyển đổi DOM elements thành selectors
        const result = {};
        for (const [key, element] of Object.entries(fields)) {
            if (element) {
                if (element.id) {
                    result[key] = '#' + element.id;
                } else if (element.name) {
                    result[key] = element.tagName.toLowerCase() + '[name="' + element.name + '"]';
                } else if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(' ').filter(c => c).join('.');
                    result[key] = element.tagName.toLowerCase() + '.' + classes;
                }
            }
        }
        
        return result;
    }""")
    
    # Kiểm tra các trường tìm được
    logger.info(f"Đã tìm thấy các trường: {found_fields}")
    
    # Mô phỏng người dùng quét trang
    if hasattr(browser, 'human_like_interaction') and browser.human_like_interaction:
        logger.info("Mô phỏng người dùng đang quét trang trước khi điền form...")
        browser.human_like_interaction.scan_page_like_human(read_time=random.uniform(2, 4))
    
    # Điền từng trường tìm được
    filled_fields = 0
    for field_name, selector in found_fields.items():
        if selector and field_name in form_data:
            # Nếu là message (textarea), cuộn xuống trước
            if field_name == "message":
                browser.human_like_scroll("down")
                time.sleep(1)
            
            # Điền dữ liệu
            logger.info(f"Điền {field_name} với giá trị: {form_data[field_name]}")
            result = browser.human_like_type(selector, form_data[field_name])
            
            if result:
                filled_fields += 1
                # Đợi một chút sau khi điền xong mỗi trường
                time.sleep(random.uniform(0.3, 0.8))
            else:
                logger.warning(f"Không thể điền vào trường {field_name}")
                
                # Thử phương pháp khác nếu thất bại
                try:
                    browser.human_like_interaction.find_and_click_visible_element(field_name)
                    time.sleep(0.5)
                    browser.page.keyboard.type(form_data[field_name])
                    filled_fields += 1
                    logger.info(f"Đã điền {field_name} bằng phương pháp thay thế")
                except Exception as e:
                    logger.warning(f"Không thể điền {field_name} với cả hai phương pháp: {e}")
    
    # Tìm nút submit
    logger.info("Tìm nút submit form...")
    submit_button = browser.page.evaluate("""() => {
        const submitButtons = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:not([type])',
            'a.submit', 
            'a.btn-submit',
            'button.submit',
            'button.btn-submit',
            'input.submit'
        ];
        
        for (const selector of submitButtons) {
            const button = document.querySelector(selector);
            if (button && button.offsetParent !== null) {
                if (button.id) {
                    return '#' + button.id;
                } else if (button.name) {
                    return button.tagName.toLowerCase() + '[name="' + button.name + '"]';
                } else if (button.className && typeof button.className === 'string') {
                    const classes = button.className.split(' ').filter(c => c).join('.');
                    return button.tagName.toLowerCase() + '.' + classes;
                } else {
                    return selector;
                }
            }
        }
        
        // Thử tìm theo text
        const formButtons = Array.from(document.querySelectorAll('button, input[type="button"], a.btn, a.button'));
        for (const button of formButtons) {
            const text = button.textContent.toLowerCase();
            if (text.includes('submit') || text.includes('send') || text.includes('gửi') || text.includes('submit')) {
                if (button.id) {
                    return '#' + button.id;
                } else if (button.name) {
                    return button.tagName.toLowerCase() + '[name="' + button.name + '"]';
                } else if (button.className && typeof button.className === 'string') {
                    const classes = button.className.split(' ').filter(c => c).join('.');
                    return button.tagName.toLowerCase() + '.' + classes;
                }
            }
        }
        
        return null;
    }""")
    
    # Đợi một chút trước khi submit
    time.sleep(random.uniform(1, 2))
    
    # Submit form
    if submit_button:
        logger.info(f"Tìm thấy nút submit: {submit_button}")
        # Cuộn đến nút submit nếu cần
        browser.human_like_scroll("down")
        time.sleep(0.5)
        
        # Click nút submit
        result = browser.human_like_click(submit_button)
        if result:
            logger.info("Đã submit form thành công")
        else:
            logger.warning("Không thể click nút submit")
    else:
        logger.warning("Không tìm thấy nút submit")
        # Thử tìm bằng text
        try:
            browser.human_like_interaction.find_and_click_visible_element("submit")
            logger.info("Đã tìm và click nút submit bằng text")
        except Exception:
            logger.warning("Không thể tìm nút submit bằng text")
    
    # Đợi một chút sau khi submit
    time.sleep(3)
    
    # Kiểm tra kết quả
    return filled_fields > 0


def test_natural_browsing(browser, start_url, duration=60):
    """Mô phỏng hành vi duyệt web tự nhiên trong thời gian nhất định"""
    logger.info(f"Bắt đầu duyệt web tự nhiên từ {start_url} trong {duration} giây")
    
    # Điều hướng đến URL bắt đầu
    browser.navigate_to(start_url)
    
    # Đợi trang load
    time.sleep(3)
    
    # Thời gian bắt đầu
    start_time = time.time()
    
    # Danh sách URL đã truy cập
    visited_urls = [start_url]
    
    # Vòng lặp duyệt web
    while time.time() - start_time < duration:
        # Đã hết thời gian
        remaining_time = duration - (time.time() - start_time)
        if remaining_time <= 0:
            break
            
        # Tự động xử lý popup nếu có
        if hasattr(browser, 'overlay_handler') and browser.overlay_handler:
            browser.overlay_handler.close_overlay(close_all=True)
        
        # Hành động hiện tại: cuộn, click, xem, điền form
        actions = ["scroll", "view", "click"]
        current_action = random.choice(actions)
        
        logger.info(f"Thực hiện hành động: {current_action} (còn lại {int(remaining_time)}s)")
        
        if current_action == "scroll":
            # Cuộn trang với tốc độ ngẫu nhiên
            speeds = ["slow", "medium", "fast"]
            browser.human_like_scroll("down", None, random.choice(speeds))
            
            # Đôi khi cuộn lên
            if random.random() < 0.3:  # 30% cơ hội
                time.sleep(random.uniform(1, 3))
                browser.human_like_scroll("up")
        
        elif current_action == "view":
            # Xem/đọc trang
            browser.human_like_scan_page(read_time=random.uniform(3, 8))
        
        elif current_action == "click":
            # Tìm các link trên trang
            clickable_elements = browser.page.evaluate("""() => {
                // Tìm tất cả links
                const links = Array.from(document.querySelectorAll('a[href]'))
                    .filter(a => {
                        const href = a.getAttribute('href');
                        return href && 
                               !href.startsWith('javascript:') && 
                               !href.startsWith('#') && 
                               !href.startsWith('tel:') && 
                               !href.startsWith('mailto:') &&
                               a.offsetParent !== null; // Đảm bảo visible
                    })
                    .map(a => ({
                        text: a.textContent.trim(),
                        href: a.getAttribute('href'),
                        selector: a.id ? '#' + a.id : 
                                  (a.className && typeof a.className === 'string' ? 
                                   'a.' + a.className.split(' ').filter(c => c).join('.') : 
                                   null)
                    }));
                
                return links;
            }""")
            
            # Nếu có links, chọn một link ngẫu nhiên để click
            if clickable_elements and len(clickable_elements) > 0:
                # Chọn một link ngẫu nhiên
                random_link = random.choice(clickable_elements)
                logger.info(f"Tìm thấy {len(clickable_elements)} links, thử click: {random_link['text']}")
                
                # Click link
                if random_link['selector']:
                    browser.human_like_click(random_link['selector'])
                else:
                    browser.human_like_interaction.find_and_click_visible_element(random_link['text'])
                
                # Đợi trang mới load
                time.sleep(random.uniform(3, 5))
                
                # Lấy URL mới
                current_url = browser.get_current_url()
                
                # Thêm vào danh sách đã truy cập
                if current_url and current_url not in visited_urls:
                    visited_urls.append(current_url)
                    logger.info(f"Đã điều hướng đến URL mới: {current_url}")
            else:
                logger.info("Không tìm thấy links để click")
                # Nếu không tìm thấy links, chọn hành động khác
                browser.human_like_scroll("down")
        
        # Đợi giữa các hành động
        wait_time = random.uniform(1, 3)
        logger.info(f"Đợi {wait_time:.2f}s trước hành động tiếp theo")
        time.sleep(wait_time)
    
    # Kết thúc
    logger.info(f"Đã hoàn thành duyệt web tự nhiên. Đã truy cập {len(visited_urls)} URLs")
    return visited_urls


def run_tests(target_url, profile_name=None, test_name=None, headless=False):
    """Chạy các bài kiểm tra"""
    profiles = create_test_profiles()
    
    # Nếu chỉ định profile, sử dụng profile đó
    human_profile = None
    if profile_name and profile_name in profiles:
        human_profile = profiles[profile_name]
        logger.info(f"Sử dụng profile: {profile_name}")
    else:
        # Sử dụng profile ngẫu nhiên
        profile_name = random.choice(list(profiles.keys()))
        human_profile = profiles[profile_name]
        logger.info(f"Sử dụng profile ngẫu nhiên: {profile_name}")
    
    # Khởi tạo BrowserController với chế độ human_like_mode
    browser = BrowserController(
        screenshots_dir="data/test_human",
        use_ai_fallback=True,
        browser_type="chromium",
        use_stealth=True,
        debug=True,
        enable_auto_popup_handler=True,
        enable_cursor_icon=True,
        cursor_move_delay=0.2,
        human_like_mode=True,
        human_profile=human_profile
    )
    
    # Khởi động trình duyệt
    browser.start_browser(headless=headless)
    
    try:
        # Áp dụng stealth config
        stealth_config = StealthConfig(level=2)
        stealth_config.apply(browser.page)
        
        # Thiết lập viewport phù hợp
        browser.page.set_viewport_size({"width": 1280, "height": 800})
        
        # Chạy test theo tên nếu được chỉ định
        if test_name:
            if test_name == "click":
                test_click_behavior(browser, target_url, "button", is_text=False)
            elif test_name == "type":
                test_typing_behavior(browser, target_url, "input", "This is a test of human-like typing behavior with random delays and occasional errors.", is_text=False)
            elif test_name == "scroll":
                test_scroll_behavior(browser, target_url)
            elif test_name == "form":
                test_form_filling(browser, target_url)
            elif test_name == "workflow":
                test_workflow(browser, target_url)
            elif test_name == "browsing":
                test_natural_browsing(browser, target_url, duration=120)
            else:
                logger.warning(f"Không tìm thấy test: {test_name}")
        else:
            # Chạy tất cả các test
            logger.info("Chạy tất cả các test")
            
            # Bắt đầu với kiểm tra cuộn trang
            test_scroll_behavior(browser, target_url)
            
            # Điền form nếu URL chứa form
            test_form_filling(browser, target_url)
            
            # Thử workflow hoàn chỉnh
            test_workflow(browser, target_url)
            
            # Duyệt web tự nhiên với thời gian ngắn
            test_natural_browsing(browser, target_url, duration=60)
    
    except Exception as e:
        logger.error(f"Lỗi khi chạy test: {str(e)}")
    
    finally:
        # Đóng trình duyệt
        browser.close_browser()


def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Kiểm tra hành vi mô phỏng người dùng thật")
    parser.add_argument("url", help="URL để test")
    parser.add_argument("--profile", help="Tên profile người dùng (elderly, young_professional, casual_user, impatient_user, precise_user)")
    parser.add_argument("--test", help="Tên test (click, type, scroll, form, workflow, browsing)")
    parser.add_argument("--headless", action="store_true", help="Chạy ở chế độ headless")
    
    args = parser.parse_args()
    
    run_tests(args.url, args.profile, args.test, args.headless)


if __name__ == "__main__":
    main()
