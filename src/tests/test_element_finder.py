"""
Test Element Finder
Kiểm tra và phát hiện các vấn đề với việc tìm kiếm element
"""

import os
import sys
import logging
import time
from pathlib import Path

# Thêm thư mục gốc vào sys.path
current_dir = Path(__file__).parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

from automation import BrowserController
from ai.enhanced_element_finder import EnhancedElementFinder
from ai.ai_element_finder import AIElementFinder
from ai.page_observer import PageObserverSafe, HTMLAnalyzer

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("element_finder_test.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ElementFinderTest")

def test_basic_selectors(browser):
    """Kiểm tra các selector cơ bản"""
    logger.info("=== KIỂM TRA SELECTOR CƠ BẢN ===")
    
    # 1. CSS Selector
    css_result = browser.wait_for_selector("body", timeout=5000)
    logger.info(f"CSS Selector 'body': {'PASS' if css_result else 'FAIL'}")
    
    # 2. XPath
    xpath_result = browser.wait_for_selector("xpath=//body", timeout=5000)
    logger.info(f"XPath '//body': {'PASS' if xpath_result else 'FAIL'}")
    
    # 3. ID
    browser.page.evaluate("""() => {
        const div = document.createElement('div');
        div.id = 'test-element';
        div.textContent = 'Test Element';
        document.body.appendChild(div);
    }""")
    id_result = browser.wait_for_selector("#test-element", timeout=5000)
    logger.info(f"ID Selector '#test-element': {'PASS' if id_result else 'FAIL'}")
    
    # 4. Class
    browser.page.evaluate("""() => {
        const div = document.createElement('div');
        div.className = 'test-class';
        div.textContent = 'Test Class Element';
        document.body.appendChild(div);
    }""")
    class_result = browser.wait_for_selector(".test-class", timeout=5000)
    logger.info(f"Class Selector '.test-class': {'PASS' if class_result else 'FAIL'}")
    
    # 5. Attribute
    browser.page.evaluate("""() => {
        const div = document.createElement('div');
        div.setAttribute('data-test', 'test-value');
        div.textContent = 'Test Attribute Element';
        document.body.appendChild(div);
    }""")
    attr_result = browser.wait_for_selector("[data-test='test-value']", timeout=5000)
    logger.info(f"Attribute Selector '[data-test='test-value']': {'PASS' if attr_result else 'FAIL'}")

def test_complex_selectors(browser):
    """Kiểm tra các selector phức tạp"""
    logger.info("=== KIỂM TRA SELECTOR PHỨC TẠP ===")
    
    # Tạo cấu trúc DOM phức tạp
    browser.page.evaluate("""() => {
        // Tạo một cấu trúc DOM phức tạp
        const container = document.createElement('div');
        container.id = 'complex-container';
        
        // Tạo một form
        const form = document.createElement('form');
        form.id = 'test-form';
        
        // Tạo các input
        const input1 = document.createElement('input');
        input1.type = 'text';
        input1.name = 'username';
        input1.placeholder = 'Nhập tên người dùng';
        
        const input2 = document.createElement('input');
        input2.type = 'password';
        input2.name = 'password';
        input2.placeholder = 'Nhập mật khẩu';
        
        // Tạo button
        const button = document.createElement('button');
        button.type = 'submit';
        button.textContent = 'Đăng nhập';
        
        // Tạo thông báo lỗi
        const errorMsg = document.createElement('div');
        errorMsg.className = 'error-message';
        errorMsg.style.display = 'none';
        errorMsg.textContent = 'Thông tin đăng nhập không chính xác';
        
        // Thêm các phần tử vào form
        form.appendChild(input1);
        form.appendChild(input2);
        form.appendChild(button);
        form.appendChild(errorMsg);
        
        // Thêm form vào container
        container.appendChild(form);
        
        // Thêm container vào body
        document.body.appendChild(container);
    }""")
    
    # 1. Selector con
    child_result = browser.wait_for_selector("#complex-container > #test-form", timeout=5000)
    logger.info(f"Child Selector '#complex-container > #test-form': {'PASS' if child_result else 'FAIL'}")
    
    # 2. Selector hậu duệ
    descendant_result = browser.wait_for_selector("#complex-container input[name='username']", timeout=5000)
    logger.info(f"Descendant Selector '#complex-container input[name='username']': {'PASS' if descendant_result else 'FAIL'}")
    
    # 3. XPath phức tạp
    xpath_complex_result = browser.wait_for_selector("xpath=//div[@id='complex-container']//input[@placeholder='Nhập mật khẩu']", timeout=5000)
    logger.info(f"Complex XPath '//div[@id='complex-container']//input[@placeholder='Nhập mật khẩu']': {'PASS' if xpath_complex_result else 'FAIL'}")
    
    # 4. Selector anh em
    browser.page.evaluate("""() => {
        const container = document.querySelector('#complex-container');
        const sibling1 = document.createElement('div');
        sibling1.className = 'sibling first';
        sibling1.textContent = 'Sibling 1';
        
        const sibling2 = document.createElement('div');
        sibling2.className = 'sibling second';
        sibling2.textContent = 'Sibling 2';
        
        container.appendChild(sibling1);
        container.appendChild(sibling2);
    }""")
    sibling_result = browser.wait_for_selector(".sibling.first + .sibling.second", timeout=5000)
    logger.info(f"Sibling Selector '.sibling.first + .sibling.second': {'PASS' if sibling_result else 'FAIL'}")

def test_enhanced_element_finder(browser):
    """Kiểm tra EnhancedElementFinder"""
    logger.info("=== KIỂM TRA ENHANCED ELEMENT FINDER ===")
    
    try:
        # Khởi tạo EnhancedElementFinder
        finder = EnhancedElementFinder(browser, use_page_observer=True, debug=True)
        
        # Tạo các phần tử với text để tìm kiếm
        browser.page.evaluate("""() => {
            // Xóa container cũ nếu có
            const oldContainer = document.querySelector('#enhanced-test-container');
            if (oldContainer) oldContainer.remove();
            
            // Tạo container mới
            const container = document.createElement('div');
            container.id = 'enhanced-test-container';
            
            // Button đăng nhập
            const loginButton = document.createElement('button');
            loginButton.id = 'login-btn';
            loginButton.textContent = 'Đăng nhập';
            
            // Button đăng ký
            const registerButton = document.createElement('button');
            registerButton.id = 'register-btn';
            registerButton.textContent = 'Đăng ký tài khoản';
            
            // Input tìm kiếm
            const searchInput = document.createElement('input');
            searchInput.type = 'text';
            searchInput.placeholder = 'Tìm kiếm sản phẩm';
            
            // Menu dropdown
            const dropdown = document.createElement('div');
            dropdown.className = 'dropdown';
            dropdown.innerHTML = '<span>Danh mục sản phẩm</span>';
            
            // Thêm các phần tử vào container
            container.appendChild(loginButton);
            container.appendChild(document.createElement('br'));
            container.appendChild(registerButton);
            container.appendChild(document.createElement('br'));
            container.appendChild(searchInput);
            container.appendChild(document.createElement('br'));
            container.appendChild(dropdown);
            
            // Thêm container vào body
            document.body.appendChild(container);
        }""")
        
        # Tìm kiếm phần tử theo mô tả
        logger.info("Tìm kiếm các phần tử theo mô tả:")
        
        # 1. Tìm button đăng nhập
        login_btn = finder.find_element_by_description("nút đăng nhập")
        logger.info(f"1. 'nút đăng nhập': {login_btn} - {'PASS' if login_btn else 'FAIL'}")
        
        # 2. Tìm button đăng ký
        register_btn = finder.find_element_by_description("đăng ký tài khoản")
        logger.info(f"2. 'đăng ký tài khoản': {register_btn} - {'PASS' if register_btn else 'FAIL'}")
        
        # 3. Tìm input tìm kiếm
        search_input = finder.find_element_by_description("tìm kiếm sản phẩm")
        logger.info(f"3. 'tìm kiếm sản phẩm': {search_input} - {'PASS' if search_input else 'FAIL'}")
        
        # 4. Tìm dropdown
        dropdown = finder.find_element_by_description("danh mục sản phẩm")
        logger.info(f"4. 'danh mục sản phẩm': {dropdown} - {'PASS' if dropdown else 'FAIL'}")
        
        # 5. Tìm kiếm phần tử không tồn tại
        non_existent = finder.find_element_by_description("phần tử không tồn tại")
        logger.info(f"5. 'phần tử không tồn tại': {non_existent} - {'PASS' if non_existent is None else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra EnhancedElementFinder: {str(e)}")

def test_ai_element_finder(browser):
    """Kiểm tra AIElementFinder"""
    logger.info("=== KIỂM TRA AI ELEMENT FINDER ===")
    
    try:
        # Khởi tạo AIElementFinder
        finder = AIElementFinder(browser)
        
        # Tạo các phần tử với text để tìm kiếm
        browser.page.evaluate("""() => {
            // Xóa container cũ nếu có
            const oldContainer = document.querySelector('#ai-test-container');
            if (oldContainer) oldContainer.remove();
            
            // Tạo container mới
            const container = document.createElement('div');
            container.id = 'ai-test-container';
            
            // Button thanh toán
            const payButton = document.createElement('button');
            payButton.id = 'pay-btn';
            payButton.textContent = 'Thanh toán ngay';
            
            // Checkbox đồng ý điều khoản
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = 'terms-checkbox';
            const label = document.createElement('label');
            label.htmlFor = 'terms-checkbox';
            label.textContent = 'Tôi đồng ý với điều khoản sử dụng';
            
            // Select box chọn phương thức thanh toán
            const select = document.createElement('select');
            select.id = 'payment-method';
            select.innerHTML = `
                <option value="">Chọn phương thức thanh toán</option>
                <option value="card">Thẻ tín dụng</option>
                <option value="bank">Chuyển khoản ngân hàng</option>
                <option value="ewallet">Ví điện tử</option>
            `;
            
            // Thêm các phần tử vào container
            container.appendChild(payButton);
            container.appendChild(document.createElement('br'));
            container.appendChild(checkbox);
            container.appendChild(label);
            container.appendChild(document.createElement('br'));
            container.appendChild(select);
            
            // Thêm container vào body
            document.body.appendChild(container);
        }""")
        
        # Tìm kiếm phần tử theo mô tả
        logger.info("Tìm kiếm các phần tử theo mô tả:")
        
        # 1. Tìm button thanh toán
        pay_btn = finder.find_element_by_description("nút thanh toán")
        logger.info(f"1. 'nút thanh toán': {pay_btn} - {'PASS' if pay_btn else 'FAIL'}")
        
        # 2. Tìm checkbox đồng ý điều khoản
        terms_checkbox = finder.find_element_by_description("đồng ý với điều khoản")
        logger.info(f"2. 'đồng ý với điều khoản': {terms_checkbox} - {'PASS' if terms_checkbox else 'FAIL'}")
        
        # 3. Tìm select box phương thức thanh toán
        payment_method = finder.find_element_by_description("phương thức thanh toán")
        logger.info(f"3. 'phương thức thanh toán': {payment_method} - {'PASS' if payment_method else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra AIElementFinder: {str(e)}")

def test_page_observer(browser):
    """Kiểm tra PageObserver"""
    logger.info("=== KIỂM TRA PAGE OBSERVER ===")
    
    try:
        # Khởi tạo HTMLAnalyzer và PageObserver
        html_analyzer = HTMLAnalyzer(use_ai=False)
        page_observer = PageObserverSafe(browser, html_analyzer, debug=True)
        
        # Bắt đầu theo dõi trang
        page_observer.start()
        
        # Tạo các phần tử để theo dõi
        browser.page.evaluate("""() => {
            // Xóa container cũ nếu có
            const oldContainer = document.querySelector('#observer-test-container');
            if (oldContainer) oldContainer.remove();
            
            // Tạo container mới
            const container = document.createElement('div');
            container.id = 'observer-test-container';
            
            // Thêm container vào body
            document.body.appendChild(container);
        }""")
        
        # Cập nhật trang và theo dõi
        logger.info("Cập nhật trang và theo dõi các thay đổi")
        
        # 1. Cập nhật trang lần đầu
        browser.page.evaluate("""() => {
            const container = document.querySelector('#observer-test-container');
            container.innerHTML = '<button id="first-button">Nút đầu tiên</button>';
        }""")
        
        # Xử lý cập nhật trang
        update_result_1 = page_observer.process_page_update()
        logger.info(f"Cập nhật lần 1: {'PASS' if update_result_1 else 'FAIL'}")
        
        # 2. Cập nhật trang lần thứ hai
        browser.page.evaluate("""() => {
            const container = document.querySelector('#observer-test-container');
            container.innerHTML += '<button id="second-button">Nút thứ hai</button>';
        }""")
        
        # Xử lý cập nhật trang
        update_result_2 = page_observer.process_page_update()
        logger.info(f"Cập nhật lần 2: {'PASS' if update_result_2 else 'FAIL'}")
        
        # 3. Thử tìm phần tử qua PageObserver
        button = page_observer.find_element_by_description("nút đầu tiên")
        logger.info(f"Tìm 'nút đầu tiên': {button} - {'PASS' if button else 'FAIL'}")
        
        button2 = page_observer.find_element_by_description("nút thứ hai")
        logger.info(f"Tìm 'nút thứ hai': {button2} - {'PASS' if button2 else 'FAIL'}")
        
        # Dừng theo dõi
        page_observer.stop()
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra PageObserver: {str(e)}")

def test_overlay_handling(browser):
    """Kiểm tra xử lý overlay"""
    logger.info("=== KIỂM TRA XỬ LÝ OVERLAY ===")
    
    try:
        # Tạo overlay để kiểm tra
        browser.page.evaluate("""() => {
            // Xóa overlay cũ nếu có
            const oldOverlay = document.querySelector('#test-overlay');
            if (oldOverlay) oldOverlay.remove();
            
            // Tạo overlay
            const overlay = document.createElement('div');
            overlay.id = 'test-overlay';
            overlay.style.position = 'fixed';
            overlay.style.top = '0';
            overlay.style.left = '0';
            overlay.style.width = '100%';
            overlay.style.height = '100%';
            overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
            overlay.style.zIndex = '9999';
            overlay.style.display = 'flex';
            overlay.style.justifyContent = 'center';
            overlay.style.alignItems = 'center';
            
            // Tạo popup bên trong overlay
            const popup = document.createElement('div');
            popup.style.backgroundColor = 'white';
            popup.style.padding = '20px';
            popup.style.borderRadius = '5px';
            popup.style.maxWidth = '400px';
            
            // Tiêu đề popup
            const title = document.createElement('h2');
            title.textContent = 'Thông báo quan trọng';
            
            // Nội dung popup
            const content = document.createElement('p');
            content.textContent = 'Đây là một thông báo quan trọng cần xử lý trước khi tiếp tục.';
            
            // Nút đóng
            const closeButton = document.createElement('button');
            closeButton.textContent = 'Đóng';
            closeButton.className = 'close-button';
            closeButton.onclick = function() {
                overlay.style.display = 'none';
            };
            
            // Thêm các phần tử vào popup
            popup.appendChild(title);
            popup.appendChild(content);
            popup.appendChild(closeButton);
            
            // Thêm popup vào overlay
            overlay.appendChild(popup);
            
            // Thêm overlay vào body
            document.body.appendChild(overlay);
            
            // Tạo button bị overlay che
            const button = document.createElement('button');
            button.id = 'hidden-button';
            button.textContent = 'Button bị che';
            document.body.appendChild(button);
        }""")
        
        # Kiểm tra phát hiện overlay
        overlays = browser.overlay_handler.detect_overlays()
        logger.info(f"Phát hiện overlay: {'PASS' if overlays and len(overlays) > 0 else 'FAIL'}")
        
        # Kiểm tra đóng overlay
        close_result = browser.overlay_handler.close_overlay()
        logger.info(f"Đóng overlay: {'PASS' if close_result else 'FAIL'}")
        
        # Kiểm tra làm cho phần tử có thể click
        clickable_result = browser.overlay_handler.make_element_clickable("#hidden-button")
        logger.info(f"Làm phần tử có thể click: {'PASS' if clickable_result else 'FAIL'}")
        
        # Kiểm tra xóa tất cả overlay
        remove_all_result = browser.overlay_handler.remove_all_overlays()
        logger.info(f"Xóa tất cả overlay: {'PASS' if remove_all_result else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra xử lý overlay: {str(e)}")

def test_selectors_with_various_html(browser):
    """Kiểm tra tìm kiếm với các cấu trúc HTML khác nhau"""
    logger.info("=== KIỂM TRA TÌM KIẾM VỚI CÁC CẤU TRÚC HTML KHÁC NHAU ===")
    
    try:
        # 1. HTML đơn giản
        browser.page.evaluate("""() => {
            // Xóa container cũ nếu có
            const oldContainer = document.querySelector('#various-html-container');
            if (oldContainer) oldContainer.remove();
            
            // Tạo container mới
            const container = document.createElement('div');
            container.id = 'various-html-container';
            
            // 1. HTML đơn giản
            container.innerHTML = `
                <div class="simple-html">
                    <h2>Tiêu đề đơn giản</h2>
                    <p>Đoạn văn bản đơn giản</p>
                    <button id="simple-button">Nút đơn giản</button>
                </div>
            `;
            
            // Thêm container vào body
            document.body.appendChild(container);
        }""")
        
        # Tìm phần tử trong HTML đơn giản
        simple_button = browser.wait_for_selector("#simple-button", timeout=5000)
        logger.info(f"HTML đơn giản - #simple-button: {'PASS' if simple_button else 'FAIL'}")
        
        # 2. HTML phức tạp (sử dụng shadow DOM)
        browser.page.evaluate("""() => {
            const container = document.querySelector('#various-html-container');
            
            // 2. HTML phức tạp với shadow DOM
            const shadowHost = document.createElement('div');
            shadowHost.id = 'shadow-host';
            container.appendChild(shadowHost);
            
            // Tạo shadow root
            const shadowRoot = shadowHost.attachShadow({mode: 'open'});
            
            // Thêm nội dung vào shadow DOM
            shadowRoot.innerHTML = `
                <style>
                    .shadow-button {
                        background-color: blue;
                        color: white;
                        padding: 10px;
                    }
                </style>
                <div class="shadow-content">
                    <h3>Tiêu đề trong Shadow DOM</h3>
                    <p>Đoạn văn bản trong Shadow DOM</p>
                    <button class="shadow-button">Nút trong Shadow DOM</button>
                </div>
            `;
        }""")
        
        # 3. HTML với iframe
        browser.page.evaluate("""() => {
            const container = document.querySelector('#various-html-container');
            
            // 3. HTML với iframe
            const iframe = document.createElement('iframe');
            iframe.id = 'test-iframe';
            iframe.style.width = '300px';
            iframe.style.height = '200px';
            iframe.style.border = '1px solid black';
            container.appendChild(iframe);
            
            // Thêm nội dung vào iframe sau khi nó đã tải
            iframe.onload = function() {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    iframeDoc.body.innerHTML = `
                        <div class="iframe-content">
                            <h3>Tiêu đề trong iframe</h3>
                            <p>Đoạn văn bản trong iframe</p>
                            <button id="iframe-button">Nút trong iframe</button>
                        </div>
                    `;
                } catch (e) {
                    console.error('Không thể truy cập nội dung iframe:', e);
                }
            };
            
            // Trigger onload
            iframe.src = 'about:blank';
        }""")
        
        # Đợi iframe tải xong
        time.sleep(1)
        
        # Tìm phần tử trong iframe
        iframe_selector = "#test-iframe"
        frame = browser.switch_to_iframe(iframe_selector)
        logger.info(f"HTML với iframe - switch_to_iframe: {'PASS' if frame else 'FAIL'}")
        
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra với các cấu trúc HTML khác nhau: {str(e)}")

def main():
    """Hàm chính để chạy tất cả các bài kiểm tra"""
    logger.info("====== BẮT ĐẦU BỘ KIỂM TRA ELEMENT FINDER ======")
    
    try:
        # Khởi tạo trình duyệt
        logger.info("Khởi động trình duyệt...")
        browser = BrowserController(browser_type="chromium", use_ai_fallback=True, debug=True)
        
        # Khởi động trình duyệt
        browser.start_browser(headless=False)
        
        # Điều hướng đến trang test
        browser.navigate_to("about:blank")
        
        # Chạy các bài kiểm tra
        test_basic_selectors(browser)
        test_complex_selectors(browser)
        test_enhanced_element_finder(browser)
        test_ai_element_finder(browser)
        test_page_observer(browser)
        test_overlay_handling(browser)
        test_selectors_with_various_html(browser)
        
        # Đóng trình duyệt
        browser.close_browser()
        
        logger.info("====== HOÀN THÀNH BỘ KIỂM TRA ELEMENT FINDER ======")
        
    except Exception as e:
        logger.error(f"Lỗi khi chạy bộ kiểm tra: {str(e)}")
        
if __name__ == "__main__":
    main()
