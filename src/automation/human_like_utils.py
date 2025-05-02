"""
Human-like Utils Module
Cung cấp các công cụ để mô phỏng hành vi người dùng thực
"""

import logging
import time
import random
import math
import json
from pathlib import Path
import threading

class HumanLikeInteraction:
    """
    Cung cấp các phương thức mô phỏng hành vi người dùng thực khi tương tác với trình duyệt
    """
    
    def __init__(self, browser_controller, debug=False):
        """
        Khởi tạo Human-like Interaction
        
        Args:
            browser_controller: Controller trình duyệt
            debug (bool): Bật log chi tiết
        """
        # Cấu hình logging
        try:
            from src.utils.logging_utils import get_logger
            self.logger = get_logger("HumanLikeInteraction")
        except ImportError:
            self.logger = logging.getLogger("HumanLikeInteraction")
            
        self.browser = browser_controller
        self.debug = debug
        
        # Lưu vết chuột cuối cùng
        self.last_mouse_position = {"x": 0, "y": 0}
        
        # Trạng thái hiển thị con trỏ chuột
        self.show_cursor = True
        self.cursor_initialized = False
        
        # Khởi tạo tham số mô phỏng người dùng
        self._init_human_params()
        
        # Khởi tạo con trỏ chuột nếu có trình duyệt
        if self.browser and self.browser.page:
            self._init_visual_cursor()
            self._auto_restore_cursor_on_navigation()
        
        self.action_lock = threading.Lock()
    
    def _init_human_params(self):
        """Khởi tạo các tham số mô phỏng người dùng"""
        # Tốc độ di chuyển chuột (pixel/ms)
        self.mouse_speed = random.uniform(0.3, 0.7)
        
        # Độ trễ ngẫu nhiên giữa các thao tác (ms)
        self.action_delay_min = 300
        self.action_delay_max = 1200
        
        # Tốc độ gõ phím (ký tự/giây)
        self.typing_speed_min = 5
        self.typing_speed_max = 12
        
        # Tỷ lệ lỗi gõ phím (%)
        self.typing_error_rate = random.uniform(0.5, 2.0)
        
        # Tần suất dừng cuộn trang (%)
        self.scroll_pause_chance = 15
        
        # Tỷ lệ mắt nhìn rồi mới di chuột (%)
        self.look_before_move_chance = 70
        
        # Tọa độ mắt (giả lập sự chú ý, một điểm ảo mà người dùng đang nhìn)
        self.eye_position = {"x": 0, "y": 0}
        
        # Kích thước cửa sổ đang hiển thị
        self.viewport_size = {"width": 1280, "height": 720}
        if self.browser and self.browser.page:
            self.viewport_size = self.browser.page.viewport_size
            
        # Đặc điểm người dùng
        self.user_profile = {
            "reading_speed": random.uniform(150, 400),  # Từ/phút
            "cursor_accuracy": random.uniform(0.85, 0.98),  # Độ chính xác khi di chuột
            "decision_speed": random.uniform(0.8, 1.2),  # Hệ số tốc độ quyết định
            "attention_span": random.uniform(15, 45),  # Thời gian chú ý liên tục (giây)
            "distraction_chance": random.uniform(2, 8),  # Xác suất bị phân tâm (%)
            "hesitation_chance": random.uniform(5, 20),  # Xác suất ngập ngừng (%)
            "double_check_chance": random.uniform(10, 30),  # Xác suất kiểm tra lại (%)
            "age_group": random.choice(["18-24", "25-34", "35-44", "45-54", "55+"]),
            "tech_savvy": random.uniform(0.5, 1.0),  # Mức độ thành thạo công nghệ
            "patience": random.uniform(0.7, 1.0)  # Mức độ kiên nhẫn
        }
        
        # Cập nhật các tham số dựa trên profile người dùng
        self._adjust_params_based_on_profile()
        
        if self.debug:
            self.logger.info(f"Đã khởi tạo profile người dùng: {json.dumps(self.user_profile, indent=2)}")
    
    def _adjust_params_based_on_profile(self):
        """Điều chỉnh các tham số dựa trên profile người dùng"""
        # Điều chỉnh tốc độ gõ phím theo độ thành thạo công nghệ
        tech_factor = self.user_profile["tech_savvy"]
        self.typing_speed_min = 3 + 10 * tech_factor
        self.typing_speed_max = 8 + 15 * tech_factor
        
        # Điều chỉnh tỷ lệ lỗi gõ phím theo độ thành thạo và tuổi
        age_factor = 1.0
        if self.user_profile["age_group"] == "55+":
            age_factor = 1.4
        elif self.user_profile["age_group"] == "45-54":
            age_factor = 1.2
        elif self.user_profile["age_group"] == "18-24":
            age_factor = 0.8
            
        self.typing_error_rate = random.uniform(0.5, 3.0) * (2 - tech_factor) * age_factor
        
        # Điều chỉnh tốc độ quyết định
        decision_speed = self.user_profile["decision_speed"]
        self.action_delay_min = int(300 / decision_speed)
        self.action_delay_max = int(1200 / decision_speed)
        
        # Điều chỉnh độ chính xác chuột
        self.mouse_speed = 0.2 + 0.8 * self.user_profile["cursor_accuracy"]
    
    def safe_action(self, func, *args, **kwargs):
        with self.action_lock:
            return func(*args, **kwargs)
    
    def human_like_delay(self, action_type="normal"):
        """
        Tạo độ trễ giống con người giữa các thao tác
        
        Args:
            action_type (str): Loại thao tác ("normal", "read", "think", "decide")
            
        Returns:
            float: Thời gian trễ (giây)
        """
        # Độ trễ cơ bản
        base_delay = random.uniform(self.action_delay_min, self.action_delay_max) / 1000
        
        # Điều chỉnh theo loại hành động
        if action_type == "read":
            # Thời gian đọc phụ thuộc vào lượng text
            delay = base_delay * random.uniform(1.5, 3.0)
        elif action_type == "think":
            # Thời gian suy nghĩ khi đưa ra quyết định phức tạp
            delay = base_delay * random.uniform(2.0, 4.0)
        elif action_type == "decide":
            # Thời gian quyết định lựa chọn
            delay = base_delay * random.uniform(1.2, 2.5)
        else:
            # Thao tác bình thường
            delay = base_delay
        
        # Thêm biến động ngẫu nhiên
        delay *= random.uniform(0.8, 1.2)
        
        # Ngẫu nhiên thêm thời gian phân tâm
        if random.random() * 100 < self.user_profile["distraction_chance"]:
            delay += random.uniform(1.0, 5.0)  # Bị phân tâm 1-5 giây
            if self.debug:
                self.logger.info(f"Người dùng bị phân tâm: +{delay:.2f}s")
        
        # Ngẫu nhiên thêm thời gian ngập ngừng
        if random.random() * 100 < self.user_profile["hesitation_chance"]:
            delay += random.uniform(0.5, 2.0)  # Ngập ngừng 0.5-2 giây
            if self.debug:
                self.logger.info(f"Người dùng ngập ngừng: +{delay:.2f}s")
        
        time.sleep(delay)
        return delay
    
    def human_like_move_mouse(self, target_x, target_y, click=False, button="left", reason=None):
        """
        Di chuyển chuột theo đường cong tự nhiên đến vị trí mục tiêu
        
        Args:
            target_x (int): Tọa độ X mục tiêu
            target_y (int): Tọa độ Y mục tiêu
            click (bool): Có thực hiện click sau khi di chuyển
            button (str): Nút chuột ("left", "middle", "right")
            reason (str): Lý do di chuyển chuột (để logging)
            
        Returns:
            bool: True nếu thành công
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Cập nhật kích thước viewport nếu cần
            self.viewport_size = self.browser.page.viewport_size
            
            # Hiện tại chuột ở đâu?
            start_x = self.last_mouse_position["x"]
            start_y = self.last_mouse_position["y"]
            
            # Nếu chưa biết vị trí chuột, giả sử từ góc trên bên trái
            if start_x == 0 and start_y == 0:
                start_x = self.viewport_size["width"] // 3
                start_y = 100  # Khoảng thanh địa chỉ/tab trình duyệt
            
            # Giả lập hành vi "nhìn trước khi di chuyển"
            if random.random() * 100 < self.look_before_move_chance:
                # Cập nhật vị trí mắt trước khi di chuyển chuột
                self.eye_position = {"x": target_x, "y": target_y}
                if self.debug:
                    self.logger.debug(f"Người dùng nhìn tới ({target_x}, {target_y}) trước khi di chuyển chuột")
                
                # Đợi một chút sau khi nhìn, trước khi di chuyển chuột
                time.sleep(random.uniform(0.1, 0.3))
            
            # Tính toán khoảng cách và thời gian di chuyển
            distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
            
            # Thêm độ nhiễu cho vị trí đích (mô phỏng độ chính xác của chuột)
            accuracy = self.user_profile["cursor_accuracy"]
            jitter_x = int(random.gauss(0, max(1, (1 - accuracy) * 20)))
            jitter_y = int(random.gauss(0, max(1, (1 - accuracy) * 20)))
            
            # Nếu là click, đảm bảo vẫn click được vào đúng phần tử
            if click:
                # Giảm độ nhiễu để đảm bảo click vào đúng phần tử
                target_x += jitter_x // 2
                target_y += jitter_y // 2
            else:
                target_x += jitter_x
                target_y += jitter_y
            
            # Tạo một đường cong Bezier để mô phỏng chuyển động chuột tự nhiên
            # Chọn 1-2 điểm kiểm soát ngẫu nhiên giữa điểm đầu và điểm cuối
            control_points = []
            
            # Số điểm kiểm soát phụ thuộc vào khoảng cách
            num_control_points = 1 if distance < 300 else 2
            
            for _ in range(num_control_points):
                # Tạo điểm kiểm soát với một số nhiễu ngẫu nhiên
                # Càng xa thì độ lệch càng lớn
                control_x = start_x + (target_x - start_x) * random.uniform(0.3, 0.7)
                control_y = start_y + (target_y - start_y) * random.uniform(0.3, 0.7)
                
                # Thêm độ lệch ngẫu nhiên
                control_x += random.gauss(0, distance * 0.2)
                control_y += random.gauss(0, distance * 0.2)
                
                control_points.append((control_x, control_y))
            
            # Tính số bước di chuyển dựa trên khoảng cách và tốc độ chuột
            # Càng xa càng nhiều bước để di chuyển mượt mà
            steps = max(10, int(distance / (self.mouse_speed * 10)))
            
            # Đảm bảo số bước không quá lớn
            steps = min(steps, 100)
            
            # Thực hiện di chuyển chuột
            for i in range(steps + 1):
                t = i / steps
                
                # Tính tọa độ trên đường cong Bezier
                if num_control_points == 1:
                    # Đường cong bậc 2 với 1 điểm kiểm soát
                    x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_points[0][0] + t ** 2 * target_x
                    y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_points[0][1] + t ** 2 * target_y
                else:
                    # Đường cong bậc 3 với 2 điểm kiểm soát
                    x = (1 - t) ** 3 * start_x + 3 * (1 - t) ** 2 * t * control_points[0][0] + \
                        3 * (1 - t) * t ** 2 * control_points[1][0] + t ** 3 * target_x
                    y = (1 - t) ** 3 * start_y + 3 * (1 - t) ** 2 * t * control_points[0][1] + \
                        3 * (1 - t) * t ** 2 * control_points[1][1] + t ** 3 * target_y
                
                # Thêm hiệu ứng "nghỉ" - đôi khi chuột dừng lại giữa chừng
                should_pause = random.random() < 0.01  # Xác suất dừng 1%
                
                # Thêm một chút nhiễu vào mỗi bước di chuyển
                noise_x = random.gauss(0, 1)
                noise_y = random.gauss(0, 1)
                
                # Cập nhật tọa độ
                current_x = x + noise_x
                current_y = y + noise_y
                
                # Di chuyển chuột đến vị trí mới
                self.browser.page.mouse.move(current_x, current_y)
                
                # Cập nhật con trỏ chuột trực quan
                self._update_visual_cursor(current_x, current_y)
                
                # Cập nhật vị trí chuột cuối cùng
                self.last_mouse_position["x"] = current_x
                self.last_mouse_position["y"] = current_y
                
                # Dừng nếu cần
                if should_pause:
                    time.sleep(random.uniform(0.05, 0.2))
                else:
                    # Tốc độ không đều - chậm ở đầu và cuối, nhanh ở giữa (easing)
                    delay = 0
                    if i < steps * 0.2 or i > steps * 0.8:
                        delay = 0.01  # Chậm hơn ở đầu và cuối
                    
                    time.sleep(max(0.001, delay))  # Đảm bảo ít nhất 1ms
            
            # Thêm độ trễ trước khi click
            if click:
                time.sleep(random.uniform(0.08, 0.2))
                
                # Cập nhật con trỏ chuột với trạng thái đang click
                self._update_visual_cursor(target_x, target_y, clicking=True)
                
                # Click với tốc độ ngẫu nhiên
                if button == "left":
                    if random.random() < 0.05:  # 5% cơ hội double-click
                        self.browser.page.mouse.dblclick(target_x, target_y)
                        if self.debug:
                            self.logger.debug(f"Double-click tại ({target_x}, {target_y})")
                    else:
                        self.browser.page.mouse.click(target_x, target_y)
                        if self.debug:
                            self.logger.debug(f"Click tại ({target_x}, {target_y})")
                elif button == "right":
                    self.browser.page.mouse.click(target_x, target_y, button="right")
                    if self.debug:
                        self.logger.debug(f"Right-click tại ({target_x}, {target_y})")
            
            if reason and self.debug:
                self.logger.info(f"Di chuyển chuột đến ({target_x}, {target_y}) - {reason}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi di chuyển chuột: {str(e)}")
            return False
    
    def _get_best_description(self, step):
        """Lấy mô tả thực tế nhất cho step (ưu tiên text, placeholder, aria-label, label liên kết)"""
        desc = step.get('description')
        if desc and not desc.lower().startswith('bước'):
            return desc
        # Ưu tiên text, placeholder, aria-label
        for key in ['text', 'placeholder', 'aria-label', 'label']:
            if step.get(key):
                return step[key]
        # Nếu là type, lấy value hoặc name của input
        if step.get('action') == 'type' and step.get('selector'):
            try:
                el = self.browser.page.query_selector(step['selector'])
                if el:
                    for attr in ['placeholder', 'aria-label', 'name', 'id']:
                        val = el.get_attribute(attr)
                        if val:
                            return val
            except Exception:
                pass
        return None

    def _find_nearest_input(self, keywords=None):
        keywords = keywords or ["email", "password", "search", "tìm kiếm", "find", "query", "user", "username", "mật khẩu"]
        js_code = f"""
        (keywords) => {{
            const inputs = Array.from(document.querySelectorAll('input, textarea'));
            let best = null;
            let bestScore = 0;
            for (const el of inputs) {{
                let score = 0;
                const type = el.type ? el.type.toLowerCase() : '';
                const placeholder = el.placeholder ? el.placeholder.toLowerCase() : '';
                const aria = el.getAttribute('aria-label') ? el.getAttribute('aria-label').toLowerCase() : '';
                const name = el.name ? el.name.toLowerCase() : '';
                const id = el.id ? el.id.toLowerCase() : '';
                for (const kw of keywords) {{
                    if (type == kw) score += 3;
                    if (placeholder.includes(kw)) score += 2;
                    if (aria.includes(kw)) score += 2;
                    if (name.includes(kw)) score += 1;
                    if (id.includes(kw)) score += 1;
                }}
                // Ưu tiên input hiển thị
                if (el.offsetWidth > 0 && el.offsetHeight > 0) score += 1;
                if (score > bestScore) {{
                    best = el;
                    bestScore = score;
                }}
            }}
            
            if (best) {{
                if (best.id) return '#' + best.id;
                if (best.name) return best.tagName.toLowerCase() + '[name="' + best.name + '"]';
                if (best.className && typeof best.className === 'string') {{
                    const classes = best.className.split(' ').filter(c => c).join('.');
                    return best.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }}
                // Fallback XPath
                let path = '';
                let current = best;
                while (current && current !== document.body) {{
                    const parent = current.parentElement;
                    if (!parent) break;
                    
                    const siblings = [...parent.children];
                    const index = siblings.indexOf(current) + 1;
                    
                    const tagName = current.tagName.toLowerCase();
                    path = `/${{tagName}}[${{index}}]${{path}}`;
                    
                    current = parent;
                }}
                return 'xpath=/html/body' + path;
            }}
            return null;
        }}
        """
        selector = self.browser.page.evaluate(js_code, keywords)
        if selector:
            self.logger.info(f"Đã tìm thấy input gần đúng nhất: {selector}")
        else:
            self.logger.warning("Không tìm thấy input gần đúng nào với các từ khóa: " + str(keywords))
        return selector

    def safe_action(self, func, *args, **kwargs):
        with self.action_lock:
            return func(*args, **kwargs)
    
    def click_with_human_like_delay(self, selector, description=None, retry=2):
        return self.safe_action(self._click_with_human_like_delay, selector, description, retry)

    def _click_with_human_like_delay(self, selector, description=None, retry=2):
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        try:
            # Thử wait_for_selector trước khi thao tác (nếu có hàm này)
            try:
                if hasattr(self.browser.page, 'wait_for_selector'):
                    self.browser.page.wait_for_selector(selector, timeout=5000)
            except Exception:
                pass
            element = self.browser.page.query_selector(selector)
            if not element:
                # Log lại tất cả các button để debug
                try:
                    all_buttons = self.browser.page.evaluate("""() => Array.from(document.querySelectorAll('button')).map(b => b.outerHTML)""")
                except Exception:
                    all_buttons = []
                self.logger.error(f"Không tìm thấy phần tử: {selector}. Các button hiện có: {all_buttons}")
                return False
            box = element.bounding_box()
            if not box:
                self.logger.error(f"Không thể lấy vị trí của phần tử: {selector}")
                return False
            text = element.text_content().strip() if hasattr(element, 'text_content') else ""
            description = description or text or selector
            is_in_viewport = self.browser.page.evaluate(
                "element => {const r = element.getBoundingClientRect(); return r.top >= 0 && r.bottom <= window.innerHeight;}",
                element
            )
            if not is_in_viewport:
                self.logger.info(f"Phần tử không trong viewport, cuộn đến: {description}")
                element.scroll_into_view_if_needed()
                self.human_like_delay("read")
                box = element.bounding_box()
            click_x = box["x"] + random.uniform(0.3, 0.7) * box["width"]
            click_y = box["y"] + random.uniform(0.3, 0.7) * box["height"]
            # Rê chuột qua 1-2 element gần đó trước khi click
            self._move_mouse_via_nearby_elements(click_x, click_y, element, n_steps=random.randint(1,2))
            self.human_like_delay("read")
            self.human_like_move_mouse(click_x, click_y, click=True, reason=f"Click: {description}")
            self.logger.info(f"Đã click phần tử với hành vi người thật: {description}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi click với hành vi người thật: {str(e)}")
            return False

    def human_like_double_click(self, selector, description=None):
        return self.safe_action(self._human_like_double_click, selector, description)

    def _human_like_double_click(self, selector, description=None):
        try:
            element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử để double-click: {selector}")
                return False
            box = element.bounding_box()
            if not box:
                self.logger.error(f"Không thể lấy vị trí của phần tử: {selector}")
                return False
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            # Rê chuột qua 1-2 element gần đó trước khi double-click
            self._move_mouse_via_nearby_elements(x, y, element, n_steps=random.randint(1,2))
            self.human_like_move_mouse(x, y, click=False, reason=f"Double-click: {description or selector}")
            time.sleep(random.uniform(0.05, 0.15))
            self.browser.page.mouse.dblclick(x, y)
            self.logger.info(f"Đã double-click vào {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi double-click: {str(e)}")
            return False

    def human_like_right_click(self, selector, description=None):
        return self.safe_action(self._human_like_right_click, selector, description)

    def _human_like_right_click(self, selector, description=None):
        try:
            element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử để right-click: {selector}")
                return False
            box = element.bounding_box()
            if not box:
                self.logger.error(f"Không thể lấy vị trí của phần tử: {selector}")
                return False
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            # Rê chuột qua 1-2 element gần đó trước khi right-click
            self._move_mouse_via_nearby_elements(x, y, element, n_steps=random.randint(1,2))
            self.human_like_move_mouse(x, y, click=False, reason=f"Right-click: {description or selector}")
            time.sleep(random.uniform(0.05, 0.15))
            self.browser.page.mouse.click(x, y, button="right")
            self.logger.info(f"Đã right-click vào {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi right-click: {str(e)}")
            return False

    def human_like_hover(self, selector, description=None):
        return self.safe_action(self._human_like_hover, selector, description)

    def _human_like_hover(self, selector, description=None):
        try:
            element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử để hover: {selector}")
                return False
            box = element.bounding_box()
            if not box:
                self.logger.error(f"Không thể lấy vị trí của phần tử: {selector}")
                return False
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            # Rê chuột qua 1-2 element gần đó trước khi hover
            self._move_mouse_via_nearby_elements(x, y, element, n_steps=random.randint(1,2))
            self.human_like_move_mouse(x, y, click=False, reason=f"Hover: {description or selector}")
            time.sleep(random.uniform(0.2, 0.6))
            self.logger.info(f"Đã hover chuột lên {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi hover: {str(e)}")
            return False

    def human_like_drag_and_drop(self, source_selector, target_selector, description=None):
        return self.safe_action(self._human_like_drag_and_drop, source_selector, target_selector, description)

    def _human_like_drag_and_drop(self, source_selector, target_selector, description=None):
        """Kéo thả từ element nguồn sang element đích với hành vi người thật"""
        try:
            source = self.browser.page.query_selector(source_selector)
            target = self.browser.page.query_selector(target_selector)
            if not source or not target:
                self.logger.error(f"Không tìm thấy phần tử để drag and drop: {source_selector} -> {target_selector}")
                return False
            box_src = source.bounding_box()
            box_tgt = target.bounding_box()
            if not box_src or not box_tgt:
                self.logger.error(f"Không thể lấy vị trí của phần tử drag/drop")
                return False
            x1 = box_src["x"] + box_src["width"] / 2
            y1 = box_src["y"] + box_src["height"] / 2
            x2 = box_tgt["x"] + box_tgt["width"] / 2
            y2 = box_tgt["y"] + box_tgt["height"] / 2
            self.human_like_move_mouse(x1, y1, click=False, reason=f"Bắt đầu drag: {description or source_selector}")
            time.sleep(random.uniform(0.05, 0.15))
            self.browser.page.mouse.down()
            self.human_like_move_mouse(x2, y2, click=False, reason=f"Kéo đến: {description or target_selector}")
            time.sleep(random.uniform(0.05, 0.15))
            self.browser.page.mouse.up()
            self.logger.info(f"Đã drag and drop từ {source_selector} sang {target_selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi drag and drop: {str(e)}")
            return False

    def _input_has_autocomplete(self, element):
        try:
            datalist_id = element.get_attribute('list')
            if datalist_id:
                datalist = self.browser.page.query_selector(f"datalist#{datalist_id}")
                if datalist:
                    return True
            # Hoặc có thuộc tính autocomplete
            if element.get_attribute('autocomplete'):
                return True
        except Exception:
            pass
        return False

    def _try_autocomplete(self, element):
        try:
            if self._input_has_autocomplete(element):
                # Nhấn mũi tên xuống và Enter để chọn gợi ý đầu tiên
                self.browser.page.keyboard.press('ArrowDown')
                time.sleep(random.uniform(0.05, 0.15))
                self.browser.page.keyboard.press('Enter')
                self.logger.info("Đã chọn gợi ý autocomplete cho input")
        except Exception:
            pass

    def find_and_click_visible_element(self, text_or_description, highlight=True, retry=2):
        tried_selectors = []
        for attempt in range(retry+1):
            # Cách 1: Tìm theo text như cũ
            result = None
            try:
                js_code = f"""(text) => {{
                    // Các loại phần tử cần tìm
                    const elementTypes = [
                        'a', 'button', 'input[type="button"]', 'input[type="submit"]',
                        '[role="button"]', '[role="link"]', '[role="tab"]',
                        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'li'
                    ];
                    
                    const textLower = text.toLowerCase();
                    const allElements = [];
                    
                    // Tìm theo text content
                    for (const type of elementTypes) {{
                        const elements = [...document.querySelectorAll(type)];
                        for (const el of elements) {{
                            const content = el.textContent?.trim().toLowerCase() || '';
                            if (content.includes(textLower)) {{
                                allElements.push({{
                                    element: el,
                                    score: content === textLower ? 1.0 : 0.8,
                                    text: el.textContent?.trim(),
                                    rect: el.getBoundingClientRect(),
                                    tag: el.tagName.toLowerCase(),
                                    visible: (el.offsetWidth > 0 && el.offsetHeight > 0) &&
                                            window.getComputedStyle(el).display !== 'none' &&
                                            window.getComputedStyle(el).visibility !== 'hidden'
                                }});
                            }}
                        }}
                    }}
                    
                    // Tìm theo aria-label
                    const ariaElements = [...document.querySelectorAll('[aria-label]')];
                    for (const el of ariaElements) {{
                        const ariaLabel = el.getAttribute('aria-label')?.toLowerCase() || '';
                        if (ariaLabel.includes(textLower)) {{
                            allElements.push({{
                                element: el,
                                score: ariaLabel === textLower ? 0.9 : 0.7,
                                text: ariaLabel,
                                rect: el.getBoundingClientRect(),
                                tag: el.tagName.toLowerCase(),
                                visible: (el.offsetWidth > 0 && el.offsetHeight > 0) &&
                                        window.getComputedStyle(el).display !== 'none' &&
                                        window.getComputedStyle(el).visibility !== 'hidden'
                            }});
                        }}
                    }}
                    
                    // Tìm theo title
                    const titleElements = [...document.querySelectorAll('[title]')];
                    for (const el of titleElements) {{
                        const title = el.getAttribute('title')?.toLowerCase() || '';
                        if (title.includes(textLower)) {{
                            allElements.push({{
                                element: el,
                                score: title === textLower ? 0.85 : 0.65,
                                text: title,
                                rect: el.getBoundingClientRect(),
                                tag: el.tagName.toLowerCase(),
                                visible: (el.offsetWidth > 0 && el.offsetHeight > 0) &&
                                        window.getComputedStyle(el).display !== 'none' &&
                                        window.getComputedStyle(el).visibility !== 'hidden'
                            }});
                        }}
                    }}
                    
                    // Tìm theo placeholder
                    const placeholderElements = [...document.querySelectorAll('[placeholder]')];
                    for (const el of placeholderElements) {{
                        const placeholder = el.getAttribute('placeholder')?.toLowerCase() || '';
                        if (placeholder.includes(textLower)) {{
                            allElements.push({{
                                element: el,
                                score: placeholder === textLower ? 0.8 : 0.6,
                                text: placeholder,
                                rect: el.getBoundingClientRect(),
                                tag: el.tagName.toLowerCase(),
                                visible: (el.offsetWidth > 0 && el.offsetHeight > 0) &&
                                        window.getComputedStyle(el).display !== 'none' &&
                                        window.getComputedStyle(el).visibility !== 'hidden'
                            }});
                        }}
                    }}
                    
                    // Lọc các phần tử hiển thị
                    const visibleElements = allElements.filter(item => item.visible);
                    
                    // Không tìm thấy phần tử nào
                    if (visibleElements.length === 0) {{
                        return null;
                    }}
                    
                    // Sắp xếp theo điểm và lấy phần tử tốt nhất
                    visibleElements.sort((a, b) => b.score - a.score);
                    
                    // Tạo selector cho phần tử tốt nhất
                    const bestElement = visibleElements[0];
                    
                    // Tạo selector cho phần tử
                    let selector = '';
                    const element = bestElement.element;
                    
                    if (element.id) {{
                        selector = `#${{element.id}}`;
                    }} else if (element.className && typeof element.className === 'string') {{
                        const classes = element.className.split(' ').filter(c => c).join('.');
                        selector = `${{element.tagName.toLowerCase()}}.${{classes}}`;
                    }} else {{
                        // XPath
                        let path = '';
                        let current = element;
                        while (current && current !== document.body) {{
                            const parent = current.parentElement;
                            if (!parent) break;
                            
                            const siblings = [...parent.children];
                            const index = siblings.indexOf(current) + 1;
                            
                            const tagName = current.tagName.toLowerCase();
                            path = `/${{tagName}}[${{index}}]${{path}}`;
                            
                            current = parent;
                        }}
                        selector = `xpath=/html/body${{path}}`;
                    }}
                    
                    return {{
                        selector: selector,
                        text: bestElement.text,
                        score: bestElement.score,
                        tag: bestElement.tag,
                        rect: {{
                            x: bestElement.rect.left,
                            y: bestElement.rect.top,
                            width: bestElement.rect.width,
                            height: bestElement.rect.height
                        }}
                    }};
                }}"""
                result = self.browser.page.evaluate(js_code, text_or_description)
            except Exception:
                pass
            if result and result.get("selector"):
                sel = result["selector"]
                tried_selectors.append(sel)
                # Highlight phần tử nếu yêu cầu
                if highlight and hasattr(self.browser, 'element_inspector') and self.browser.element_inspector:
                    self.browser.element_inspector.highlight_element(
                        sel,
                        color="green",
                        timeout=1500
                    )
                    
                    # Đợi một chút để người dùng thấy highlight
                    time.sleep(random.uniform(0.3, 0.7))
                
                # Mô phỏng người dùng đọc/xem trước khi click
                self.human_like_delay("read")
                
                # Click với hành vi người thật
                click_x = result["rect"]["x"] + result["rect"]["width"] * random.uniform(0.3, 0.7)
                click_y = result["rect"]["y"] + result["rect"]["height"] * random.uniform(0.3, 0.7)
                
                # Di chuyển chuột và click
                self.human_like_move_mouse(
                    click_x, click_y, 
                    click=True,
                    reason=f"Click: {result['text'] or text_or_description}"
                )
                
                self.logger.info(f"Đã click phần tử '{result['text'] or text_or_description}' với hành vi người thật")
                return True
            # Nếu thất bại, thử fallback selector
            if attempt == 0:
                fallback_selectors = self._generate_fallback_selectors(text_or_description)
                for sel in fallback_selectors:
                    if sel not in tried_selectors:
                        tried_selectors.append(sel)
                        result = self.click_with_human_like_delay(sel, text_or_description)
                        if result:
                            self.logger.info(f"Thành công với fallback selector: {sel}")
                            return True
            # Nếu vẫn thất bại, thử button gần đúng nhất
            if attempt == retry:
                sel = self._find_nearest_button([text_or_description])
                if sel and sel not in tried_selectors:
                    tried_selectors.append(sel)
                    result = self.click_with_human_like_delay(sel, text_or_description)
                    if result:
                        self.logger.info(f"Thành công với button gần đúng nhất: {sel}")
                        return True
        self.logger.error(f"Không thể tìm và click. Đã thử các selector: {tried_selectors}")
        return False
    
    def scan_page_like_human(self, focus_area=None, read_time=None):
        """
        Mô phỏng người dùng đang xem/quét trang web
        
        Args:
            focus_area (dict, optional): Khu vực tập trung (x, y, width, height)
            read_time (float, optional): Thời gian đọc, nếu None sẽ tự động tính
            
        Returns:
            bool: True nếu thành công
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Cập nhật kích thước viewport
            self.viewport_size = self.browser.page.viewport_size
            
            # Tính thời gian đọc dựa trên nội dung trang
            if read_time is None:
                # Ước tính số từ trên trang
                word_count = self.browser.page.evaluate("""() => {
                    const text = document.body.innerText;
                    return text.split(/\\s+/).length;
                }""")
                
                # Tính thời gian đọc dựa trên tốc độ đọc
                reading_speed = self.user_profile["reading_speed"]  # từ/phút
                base_read_time = (word_count / reading_speed) * 60  # giây
                
                # Thêm biến động ngẫu nhiên
                read_time = base_read_time * random.uniform(0.7, 1.3)
                
                # Giới hạn thời gian đọc
                read_time = min(max(2.0, read_time), 20.0)  # Từ 2 đến 20 giây
                
                if self.debug:
                    self.logger.debug(f"Dự tính {word_count} từ, thời gian đọc: {read_time:.2f}s")
            
            # Xác định khu vực quét
            if focus_area:
                area_x = focus_area["x"]
                area_y = focus_area["y"]
                area_width = focus_area["width"]
                area_height = focus_area["height"]
            else:
                # Sử dụng toàn bộ viewport làm khu vực quét
                area_x = 0
                area_y = 0
                area_width = self.viewport_size["width"]
                area_height = self.viewport_size["height"]
            
            # Tính số điểm quét dựa trên thời gian đọc
            # Càng nhiều thời gian càng nhiều điểm quét
            scan_points = max(3, int(read_time / 0.8))
            
            start_time = time.time()
            
            # Tạo các điểm quét trong khu vực
            for i in range(scan_points):
                # Tính điểm tiếp theo với mô hình Z-pattern (đọc từ trái qua phải, từ trên xuống dưới)
                progress = i / scan_points
                
                if progress < 0.2:
                    # Phần trên cùng - từ trái sang phải
                    point_x = area_x + area_width * (progress * 5)
                    point_y = area_y + area_height * 0.1
                elif progress < 0.4:
                    # Đường chéo từ phải trên xuống trái giữa
                    point_x = area_x + area_width * (1 - (progress - 0.2) * 5)
                    point_y = area_y + area_height * (0.1 + (progress - 0.2) * 2)
                elif progress < 0.6:
                    # Phần giữa - từ trái sang phải
                    point_x = area_x + area_width * ((progress - 0.4) * 5)
                    point_y = area_y + area_height * 0.5
                elif progress < 0.8:
                    # Đường chéo từ phải giữa xuống trái dưới
                    point_x = area_x + area_width * (1 - (progress - 0.6) * 5)
                    point_y = area_y + area_height * (0.5 + (progress - 0.6) * 2)
                else:
                    # Phần dưới cùng - từ trái sang phải
                    point_x = area_x + area_width * ((progress - 0.8) * 5)
                    point_y = area_y + area_height * 0.9
                
                # Thêm nhiễu ngẫu nhiên
                point_x += random.gauss(0, area_width * 0.05)
                point_y += random.gauss(0, area_height * 0.05)
                
                # Giới hạn trong khu vực
                point_x = max(area_x, min(area_x + area_width, point_x))
                point_y = max(area_y, min(area_y + area_height, point_y))
                
                # Di chuyển mắt (cập nhật eye_position)
                self.eye_position = {"x": point_x, "y": point_y}
                
                # Đôi khi di chuyển chuột theo mắt
                if random.random() < 0.3:  # 30% cơ hội
                    self.human_like_move_mouse(
                        point_x, point_y, 
                        click=False,
                        reason="Theo dõi nội dung"
                    )
                
                # Đôi khi cuộn trang nếu đã đến cuối khu vực hiển thị
                if i > scan_points * 0.7 and random.random() < 0.3:  # 30% cơ hội sau 70% điểm
                    self.human_like_scroll("down", None, "slow", "Cuộn để đọc tiếp")
                    
                    # Cập nhật khu vực quét sau khi cuộn
                    area_y += self.viewport_size["height"] * 0.3
                
                # Đợi một chút giữa các điểm quét
                elapsed = time.time() - start_time
                if elapsed < read_time:
                    remaining = read_time - elapsed
                    point_delay = min(remaining / (scan_points - i), 0.8)
                    time.sleep(point_delay)
            
            # Sau khi kết thúc, đôi khi di chuyển chuột đến một điểm quan tâm cuối cùng
            if random.random() < 0.5:  # 50% cơ hội
                final_x = area_x + area_width * random.uniform(0.3, 0.7)
                final_y = area_y + area_height * random.uniform(0.4, 0.6)
                
                self.human_like_move_mouse(
                    final_x, final_y, 
                    click=False,
                    reason="Điểm quan tâm cuối cùng"
                )
            
            self.logger.info(f"Đã mô phỏng người dùng xem trang trong {read_time:.2f}s")
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi mô phỏng người dùng xem trang: {str(e)}")
            return False
    
    def execute_human_like_workflow(self, steps):
        return self.safe_action(self._execute_human_like_workflow, steps)

    def _execute_human_like_workflow(self, steps):
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        success = True
        
        for i, step in enumerate(steps):
            action = step.get("action", "").lower()
            description = step.get("description", f"Bước {i+1}: {action}")
            
            try:
                self.logger.info(f"Thực hiện {description}")
                
                # Thêm độ trễ tự nhiên giữa các bước
                if i > 0:
                    self.human_like_delay()
                
                if action == "click":
                    # Click phần tử
                    selector = step.get("selector")
                    if not selector:
                        self.logger.error(f"Không có selector cho bước click: {description}")
                        success = False
                        continue
                    
                    result = self.click_with_human_like_delay(selector, description)
                    if not result:
                        self.logger.warning(f"Không thể click phần tử: {selector}")
                        success = False
                
                elif action == "double_click":
                    selector = step.get("selector")
                    if not selector:
                        self.logger.error(f"Không có selector cho bước double_click: {description}")
                        success = False
                        continue
                    result = self.human_like_double_click(selector, description)
                    if not result:
                        self.logger.warning(f"Không thể double-click phần tử: {selector}")
                        success = False
                elif action == "right_click":
                    selector = step.get("selector")
                    if not selector:
                        self.logger.error(f"Không có selector cho bước right_click: {description}")
                        success = False
                        continue
                    result = self.human_like_right_click(selector, description)
                    if not result:
                        self.logger.warning(f"Không thể right-click phần tử: {selector}")
                        success = False
                elif action == "hover":
                    selector = step.get("selector")
                    if not selector:
                        self.logger.error(f"Không có selector cho bước hover: {description}")
                        success = False
                        continue
                    result = self.human_like_hover(selector, description)
                    if not result:
                        self.logger.warning(f"Không thể hover phần tử: {selector}")
                        success = False
                elif action == "drag_and_drop":
                    source = step.get("source_selector")
                    target = step.get("target_selector")
                    if not source or not target:
                        self.logger.error(f"Không có selector cho bước drag_and_drop: {description}")
                        success = False
                        continue
                    result = self.human_like_drag_and_drop(source, target, description)
                    if not result:
                        self.logger.warning(f"Không thể drag and drop: {source} -> {target}")
                        success = False
                elif action == "find_and_click":
                    text = step.get("text")
                    if not text:
                        self.logger.error(f"Không có text cho bước find_and_click: {description}")
                        success = False
                        continue
                    result = self.find_and_click_visible_element(text, highlight=True)
                    if not result:
                        self.logger.warning(f"Không thể tìm và click phần tử có text: {text}")
                        success = False
                elif action == "type":
                    selector = step.get("selector")
                    value = step.get("value", "")
                    
                    if not selector:
                        self.logger.error(f"Không có selector cho bước type: {description}")
                        success = False
                        continue
                    
                    result = self.human_like_type(selector, value, description=description)
                    if not result:
                        self.logger.warning(f"Không thể nhập văn bản vào phần tử: {selector}")
                        success = False
                elif action == "youtube_search":
                    # Chức năng tìm kiếm đặc biệt cho YouTube
                    search_query = step.get("value", "")
                    if not search_query:
                        self.logger.error(f"Không có từ khóa tìm kiếm cho YouTube: {description}")
                        success = False
                        continue
                    
                    result = self.youtube_search(search_query)
                    if not result:
                        self.logger.warning(f"Không thể tìm kiếm trên YouTube: {search_query}")
                        success = False
                elif action == "generic_website":
                    # Tương tác với bất kỳ trang web nào
                    url = step.get("url")
                    if not url:
                        self.logger.error(f"Không có URL cho bước generic_website: {description}")
                        success = False
                        continue
                    
                    actions = step.get("actions")
                    auto_detect = step.get("auto_detect", True)
                    
                    result = self.generic_website_interaction(url, actions, auto_detect)
                    if not result:
                        self.logger.warning(f"Không thể tương tác với trang web: {url}")
                        success = False
                elif action == "ai_website":
                    # Tương tác với trang web AI
                    url = step.get("url")
                    if not url:
                        self.logger.error(f"Không có URL cho bước ai_website: {description}")
                        success = False
                        continue
                    
                    prompt = step.get("prompt")
                    
                    result = self.interact_with_ai_website(url, prompt)
                    if not result:
                        self.logger.warning(f"Không thể tương tác với trang web AI: {url}")
                        success = False
                elif action == "auto_agent":
                    # Chế độ agent tự động
                    url = step.get("url")
                    objective = step.get("objective")
                    max_actions = step.get("max_actions", 20)
                    headless = step.get("headless", False)
                    
                    self.logger.info(f"Kích hoạt chế độ Agent tự động với mục tiêu: {objective}")
                    result = self.auto_agent_mode(url, objective, max_actions, headless)
                    if not result:
                        self.logger.warning(f"Chế độ Agent tự động không thành công")
                        success = False
                elif action == "scroll":
                    direction = step.get("direction", "down")
                    distance = step.get("distance")
                    speed = step.get("speed", "medium")
                    result = self.human_like_scroll(direction, distance, speed, description)
                    if not result:
                        self.logger.warning(f"Không thể cuộn trang: {direction}")
                        success = False
                elif action == "wait":
                    wait_time = step.get("time", 1.0)
                    time.sleep(wait_time)
                    self.logger.info(f"Đã đợi {wait_time}s")
                elif action == "view":
                    area = step.get("area")
                    read_time = step.get("time")
                    result = self.scan_page_like_human(area, read_time)
                    if not result:
                        self.logger.warning("Không thể mô phỏng người dùng xem trang")
                        success = False
                else:
                    self.logger.warning(f"Hành động không được hỗ trợ: {action}")
                    success = False
            
            except Exception as e:
                self.logger.error(f"Lỗi khi thực hiện {description}: {str(e)}")
                success = False
        
        return success

    def _get_nearby_key(self, char):
        """
        Lấy một phím gần với phím đã cho để mô phỏng lỗi gõ
        
        Args:
            char (str): Ký tự gốc
            
        Returns:
            str: Ký tự lỗi
        """
        # Bản đồ bàn phím QWERTY (các phím gần nhau)
        qwerty_map = {
            'q': 'wea', 'w': 'qeas', 'e': 'wrsda', 'r': 'etdf', 't': 'ryfg', 'y': 'tugh', 'u': 'yihj', 
            'i': 'uokj', 'o': 'iplk', 'p': 'ol', 'a': 'qwsz', 's': 'weadzx', 'd': 'erfszxc', 
            'f': 'rtdgcv', 'g': 'tyfhvb', 'h': 'yugjbn', 'j': 'uihknm', 'k': 'iojlm', 
            'l': 'opk', 'z': 'asx', 'x': 'sdzc', 'c': 'dfxv', 'v': 'fgcb', 'b': 'ghnv', 
            'n': 'hjbm', 'm': 'jkn', '1': '2q', '2': '13qw', '3': '24we', '4': '35er', 
            '5': '46rt', '6': '57ty', '7': '68yu', '8': '79ui', '9': '80io', '0': '9op',
            '.': ',l', ',': 'km.', ' ': 'zxcvbnm'
        }
        
        # Chuyển về chữ thường
        lower_char = char.lower()
        
        # Nếu không có trong bản đồ, trả về nguyên ký tự
        if lower_char not in qwerty_map:
            return char
        
        # Lấy một ký tự ngẫu nhiên gần phím hiện tại
        nearby_chars = qwerty_map[lower_char]
        wrong_char = random.choice(nearby_chars)
        
        # Giữ nguyên chữ hoa/thường
        if char.isupper():
            return wrong_char.upper()
        return wrong_char
    
    def human_like_scroll(self, direction="down", distance=None, speed="medium", reason=None):
        return self.safe_action(self._human_like_scroll, direction, distance, speed, reason)

    def _human_like_scroll(self, direction="down", distance=None, speed="medium", reason=None):
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        
        try:
            # Cập nhật kích thước viewport
            self.viewport_size = self.browser.page.viewport_size
            
            # Tính thời gian cuộn dựa trên tốc độ cuộn
            scroll_speed = self.user_profile["decision_speed"]  # pixel/ms
            base_scroll_time = distance / scroll_speed if distance else 500  # ms
            
            # Thêm biến động ngẫu nhiên
            scroll_time = base_scroll_time * random.uniform(0.8, 1.2)
            
            # Thực hiện cuộn trang
            self.browser.page.mouse.wheel(0, -distance)
            time.sleep(scroll_time)
            
            if self.debug:
                self.logger.info(f"Cuộn trang {direction} {distance} pixel với tốc độ {scroll_speed:.2f} pixel/ms trong {scroll_time:.2f}ms")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi cuộn trang: {str(e)}")
            return False

    def _generate_fallback_selectors(self, description_or_text):
        """Sinh ra các selector fallback dựa trên text, aria-label, placeholder, role, title..."""
        keywords = [description_or_text.lower()]
        selectors = []
        # Theo text
        selectors.append(f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keywords[0]}')]")
        # Theo aria-label
        selectors.append(f"//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keywords[0]}')]")
        # Theo placeholder
        selectors.append(f"//*[@placeholder and contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keywords[0]}')]")
        # Theo title
        selectors.append(f"//*[@title and contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keywords[0]}')]")
        # Theo role
        selectors.append(f"//*[@role and contains(translate(@role, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keywords[0]}')]")
        return selectors

    def human_like_type(self, selector, text, delay_range=(0.05, 0.15), correct_errors=True, retry=2, description=None, step=None):
        return self.safe_action(self._human_like_type, selector, text, delay_range, correct_errors, retry, description, step)

    def _human_like_type(self, selector, text, delay_range=(0.05, 0.15), correct_errors=True, retry=2, description=None, step=None):
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
        try:
            element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử: {selector}")
                return False
            box = element.bounding_box()
            if not box:
                self.logger.error(f"Không thể lấy vị trí của phần tử: {selector}")
                return False
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2
            self._adjust_typing_params_for_input(element)
            self.human_like_move_mouse(target_x, target_y, click=True, reason=f"Focus vào field {selector}")
            import random
            time.sleep(random.uniform(0.1, 0.3))
            # Kiểm tra lại focus sau khi click
            is_focused = self.browser.page.evaluate(
                "(selector) => document.activeElement && document.activeElement.matches(selector)", selector
            )
            if not is_focused:
                self.logger.warning(f"Sau khi click, input chưa được focus. Thử focus lại bằng JS: {selector}")
                self.browser.page.evaluate(
                    "(selector) => { const el = document.querySelector(selector); if(el) el.focus(); }", selector
                )
                time.sleep(0.1)
            current_value = element.get_attribute("value") or ""
            if current_value:
                self.browser.page.keyboard.press("Control+a")
                time.sleep(random.uniform(0.05, 0.1))
                self.browser.page.keyboard.press("Backspace")
                time.sleep(random.uniform(0.05, 0.1))
            # Xác suất copy-paste (10-20%)
            if random.random() < 0.15:
                self.browser.page.keyboard.insert_text(text)
                self.logger.info("Đã nhập liệu bằng copy-paste (insert_text)")
                self._try_autocomplete(element)
                self.human_like_move_mouse(
                    target_x + random.uniform(50, 100),
                    target_y + random.uniform(30, 70),
                    reason="Di chuyển ra khỏi field sau khi nhập xong"
                )
                # Kiểm tra lại giá trị sau nhập
                final_value = element.get_attribute("value") or ""
                if final_value.strip() != text.strip():
                    self.logger.warning(f"Giá trị sau nhập không đúng. Thử fill/text bằng JS: {selector}")
                    try:
                        element.fill(text)
                    except Exception:
                        self.browser.page.evaluate(
                            "(selector, value) => { const el = document.querySelector(selector); if(el) el.value = value; }",
                            selector, text
                        )
                return True
            # Nhập từng ký tự như cũ
            typed_text = ""
            error_positions = []
            for i, char in enumerate(text):
                # Đôi khi nhập sai nhưng không sửa ngay
                if random.random() * 100 < self.typing_error_rate:
                    wrong_char = self._get_nearby_key(char)
                    if self.debug:
                        self.logger.debug(f"Lỗi gõ: '{char}' -> '{wrong_char}' (chưa sửa ngay)")
                    self.browser.page.keyboard.press(wrong_char)
                    typed_text += wrong_char
                    error_positions.append(i)
                    # Đôi khi không sửa ngay mà tiếp tục nhập
                    if random.random() < 0.5:
                        continue
                    # Nếu sửa, xóa ký tự vừa nhập
                    self.browser.page.keyboard.press("Backspace")
                    typed_text = typed_text[:-1]
                    time.sleep(random.uniform(0.1, 0.3))
                self.browser.page.keyboard.insert_text(char)
                typed_text += char
                if i < len(text) - 1:
                    typing_speed = random.uniform(self.typing_speed_min, self.typing_speed_max)
                    base_delay = 1.0 / typing_speed
                    char_delay = base_delay * random.uniform(0.8, 1.2)
                    if char in ".,!?;:":
                        char_delay *= random.uniform(1.5, 2.5)
                    if char == " ":
                        char_delay *= random.uniform(1.2, 1.8)
                    time.sleep(char_delay)
                    if len(text) > 10 and random.random() < 0.05:
                        time.sleep(random.uniform(0.5, 2.0))
            self._try_autocomplete(element)
            input_type = element.get_attribute('type') or ''
            if (random.random() < 0.3 or input_type == 'search') and input_type not in ["textarea", "hidden"]:
                time.sleep(random.uniform(0.2, 0.5))
                self.browser.page.keyboard.press("Enter")
                if self.debug:
                    self.logger.debug(f"Đã nhấn Enter sau khi nhập xong")
            self.human_like_move_mouse(
                target_x + random.uniform(50, 100),
                target_y + random.uniform(30, 70),
                reason="Di chuyển ra khỏi field sau khi nhập xong"
            )
            # Kiểm tra lại giá trị sau nhập
            final_value = element.get_attribute("value") or ""
            if final_value.strip() != text.strip():
                self.logger.warning(f"Giá trị sau nhập không đúng. Thử fill/text bằng JS: {selector}")
                try:
                    element.fill(text)
                except Exception:
                    self.browser.page.evaluate(
                        "(selector, value) => { const el = document.querySelector(selector); if(el) el.value = value; }",
                        selector, text
                    )
            self.logger.info(f"Đã nhập văn bản vào {selector} với kiểu người thật")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi nhập văn bản: {str(e)}")
            return False

    def _find_nearest_button(self, keywords=None):
        """Tìm button gần đúng nhất dựa trên từ khóa"""
        keywords = keywords or []
        js_code = f"""
        (keywords) => {{
            const buttons = Array.from(document.querySelectorAll('button, [role="button"], a.btn, a[href], input[type="button"], input[type="submit"]'));
            let best = null;
            let bestScore = 0;
            
            for (const el of buttons) {{
                let score = 0;
                const text = el.textContent ? el.textContent.toLowerCase() : '';
                const aria = el.getAttribute('aria-label') ? el.getAttribute('aria-label').toLowerCase() : '';
                const title = el.getAttribute('title') ? el.getAttribute('title').toLowerCase() : '';
                const name = el.getAttribute('name') ? el.getAttribute('name').toLowerCase() : '';
                const id = el.id ? el.id.toLowerCase() : '';
                
                // Bỏ qua các phần tử không hiển thị
                if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;

                for (const kw of keywords) {{
                    if (!kw) continue;
                    const kwLower = kw.toLowerCase();
                    if (text === kwLower) score += 5;
                    else if (text.includes(kwLower)) score += 3;
                    if (aria === kwLower) score += 4;
                    else if (aria.includes(kwLower)) score += 2;
                    if (title.includes(kwLower)) score += 2;
                    if (name.includes(kwLower)) score += 1;
                    if (id.includes(kwLower)) score += 1;
                }}
                
                // Ưu tiên button hiển thị
                if (el.offsetWidth > 0 && el.offsetHeight > 0) score += 2;
                
                // Ưu tiên button thực sự và loại trừ link không quan trọng
                if (el.tagName.toLowerCase() === 'button') score += 1;
                if (el.tagName.toLowerCase() === 'a' && !el.textContent.trim()) score -= 2;
                
                if (score > bestScore) {{
                    best = el;
                    bestScore = score;
                }}
            }}
            
            if (best) {{
                // Kiểm tra xem phần tử có thể lấy được bounds không
                const rect = best.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return null;
                
                if (best.id) return '#' + best.id;
                if (best.name) return best.tagName.toLowerCase() + '[name="' + best.name + '"]';
                if (best.className && typeof best.className === 'string') {{
                    const classes = best.className.split(' ').filter(c => c).join('.');
                    return best.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }}
                // Fallback XPath
                let path = '';
                let current = best;
                while (current && current !== document.body) {{
                    const parent = current.parentElement;
                    if (!parent) break;
                    const siblings = [...parent.children];
                    const index = siblings.indexOf(current) + 1;
                    const tagName = current.tagName.toLowerCase();
                    path = '/' + tagName + '[' + index + ']' + path;
                    current = parent;
                }}
                return 'xpath=/html/body' + path;
            }}
            return null;
        }}
        """
        selector = self.browser.page.evaluate(js_code, keywords)
        if selector:
            self.logger.info(f"Đã tìm thấy button gần đúng nhất: {selector}")
        else:
            self.logger.warning("Không tìm thấy button gần đúng nào với các từ khóa: " + str(keywords))
        return selector

    def _move_mouse_via_nearby_elements(self, target_x, target_y, target_element, n_steps=1):
        """Di chuyển chuột qua các phần tử lân cận trước khi đến phần tử mục tiêu"""
        try:
            # Lấy các phần tử gần đó
            nearby_elements_js = """
            (targetEl) => {
                const rect = targetEl.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                
                // Lấy tất cả các phần tử có thể click/hover
                const clickableElements = Array.from(document.querySelectorAll('a, button, input, select, [role="button"], [role="link"], [role="tab"]'));
                
                // Lọc các phần tử hiển thị và gần với mục tiêu
                return clickableElements
                    .filter(el => {
                        if (el === targetEl) return false;
                        const elRect = el.getBoundingClientRect();
                        
                        // Kiểm tra xem phần tử có hiển thị không
                        if (elRect.width === 0 || elRect.height === 0) return false;
                        
                        // Kiểm tra phần tử có trong viewport không
                        if (elRect.bottom < 0 || elRect.top > window.innerHeight || 
                            elRect.right < 0 || elRect.left > window.innerWidth) return false;
                        
                        // Tính khoảng cách
                        const elCenterX = elRect.left + elRect.width / 2;
                        const elCenterY = elRect.top + elRect.height / 2;
                        const distance = Math.sqrt(
                            Math.pow(elCenterX - centerX, 2) + 
                            Math.pow(elCenterY - centerY, 2)
                        );
                        
                        // Chỉ lấy các phần tử trong vòng 500px từ mục tiêu
                        return distance < 500;
                    })
                    .map(el => {
                        const r = el.getBoundingClientRect();
                        return {
                            x: r.left + r.width / 2,
                            y: r.top + r.height / 2
                        };
                    })
                    .sort(() => Math.random() - 0.5) // Xáo trộn danh sách
                    .slice(0, 5); // Chỉ lấy 5 phần tử
            }
            """
            
            nearby_points = self.browser.page.evaluate(nearby_elements_js, target_element)
            
            # Nếu không có phần tử gần đó, trả về
            if not nearby_points or len(nearby_points) == 0:
                return
            
            # Lấy vị trí chuột hiện tại
            current_x = self.last_mouse_position["x"]
            current_y = self.last_mouse_position["y"]
            
            # Chỉ di chuyển qua n_steps phần tử
            for i in range(min(n_steps, len(nearby_points))):
                point = nearby_points[i]
                
                # Di chuyển chuột tới phần tử gần đó
                self.human_like_move_mouse(
                    point["x"], 
                    point["y"],
                    click=False,
                    reason="Di chuyển qua phần tử gần đó"
                )
                
                # Đợi một chút
                time.sleep(random.uniform(0.05, 0.2))
        
        except Exception as e:
            # Nếu có lỗi, ghi log nhưng không làm gián đoạn luồng chính
            if self.debug:
                self.logger.debug(f"Lỗi khi di chuyển qua phần tử gần đó: {str(e)}")

    def _adjust_typing_params_for_input(self, element):
        """Điều chỉnh thông số gõ phím dựa trên loại input"""
        try:
            # Lưu tốc độ gõ và tỷ lệ lỗi ban đầu
            original_speed_min = self.typing_speed_min
            original_speed_max = self.typing_speed_max
            original_error_rate = self.typing_error_rate
            
            # Lấy thuộc tính của input để xác định loại
            input_type = element.get_attribute("type") or ""
            input_name = element.get_attribute("name") or ""
            input_id = element.get_attribute("id") or ""
            input_class = element.get_attribute("class") or ""
            placeholder = element.get_attribute("placeholder") or ""
            aria_label = element.get_attribute("aria-label") or ""
            
            # Các từ khóa để nhận dạng trường nhập liệu
            password_keywords = ["password", "pass", "pwd", "mật khẩu", "matkhau"]
            email_keywords = ["email", "mail", "e-mail"]
            search_keywords = ["search", "find", "lookup", "tìm", "tim", "tra cứu", "tracuu"]
            
            # Kiểm tra loại input
            is_password = (
                input_type.lower() == "password" or
                any(kw in input_name.lower() for kw in password_keywords) or
                any(kw in input_id.lower() for kw in password_keywords) or
                any(kw in placeholder.lower() for kw in password_keywords) or
                any(kw in aria_label.lower() for kw in password_keywords)
            )
            
            is_email = (
                input_type.lower() == "email" or
                any(kw in input_name.lower() for kw in email_keywords) or
                any(kw in input_id.lower() for kw in email_keywords) or
                any(kw in placeholder.lower() for kw in email_keywords) or
                any(kw in aria_label.lower() for kw in email_keywords)
            )
            
            is_search = (
                input_type.lower() == "search" or
                any(kw in input_name.lower() for kw in search_keywords) or
                any(kw in input_id.lower() for kw in search_keywords) or
                any(kw in placeholder.lower() for kw in search_keywords) or
                any(kw in aria_label.lower() for kw in search_keywords)
            )
            
            # Điều chỉnh tốc độ gõ và tỷ lệ lỗi dựa trên loại input
            if is_password:
                # Gõ mật khẩu chậm và cẩn thận hơn, nhưng nhiều lỗi hơn
                self.typing_speed_min = original_speed_min * 0.7
                self.typing_speed_max = original_speed_max * 0.8
                self.typing_error_rate = original_error_rate * 1.5
                if self.debug:
                    self.logger.debug("Đã điều chỉnh tốc độ gõ cho trường mật khẩu")
                    
            elif is_email:
                # Gõ email với tốc độ trung bình, ít lỗi hơn
                self.typing_speed_min = original_speed_min * 0.8
                self.typing_speed_max = original_speed_max * 0.9
                self.typing_error_rate = original_error_rate * 0.8
                if self.debug:
                    self.logger.debug("Đã điều chỉnh tốc độ gõ cho trường email")
                    
            elif is_search:
                # Gõ tìm kiếm nhanh hơn
                self.typing_speed_min = original_speed_min * 1.2
                self.typing_speed_max = original_speed_max * 1.3
                self.typing_error_rate = original_error_rate * 0.7
                if self.debug:
                    self.logger.debug("Đã điều chỉnh tốc độ gõ cho trường tìm kiếm")
            
            # Kiểm tra độ dài của input
            input_width = element.bounding_box()["width"]
            if input_width < 150:
                # Input ngắn, gõ chậm và cẩn thận hơn
                self.typing_speed_min *= 0.9
                self.typing_speed_max *= 0.9
                
            elif input_width > 400:
                # Input dài, gõ nhanh hơn
                self.typing_speed_min *= 1.1
                self.typing_speed_max *= 1.1
            
        except Exception as e:
            # Nếu có lỗi, khôi phục thông số ban đầu và ghi log
            self.typing_speed_min = original_speed_min
            self.typing_speed_max = original_speed_max
            self.typing_error_rate = original_error_rate
            if self.debug:
                self.logger.debug(f"Lỗi khi điều chỉnh thông số gõ: {str(e)}")

    def _init_visual_cursor(self):
        """Khởi tạo con trỏ chuột trực quan trên trình duyệt"""
        if not self.browser.page or self.cursor_initialized:
            return

        try:
            # CSS cho con trỏ chuột
            cursor_css = """
            .human-like-cursor {
                position: fixed;
                width: 24px;
                height: 24px;
                background-image: url('data:image/svg+xml;utf8,<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\"><path d=\"M7,2l12,11.2l-5.8,0.5l3.3,7.3l-2.2,1l-3.2-7.4L7,18.5V2\" stroke=\"%23000\" stroke-width=\"1.5\" fill=\"%23fff\" /></svg>');
                background-repeat: no-repeat;
                background-size: contain;
                pointer-events: none;
                z-index: 999999;
                transition: transform 0.05s linear;
                transform-origin: top left;
                opacity: 0.9;
            }
            .human-like-cursor.clicking {
                transform: scale(0.9);
                opacity: 1;
            }
            """
            # JavaScript để tạo và quản lý con trỏ chuột (truyền CSS qua closure, không dùng arguments)
            cursor_js = f"""
            () => {{
                // Chờ document.head và document.body sẵn sàng
                if (!document.head || !document.body) return false;
                // Tạo element con trỏ nếu chưa tồn tại
                if (!document.getElementById('human-like-cursor')) {{
                    // Thêm style
                    const style = document.createElement('style');
                    style.textContent = `{cursor_css}`;
                    document.head.appendChild(style);
                    // Tạo element con trỏ
                    const cursor = document.createElement('div');
                    cursor.id = 'human-like-cursor';
                    cursor.className = 'human-like-cursor';
                    cursor.style.display = 'block'; // Hiển thị mặc định
                    document.body.appendChild(cursor);
                    window._humanLikeCursor = {{
                        element: cursor,
                        visible: true, // Đặt trạng thái là hiển thị
                        clicking: false,
                        position: {{ x: 0, y: 0 }}
                    }};
                }}
                return true;
            }}
            """
            # Inject CSS và JavaScript
            self.browser.page.evaluate(cursor_js)
            self.cursor_initialized = True
            # Đảm bảo con trỏ chuột được hiển thị
            self.show_visual_cursor(True)
            self.logger.info("Đã khởi tạo và hiển thị con trỏ chuột trực quan")
        except Exception as e:
            self.logger.error(f"Lỗi khi khởi tạo con trỏ chuột: {str(e)}")

    def show_visual_cursor(self, show=True):
        """Hiển thị/ẩn con trỏ chuột trực quan"""
        self.show_cursor = show
        if not self.cursor_initialized and show:
            self._init_visual_cursor()
            
        try:
            if self.browser.page:
                self.browser.page.evaluate("""
                (show) => {
                    if (window._humanLikeCursor) {
                        window._humanLikeCursor.visible = show;
                        window._humanLikeCursor.element.style.display = show ? 'block' : 'none';
                    }
                }
                """, show)
        except Exception as e:
            self.logger.error(f"Lỗi khi {show and 'hiển thị' or 'ẩn'} con trỏ chuột: {str(e)}")

    def _update_visual_cursor(self, x, y, clicking=False):
        """Cập nhật vị trí con trỏ chuột trực quan"""
        if not self.show_cursor or not self.cursor_initialized:
            return
            
        try:
            if self.browser.page:
                self.browser.page.evaluate("""
                (position, clicking) => {
                    if (window._humanLikeCursor) {
                        const cursor = window._humanLikeCursor.element;
                        if (cursor) {
                            cursor.style.left = position.x + 'px';
                            cursor.style.top = position.y + 'px';
                            
                            if (clicking) {
                                cursor.classList.add('clicking');
                                setTimeout(() => cursor.classList.remove('clicking'), 200);
                            }
                            
                            window._humanLikeCursor.position = position;
                            window._humanLikeCursor.clicking = clicking;
                        }
                    }
                }
                """, {"x": x, "y": y}, clicking)
        except Exception as e:
            if self.debug:
                self.logger.debug(f"Lỗi khi cập nhật con trỏ chuột: {str(e)}")

    def youtube_search(self, search_query):
        """
        Thực hiện tìm kiếm trên YouTube với hành vi người thật
        
        Args:
            search_query (str): Từ khóa tìm kiếm
            
        Returns:
            bool: True nếu thành công
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
            
        try:
            # 1. Kiểm tra và điều hướng đến YouTube nếu cần
            current_url = self.browser.page.url
            if "youtube.com" not in current_url:
                self.logger.info("Đang điều hướng đến YouTube...")
                self.browser.page.goto("https://www.youtube.com")
                self.human_like_delay("read")
            
            # 2. Tìm thanh tìm kiếm bằng nhiều cách
            js_find_search = """
            () => {
                // Tìm thanh tìm kiếm
                const searchInput = document.querySelector('input#search') || 
                                   document.querySelector('input[name="search_query"]') ||
                                   document.querySelector('input[placeholder*="Search"]') ||
                                   document.querySelector('input[placeholder*="Tìm"]') ||
                                   document.querySelector('input[aria-label*="Search"]') ||
                                   document.querySelector('input[aria-label*="Tìm"]');
                
                if (searchInput) {
                    return {
                        selector: searchInput.id ? '#' + searchInput.id : 
                                 (searchInput.name ? 'input[name="' + searchInput.name + '"]' : 
                                 'input[placeholder="' + (searchInput.placeholder || '') + '"]'),
                        rect: searchInput.getBoundingClientRect()
                    };
                }
                
                return null;
            }
            """
            
            search_result = self.browser.page.evaluate(js_find_search)
            
            if not search_result:
                self.logger.error("Không tìm thấy thanh tìm kiếm YouTube")
                return False
                
            search_selector = search_result["selector"]
            search_rect = search_result["rect"]
            
            # 3. Click vào thanh tìm kiếm
            self.logger.info(f"Đã tìm thấy thanh tìm kiếm: {search_selector}")
            
            # Di chuyển chuột đến thanh tìm kiếm
            click_x = search_rect["x"] + search_rect["width"] * 0.5
            click_y = search_rect["y"] + search_rect["height"] * 0.5
            
            # Di chuyển qua vài phần tử gần đó trước
            element = self.browser.page.query_selector(search_selector)
            if element:
                self._move_mouse_via_nearby_elements(click_x, click_y, element, n_steps=random.randint(1, 3))
            
            # Click vào thanh tìm kiếm
            self.human_like_move_mouse(click_x, click_y, click=True, reason="Click vào thanh tìm kiếm")
            self.human_like_delay()
            
            # 4. Xóa nội dung hiện tại nếu có
            self.browser.page.keyboard.press("Control+a")  # Chọn tất cả
            time.sleep(random.uniform(0.1, 0.3))
            self.browser.page.keyboard.press("Backspace")  # Xóa
            time.sleep(random.uniform(0.1, 0.3))
            
            # 5. Nhập từ khóa tìm kiếm với kiểu người thật
            self._human_like_type_core(search_selector, search_query)
            self.human_like_delay()
            
            # 6. Tìm và nhấn nút tìm kiếm
            js_find_search_button = """
            () => {
                // Tìm nút tìm kiếm
                const searchButton = document.querySelector('#search-icon-legacy') || 
                                    document.querySelector('button[aria-label*="Search"]') ||
                                    document.querySelector('button[aria-label*="Tìm kiếm"]') ||
                                    document.querySelector('ytd-searchbox button') ||
                                    Array.from(document.querySelectorAll('button')).find(btn => {
                                        const rect = btn.getBoundingClientRect();
                                        return rect.width > 0 && rect.height > 0 && 
                                               (btn.getAttribute('aria-label')?.includes('earch') || 
                                                btn.getAttribute('aria-label')?.includes('ìm'));
                                    });
                
                if (searchButton) {
                    const rect = searchButton.getBoundingClientRect();
                    return {
                        selector: searchButton.id ? '#' + searchButton.id : 
                                (searchButton.className && typeof searchButton.className === 'string' ? 
                                'button.' + searchButton.className.split(' ').filter(c => c).join('.') : 
                                'button'),
                        rect: rect
                    };
                }
                
                return null;
            }
            """
            
            button_result = self.browser.page.evaluate(js_find_search_button)
            
            if not button_result:
                self.logger.info("Không tìm thấy nút tìm kiếm, nhấn Enter để tìm kiếm")
                self.browser.page.keyboard.press("Enter")
            else:
                button_selector = button_result["selector"]
                button_rect = button_result["rect"]
                
                self.logger.info(f"Đã tìm thấy nút tìm kiếm: {button_selector}")
                
                # Di chuyển và click vào nút tìm kiếm
                click_x = button_rect["x"] + button_rect["width"] * 0.5
                click_y = button_rect["y"] + button_rect["height"] * 0.5
                
                self.human_like_move_mouse(click_x, click_y, click=True, reason="Click vào nút tìm kiếm")
            
            # 7. Đợi kết quả tìm kiếm
            self.logger.info("Đang đợi kết quả tìm kiếm...")
            time.sleep(random.uniform(2.0, 3.5))
            
            # 8. Mô phỏng người dùng xem kết quả
            self.scan_page_like_human()
            
            # 9. Tìm video phù hợp với từ khóa
            js_find_matching_video = """
            (keyword) => {
                const keywordLower = keyword.toLowerCase();
                const videos = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-compact-video-renderer, ytd-grid-video-renderer'));
                
                for (const video of videos) {
                    const titleEl = video.querySelector('#video-title, #title, .title');
                    if (!titleEl) continue;
                    
                    const title = titleEl.textContent.trim().toLowerCase();
                    const titleMatch = title.includes(keywordLower);
                    
                    if (titleMatch) {
                        const rect = titleEl.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) continue;
                        
                        return {
                            title: titleEl.textContent.trim(),
                            selector: titleEl.id ? '#' + titleEl.id : 
                                     (titleEl.className && typeof titleEl.className === 'string' ? 
                                     titleEl.tagName.toLowerCase() + '.' + titleEl.className.split(' ').filter(c => c).join('.') : 
                                     '#video-title'),
                            rect: rect
                        };
                    }
                }
                
                // Nếu không tìm thấy kết quả chính xác, lấy video đầu tiên
                const firstVideo = videos[0];
                if (firstVideo) {
                    const titleEl = firstVideo.querySelector('#video-title, #title, .title');
                    if (titleEl) {
                        const rect = titleEl.getBoundingClientRect();
                        return {
                            title: titleEl.textContent.trim(),
                            selector: titleEl.id ? '#' + titleEl.id : 
                                     (titleEl.className && typeof titleEl.className === 'string' ? 
                                     titleEl.tagName.toLowerCase() + '.' + titleEl.className.split(' ').filter(c => c).join('.') : 
                                     '#video-title'),
                            rect: rect
                        };
                    }
                }
                
                return null;
            }
            """
            
            video_result = self.browser.page.evaluate(js_find_matching_video, search_query)
            
            if not video_result:
                self.logger.error("Không tìm thấy video phù hợp")
                return False
                
            video_title = video_result["title"]
            video_selector = video_result["selector"]
            video_rect = video_result["rect"]
            
            self.logger.info(f"Đã tìm thấy video: {video_title}")
            
            # Di chuyển và click vào video
            click_x = video_rect["x"] + video_rect["width"] * 0.5
            click_y = video_rect["y"] + video_rect["height"] * 0.5
            
            self.human_like_move_mouse(click_x, click_y, click=True, reason=f"Click vào video: {video_title}")
            
            # Đợi video tải
            self.logger.info("Đang đợi video tải...")
            time.sleep(random.uniform(2.5, 4.0))
            
            # Mô phỏng người dùng xem video
            self.scan_page_like_human()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tìm kiếm YouTube: {str(e)}")
            return False

    def generic_website_interaction(self, url, actions=None, auto_detect=True):
        """
        Thực hiện tương tác với bất kỳ trang web nào với hành vi người dùng thực
        
        Args:
            url (str): URL của trang web cần tương tác
            actions (list, optional): Danh sách các hành động cần thực hiện 
                Mỗi hành động là dict chứa:
                - type: loại hành động ("click", "type", "scroll", etc.)
                - selector: CSS selector của phần tử
                - value: giá trị nhập vào (dành cho type)
                - description: mô tả (tùy chọn)
            auto_detect (bool): Tự động phát hiện các phần tử tương tác được trên trang
            
        Returns:
            bool: True nếu thành công
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
            
        try:
            # 1. Điều hướng đến trang web
            current_url = self.browser.page.url
            if url.lower() not in current_url.lower():
                self.logger.info(f"Đang điều hướng đến {url}...")
                self.browser.page.goto(url)
                self.human_like_delay("read")
            
            # 2. Nếu không có hành động được chỉ định và auto_detect được bật
            if not actions and auto_detect:
                self.logger.info("Đang tự động phát hiện các phần tử tương tác...")
                actions = self._auto_detect_interactive_elements()
            
            # 3. Thực hiện các hành động đã chỉ định
            if actions:
                for action in actions:
                    action_type = action.get("type", "").lower()
                    selector = action.get("selector")
                    value = action.get("value", "")
                    description = action.get("description", f"Hành động {action_type}")
                    
                    if action_type == "click":
                        if not selector:
                            if "text" in action:
                                # Tìm và click theo văn bản
                                result = self.find_and_click_visible_element(action["text"])
                            else:
                                self.logger.error(f"Không có selector cho hành động click: {description}")
                                continue
                        else:
                            result = self.click_with_human_like_delay(selector, description)
                        
                        if not result:
                            self.logger.warning(f"Không thể click phần tử: {selector}")
                    
                    elif action_type == "type":
                        if not selector:
                            # Tìm ô input gần nhất
                            input_el = self._find_nearest_input(action.get("keywords"))
                            if input_el:
                                selector = input_el.get("selector")
                            else:
                                self.logger.error(f"Không tìm thấy ô input cho hành động type: {description}")
                                continue
                        
                        result = self.human_like_type(selector, value, description=description)
                        if not result:
                            self.logger.warning(f"Không thể nhập văn bản vào: {selector}")
                    
                    elif action_type == "scroll":
                        direction = action.get("direction", "down")
                        distance = action.get("distance")
                        speed = action.get("speed", "medium")
                        self.human_like_scroll(direction, distance, speed, description)
                    
                    elif action_type == "wait":
                        wait_time = action.get("time", 1.0)
                        time.sleep(wait_time)
                    
                    elif action_type == "view":
                        self.scan_page_like_human()
                    
                    else:
                        self.logger.warning(f"Loại hành động không được hỗ trợ: {action_type}")
                    
                    # Độ trễ giữa các hành động
                    self.human_like_delay()
            else:
                # Mặc định nếu không có hành động: xem trang
                self.scan_page_like_human()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tương tác với trang web {url}: {str(e)}")
            return False
    
    def _auto_detect_interactive_elements(self):
        """
        Tự động phát hiện các phần tử tương tác được trên trang
        
        Returns:
            list: Danh sách các hành động phát hiện được
        """
        if not self.browser.page:
            return []
            
        try:
            # Sử dụng JavaScript để phát hiện các phần tử tương tác
            js_detect = """
            () => {
                const actions = [];
                
                // Phát hiện form và input
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    const inputs = form.querySelectorAll('input:not([type="hidden"]), textarea');
                    inputs.forEach(input => {
                        if (input.type === 'text' || input.type === 'search' || input.type === 'email' || 
                            input.type === 'password' || input.type === 'tel' || input.tagName === 'TEXTAREA') {
                            const placeholder = input.placeholder || '';
                            const inputType = input.type || 'text';
                            const name = input.name || '';
                            const id = input.id || '';
                            
                            let description = '';
                            // Tìm label
                            let label = null;
                            if (id) {
                                label = document.querySelector(`label[for="${id}"]`);
                            }
                            if (!label) {
                                let parent = input.parentElement;
                                for (let i = 0; i < 3 && parent; i++) {
                                    label = parent.querySelector('label');
                                    if (label) break;
                                    parent = parent.parentElement;
                                }
                            }
                            
                            if (label) {
                                description = label.textContent.trim();
                            } else if (placeholder) {
                                description = placeholder;
                            } else if (name) {
                                description = name.replace(/[_-]/g, ' ');
                            }
                            
                            const selector = input.id ? `#${input.id}` : 
                                (input.name ? `input[name="${input.name}"]` : 
                                `input[type="${inputType}"]`);
                            
                            actions.push({
                                type: 'type',
                                selector: selector,
                                description: `Nhập vào ${description || inputType}`,
                                keywords: [description, placeholder, name, inputType]
                            });
                        }
                    });
                    
                    // Nút submit trong form
                    const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
                    submitButtons.forEach(button => {
                        const text = button.textContent || button.value || 'Submit';
                        const selector = button.id ? `#${button.id}` : 
                            (button.name ? `button[name="${button.name}"]` : 'button[type="submit"]');
                        
                        actions.push({
                            type: 'click',
                            selector: selector,
                            description: `Click vào ${text.trim()}`
                        });
                    });
                });
                
                // Phát hiện các nút và liên kết
                const buttons = document.querySelectorAll('button, a[href], [role="button"], .btn');
                buttons.forEach(button => {
                    if (button.tagName === 'A' && !button.href) return;
                    
                    const text = button.textContent || button.value || '';
                    if (!text.trim()) return;
                    
                    const selector = button.id ? `#${button.id}` : 
                        (button.tagName === 'A' ? `a[href="${button.getAttribute('href')}"]` : 
                        (button.className ? `${button.tagName.toLowerCase()}.${button.className.split(' ')[0]}` : 
                        button.tagName.toLowerCase()));
                    
                    actions.push({
                        type: 'click',
                        selector: selector,
                        description: `Click vào ${text.trim().substring(0, 30)}`
                    });
                });
                
                // Phát hiện các thanh tìm kiếm
                const searchInputs = document.querySelectorAll('input[type="search"], input[placeholder*="search" i], input[placeholder*="tìm" i], input[aria-label*="search" i], input[aria-label*="tìm" i]');
                searchInputs.forEach(input => {
                    const placeholder = input.placeholder || '';
                    const selector = input.id ? `#${input.id}` : 
                        (input.name ? `input[name="${input.name}"]` : 'input[type="search"]');
                    
                    actions.push({
                        type: 'type',
                        selector: selector,
                        description: `Tìm kiếm ${placeholder}`
                    });
                });
                
                return actions;
            }
            """
            
            detected_actions = self.browser.page.evaluate(js_detect)
            self.logger.info(f"Đã phát hiện {len(detected_actions)} phần tử tương tác.")
            
            # Thêm hành động mặc định: xem trang
            detected_actions.insert(0, {
                "type": "view",
                "description": "Xem trang"
            })
            
            # Thêm hành động mặc định: cuộn trang
            detected_actions.append({
                "type": "scroll",
                "direction": "down",
                "description": "Cuộn xuống trang"
            })
            
            return detected_actions
            
        except Exception as e:
            self.logger.error(f"Lỗi khi phát hiện phần tử tương tác: {str(e)}")
            return []
    
    def interact_with_ai_website(self, url, prompt=None):
        """
        Tương tác với trang web AI (ChatGPT, Bard, Claude, v.v.)
        
        Args:
            url (str): URL của trang web AI
            prompt (str, optional): Prompt để gửi đến AI
            
        Returns:
            bool: True nếu thành công
        """
        if not prompt:
            prompt = "Xin chào, tôi đang kiểm tra tính năng tự động hóa. Hãy trả lời ngắn gọn."
            
        # Xác định loại trang web AI
        ai_type = None
        if "chat.openai.com" in url.lower() or "chatgpt" in url.lower():
            ai_type = "chatgpt"
        elif "bard.google.com" in url.lower() or "gemini" in url.lower():
            ai_type = "bard"
        elif "claude.ai" in url.lower():
            ai_type = "claude"
        elif "bing.com/chat" in url.lower():
            ai_type = "bing"
        else:
            ai_type = "unknown"
            
        try:
            # Điều hướng đến trang AI
            if url.lower() not in self.browser.page.url.lower():
                self.logger.info(f"Đang điều hướng đến {url}...")
                self.browser.page.goto(url)
                self.human_like_delay("read")
            
            # Xử lý theo từng loại AI
            if ai_type == "chatgpt":
                # Xử lý ChatGPT
                input_selector = 'textarea[placeholder*="Send a message"]'
                send_selector = 'button[class*="send"], button[aria-label*="Send"]'
                
                # Nhập prompt
                self.human_like_type(input_selector, prompt)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Gửi
                self.click_with_human_like_delay(send_selector, "Gửi prompt tới ChatGPT")
                
                # Đợi phản hồi
                time.sleep(random.uniform(3.0, 5.0))
                self.scan_page_like_human()
                
            elif ai_type == "bard" or ai_type == "gemini":
                # Xử lý Bard/Gemini
                input_selector = 'textarea[placeholder*="Enter text"], textarea[placeholder*="Nhập"]'
                send_selector = 'button[aria-label*="Send"], button[aria-label*="Gửi"]'
                
                # Nhập prompt
                self.human_like_type(input_selector, prompt)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Gửi
                self.click_with_human_like_delay(send_selector, "Gửi prompt tới Bard/Gemini")
                
                # Đợi phản hồi
                time.sleep(random.uniform(3.0, 5.0))
                self.scan_page_like_human()
                
            elif ai_type == "claude":
                # Xử lý Claude
                input_selector = 'div[contenteditable="true"], textarea'
                send_selector = 'button[aria-label*="Send"], button:has(svg)'
                
                # Nhập prompt
                self.human_like_type(input_selector, prompt)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Gửi
                self.click_with_human_like_delay(send_selector, "Gửi prompt tới Claude")
                
                # Đợi phản hồi
                time.sleep(random.uniform(3.0, 5.0))
                self.scan_page_like_human()
                
            elif ai_type == "bing":
                # Xử lý Bing Chat
                input_selector = '#searchbox, textarea'
                send_selector = 'button[aria-label*="Send"], button[aria-label*="Gửi"]'
                
                # Nhập prompt
                self.human_like_type(input_selector, prompt)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Gửi
                self.click_with_human_like_delay(send_selector, "Gửi prompt tới Bing Chat")
                
                # Đợi phản hồi
                time.sleep(random.uniform(3.0, 5.0))
                self.scan_page_like_human()
                
            else:
                # Xử lý AI không xác định
                # Tìm textarea hoặc input
                js_find_input = """
                () => {
                    const textareas = Array.from(document.querySelectorAll('textarea'));
                    const inputs = Array.from(document.querySelectorAll('input[type="text"]'));
                    const contentEditable = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                    
                    const allInputs = [...textareas, ...inputs, ...contentEditable];
                    if (allInputs.length === 0) return null;
                    
                    // Ưu tiên textarea có placeholder chứa từ khóa liên quan đến chat
                    const chatRelated = allInputs.find(el => {
                        const placeholder = el.placeholder?.toLowerCase() || '';
                        return placeholder.includes('message') || 
                               placeholder.includes('chat') || 
                               placeholder.includes('prompt') ||
                               placeholder.includes('nhập') ||
                               placeholder.includes('hỏi');
                    });
                    
                    if (chatRelated) {
                        return {
                            selector: chatRelated.id ? `#${chatRelated.id}` : 
                                     (chatRelated.tagName.toLowerCase() === 'textarea' ? 'textarea' : 
                                     chatRelated.tagName.toLowerCase() === 'input' ? 'input[type="text"]' : 
                                     '[contenteditable="true"]')
                        };
                    }
                    
                    // Nếu không tìm thấy, lấy phần tử đầu tiên
                    const first = allInputs[0];
                    return {
                        selector: first.id ? `#${first.id}` : 
                                 (first.tagName.toLowerCase() === 'textarea' ? 'textarea' : 
                                 first.tagName.toLowerCase() === 'input' ? 'input[type="text"]' : 
                                 '[contenteditable="true"]')
                    };
                }
                """
                
                input_result = self.browser.page.evaluate(js_find_input)
                if not input_result:
                    self.logger.error("Không tìm thấy ô nhập liệu trên trang AI")
                    return False
                
                input_selector = input_result["selector"]
                
                # Nhập prompt
                self.human_like_type(input_selector, prompt)
                time.sleep(random.uniform(0.5, 1.0))
                
                # Tìm nút gửi gần ô nhập
                js_find_send = """
                (inputSelector) => {
                    const inputElement = document.querySelector(inputSelector);
                    if (!inputElement) return null;
                    
                    // Tìm các nút gần ô nhập
                    let parent = inputElement.parentElement;
                    let buttons = [];
                    
                    // Tìm trong 3 cấp cha
                    for (let i = 0; i < 3 && parent; i++) {
                        const btns = Array.from(parent.querySelectorAll('button'));
                        buttons = [...buttons, ...btns];
                        parent = parent.parentElement;
                    }
                    
                    // Lọc các nút có thể là nút gửi
                    const sendButtons = buttons.filter(btn => {
                        const text = btn.textContent?.toLowerCase() || '';
                        const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
                        
                        return text.includes('send') || 
                               text.includes('gửi') || 
                               ariaLabel.includes('send') || 
                               ariaLabel.includes('gửi') ||
                               btn.querySelector('svg'); // Nhiều nút gửi chỉ có biểu tượng
                    });
                    
                    if (sendButtons.length > 0) {
                        const sendBtn = sendButtons[0];
                        return {
                            selector: sendBtn.id ? `#${sendBtn.id}` : 
                                     (sendBtn.className ? `button.${sendBtn.className.split(' ')[0]}` : 
                                     'button')
                        };
                    }
                    
                    // Nếu không tìm thấy, trả về Enter
                    return { useEnter: true };
                }
                """
                
                send_result = self.browser.page.evaluate(js_find_send, input_selector)
                
                if not send_result:
                    # Nếu không tìm thấy nút gửi, dùng Enter
                    self.browser.page.keyboard.press("Enter")
                elif send_result.get("useEnter"):
                    self.browser.page.keyboard.press("Enter")
                else:
                    send_selector = send_result["selector"]
                    self.click_with_human_like_delay(send_selector, "Gửi prompt")
                
                # Đợi phản hồi
                time.sleep(random.uniform(3.0, 5.0))
                self.scan_page_like_human()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Lỗi khi tương tác với trang web AI {url}: {str(e)}")
            return False

    def auto_agent_mode(self, url=None, objective=None, max_actions=20, headless=False):
        """
        Chế độ Agent tự động: Tự tìm phần tử và thực hiện các thao tác tự động
        
        Args:
            url (str, optional): URL trang web cần tương tác. Nếu None sẽ dùng trang hiện tại
            objective (str, optional): Mục tiêu cần đạt được (VD: "Đăng nhập", "Tìm kiếm sản phẩm")
            max_actions (int): Số lượng hành động tối đa được phép thực hiện
            headless (bool): Chạy ẩn trình duyệt hay không
            
        Returns:
            bool: True nếu thành công
        """
        if not self.browser.page:
            self.logger.error("Trình duyệt chưa sẵn sàng")
            return False
            
        # Tạo logger đặc biệt cho chế độ agent
        import logging
        agent_logger = logging.getLogger("AgentAI")
        agent_logger.setLevel(logging.INFO)
        
        # Thêm handler để ghi log ra console
        if not agent_logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
            agent_logger.addHandler(console_handler)
            
            # Thêm file handler để ghi log ra file
            import os
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(os.path.join(log_dir, "agent_actions.log"), encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))
            agent_logger.addHandler(file_handler)
            
        # Thông báo bắt đầu chế độ agent
        agent_logger.info("====== BẮT ĐẦU CHẾ ĐỘ AGENT TỰ ĐỘNG ======")
        if objective:
            agent_logger.info(f"MỤC TIÊU: {objective}")
        
        try:
            # 1. Điều hướng đến URL nếu được cung cấp
            if url:
                agent_logger.info(f"Đang điều hướng đến: {url}")
                self.browser.page.goto(url)
                self.human_like_delay("read")
            
            # 2. Lấy thông tin về trang hiện tại
            current_url = self.browser.page.url
            page_title = self.browser.page.title()
            agent_logger.info(f"TRANG HIỆN TẠI: {page_title} ({current_url})")
            
            # 3. Phân tích cấu trúc trang
            agent_logger.info("Đang phân tích cấu trúc trang...")
            
            # 4. Vòng lặp tự động thực hiện hành động
            action_count = 0
            previous_actions = []
            
            while action_count < max_actions:
                # Phát hiện các phần tử tương tác
                available_actions = self._detect_actionable_elements()
                
                if not available_actions:
                    agent_logger.warning("Không tìm thấy phần tử tương tác nào trên trang")
                    break
                
                # Lọc ra các hành động phù hợp với mục tiêu
                relevant_actions = self._filter_actions_by_objective(available_actions, objective, previous_actions)
                
                if not relevant_actions:
                    agent_logger.warning("Không tìm thấy hành động phù hợp với mục tiêu")
                    # Thử cuộn trang để tìm thêm phần tử
                    agent_logger.info("Đang cuộn trang để tìm thêm phần tử...")
                    self.human_like_scroll("down")
                    continue
                
                # Chọn hành động tốt nhất
                best_action = self._choose_best_action(relevant_actions, objective)
                
                # Ghi log hành động
                agent_logger.info(f"HÀNH ĐỘNG {action_count + 1}: {best_action['description']}")
                
                # Thực hiện hành động
                action_type = best_action["type"]
                
                if action_type == "click":
                    result = self.click_with_human_like_delay(best_action["selector"], best_action["description"])
                    if not result:
                        agent_logger.warning(f"Không thể click: {best_action['description']}")
                
                elif action_type == "type":
                    # Tạo văn bản phù hợp với ngữ cảnh
                    input_text = self._generate_context_aware_text(best_action, objective)
                    agent_logger.info(f"Nhập văn bản: {input_text}")
                    
                    result = self.human_like_type(best_action["selector"], input_text, description=best_action["description"])
                    if not result:
                        agent_logger.warning(f"Không thể nhập văn bản: {best_action['description']}")
                
                elif action_type == "scroll":
                    direction = best_action.get("direction", "down")
                    self.human_like_scroll(direction)
                    agent_logger.info(f"Đã cuộn trang: {direction}")
                
                # Ghi nhớ hành động đã thực hiện
                previous_actions.append(best_action)
                
                # Tăng số lượng hành động
                action_count += 1
                
                # Kiểm tra xem mục tiêu đã đạt được chưa
                if self._is_objective_completed(objective, previous_actions):
                    agent_logger.info(f"MỤC TIÊU ĐÃ ĐẠT ĐƯỢC: {objective}")
                    break
                
                # Đợi trang cập nhật
                self.human_like_delay()
                
                # Kiểm tra xem URL có thay đổi không (chuyển trang)
                new_url = self.browser.page.url
                if new_url != current_url:
                    agent_logger.info(f"Đã chuyển trang: {new_url}")
                    current_url = new_url
                    page_title = self.browser.page.title()
                    agent_logger.info(f"TRANG MỚI: {page_title} ({current_url})")
                    # Xem trang mới
                    self.scan_page_like_human()
            
            # Thông báo kết thúc
            if action_count >= max_actions:
                agent_logger.warning(f"Đã đạt giới hạn số lượng hành động ({max_actions})")
            
            agent_logger.info(f"TỔNG SỐ HÀNH ĐỘNG ĐÃ THỰC HIỆN: {action_count}")
            agent_logger.info("====== KẾT THÚC CHẾ ĐỘ AGENT TỰ ĐỘNG ======")
            
            return True
        
        except Exception as e:
            agent_logger.error(f"LỖI: {str(e)}")
            agent_logger.info("====== CHẾ ĐỘ AGENT TỰ ĐỘNG DỪNG DO LỖI ======")
            return False
    
    def _detect_actionable_elements(self):
        """
        Phát hiện chi tiết các phần tử có thể tương tác trên trang
        
        Returns:
            list: Danh sách các hành động có thể thực hiện
        """
        if not self.browser.page:
            return []
            
        try:
            # Sử dụng JavaScript để phát hiện các phần tử chi tiết
            js_detect_detail = """
            () => {
                const actions = [];
                
                // Hàm lấy độ ưu tiên dựa trên vị trí hiển thị
                const getPriority = (element) => {
                    const rect = element.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) return -1;
                    
                    // Phần tử trong viewport có độ ưu tiên cao hơn
                    const viewportHeight = window.innerHeight;
                    const viewportWidth = window.innerWidth;
                    
                    if (rect.top < 0 || rect.left < 0) return 0;
                    if (rect.top > viewportHeight || rect.left > viewportWidth) return 0;
                    
                    // Các phần tử ở giữa và trên cùng có ưu tiên cao hơn
                    const verticalCenter = Math.abs(rect.top + rect.height/2 - viewportHeight/2);
                    const horizontalCenter = Math.abs(rect.left + rect.width/2 - viewportWidth/2);
                    
                    // Điểm ưu tiên: càng gần trung tâm càng cao (0-10)
                    const priority = 10 - Math.min(10, (verticalCenter / viewportHeight * 10 + horizontalCenter / viewportWidth * 10) / 2);
                    return priority;
                };
                
                // Hàm lấy văn bản có ý nghĩa từ phần tử
                const getMeaningfulText = (element) => {
                    if (!element) return '';
                    
                    // Lấy text trực tiếp từ phần tử
                    let text = element.textContent || '';
                    text = text.trim();
                    
                    // Nếu không có text, tìm từ các thuộc tính
                    if (!text) {
                        const attrs = ['placeholder', 'aria-label', 'title', 'alt', 'name', 'id'];
                        for (const attr of attrs) {
                            if (element.getAttribute(attr)) {
                                text = element.getAttribute(attr);
                                break;
                            }
                        }
                    }
                    
                    // Giới hạn độ dài và làm sạch text
                    return text.replace(/\\s+/g, ' ').trim().substring(0, 50);
                };
                
                // Hàm lấy selector CSS
                const getSelector = (element) => {
                    // Ưu tiên ID
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Nếu có thể nhận dạng bằng thuộc tính 
                    if (element.getAttribute('data-testid')) {
                        return `[data-testid="${element.getAttribute('data-testid')}"]`;
                    }
                    
                    if (element.getAttribute('name')) {
                        return `${element.tagName.toLowerCase()}[name="${element.getAttribute('name')}"]`;
                    }
                    
                    // Dùng class nếu có
                    if (element.className && typeof element.className === 'string' && element.className.trim()) {
                        const classes = element.className.trim().split(/\\s+/);
                        if (classes.length > 0) {
                            return `${element.tagName.toLowerCase()}.${classes[0]}`;
                        }
                    }
                    
                    // Dùng XPath thuần túy khi không thể dùng cách khác
                    return element.tagName.toLowerCase();
                };
                
                // Phát hiện các ô input và textarea
                const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, [contenteditable="true"]');
                inputs.forEach(input => {
                    const inputType = input.type || 'text';
                    if (['text', 'search', 'email', 'password', 'tel', 'url', 'number'].includes(inputType) || 
                        input.tagName === 'TEXTAREA' || input.getAttribute('contenteditable') === 'true') {
                        
                        // Tìm label hoặc mô tả
                        let label = null;
                        if (input.id) {
                            label = document.querySelector(`label[for="${input.id}"]`);
                        }
                        
                        if (!label) {
                            let parent = input.parentElement;
                            for (let i = 0; i < 3 && parent; i++) {
                                label = parent.querySelector('label');
                                if (label) break;
                                parent = parent.parentElement;
                            }
                        }
                        
                        const placeholder = input.placeholder || '';
                        const labelText = label ? label.textContent.trim() : '';
                        const name = input.name || '';
                        
                        let description = '';
                        if (labelText) {
                            description = labelText;
                        } else if (placeholder) {
                            description = `Nhập vào "${placeholder}"`;
                        } else if (name) {
                            description = `Nhập vào trường ${name.replace(/[_-]/g, ' ')}`;
                        } else {
                            description = `Nhập vào trường ${inputType}`;
                        }
                        
                        const rect = input.getBoundingClientRect();
                        const priority = getPriority(input);
                        
                        if (priority >= 0) {
                            actions.push({
                                type: 'type',
                                selector: getSelector(input),
                                description: description,
                                placeholder: placeholder,
                                inputType: inputType,
                                label: labelText,
                                name: name,
                                priority: priority,
                                x: rect.left + rect.width/2,
                                y: rect.top + rect.height/2,
                                width: rect.width,
                                height: rect.height,
                                required: input.required,
                                value: input.value || ''
                            });
                        }
                    }
                });
                
                // Phát hiện các nút và liên kết
                const clickables = document.querySelectorAll(
                    'button, a[href], [role="button"], [role="link"], input[type="submit"], input[type="button"], .btn, .button'
                );
                clickables.forEach(element => {
                    // Bỏ qua liên kết không có href
                    if (element.tagName === 'A' && !element.getAttribute('href')) return;
                    
                    const text = getMeaningfulText(element);
                    if (!text) return;
                    
                    const rect = element.getBoundingClientRect();
                    const priority = getPriority(element);
                    
                    if (priority >= 0) {
                        // Phân loại nút theo chức năng
                        let buttonType = 'normal';
                        const lowerText = text.toLowerCase();
                        
                        if (lowerText.includes('search') || lowerText.includes('tìm') || lowerText.includes('find')) {
                            buttonType = 'search';
                        } else if (lowerText.includes('login') || lowerText.includes('sign in') || lowerText.includes('đăng nhập')) {
                            buttonType = 'login';
                        } else if (lowerText.includes('submit') || lowerText.includes('send') || lowerText.includes('gửi')) {
                            buttonType = 'submit';
                        } else if (lowerText.includes('next') || lowerText.includes('tiếp') || lowerText.includes('continue')) {
                            buttonType = 'next';
                        } else if (lowerText.includes('cancel') || lowerText.includes('hủy')) {
                            buttonType = 'cancel';
                        }
                        
                        actions.push({
                            type: 'click',
                            selector: getSelector(element),
                            description: `Click vào "${text}"`,
                            text: text,
                            priority: priority,
                            buttonType: buttonType,
                            x: rect.left + rect.width/2,
                            y: rect.top + rect.height/2,
                            width: rect.width,
                            height: rect.height,
                            isLink: element.tagName === 'A',
                            href: element.tagName === 'A' ? element.getAttribute('href') : null
                        });
                    }
                });
                
                // Phát hiện các ô checkbox và radio
                const checkables = document.querySelectorAll('input[type="checkbox"], input[type="radio"]');
                checkables.forEach(element => {
                    // Tìm label
                    let label = null;
                    if (element.id) {
                        label = document.querySelector(`label[for="${element.id}"]`);
                    }
                    
                    if (!label) {
                        let parent = element.parentElement;
                        for (let i = 0; i < 3 && parent; i++) {
                            label = parent.querySelector('label');
                            if (label) break;
                            parent = parent.parentElement;
                        }
                    }
                    
                    const text = label ? label.textContent.trim() : (element.name || element.id || element.type);
                    
                    const rect = element.getBoundingClientRect();
                    const priority = getPriority(element);
                    
                    if (priority >= 0) {
                        actions.push({
                            type: 'click',
                            selector: getSelector(element),
                            description: `${element.checked ? 'Bỏ chọn' : 'Chọn'} "${text}"`,
                            text: text,
                            priority: priority,
                            buttonType: element.type,
                            x: rect.left + rect.width/2,
                            y: rect.top + rect.height/2,
                            width: rect.width,
                            height: rect.height,
                            checked: element.checked,
                            group: element.name
                        });
                    }
                });
                
                // Phát hiện các ô select (dropdown)
                const selects = document.querySelectorAll('select');
                selects.forEach(select => {
                    // Tìm label
                    let label = null;
                    if (select.id) {
                        label = document.querySelector(`label[for="${select.id}"]`);
                    }
                    
                    const text = label ? label.textContent.trim() : (select.name || 'select');
                    
                    const rect = select.getBoundingClientRect();
                    const priority = getPriority(select);
                    
                    if (priority >= 0) {
                        // Lấy danh sách các lựa chọn
                        const options = Array.from(select.options).map(option => ({
                            text: option.textContent.trim(),
                            value: option.value,
                            selected: option.selected
                        }));
                        
                        actions.push({
                            type: 'click',
                            selector: getSelector(select),
                            description: `Chọn từ dropdown "${text}"`,
                            text: text,
                            priority: priority,
                            buttonType: 'select',
                            x: rect.left + rect.width/2,
                            y: rect.top + rect.height/2,
                            width: rect.width,
                            height: rect.height,
                            options: options,
                            selectedIndex: select.selectedIndex
                        });
                    }
                });
                
                // Thêm hành động cuộn trang nếu trang dài
                if (document.body.scrollHeight > window.innerHeight * 1.5) {
                    actions.push({
                        type: 'scroll',
                        direction: 'down',
                        description: 'Cuộn xuống',
                        priority: 1 // Ưu tiên thấp
                    });
                    
                    if (window.scrollY > window.innerHeight) {
                        actions.push({
                            type: 'scroll',
                            direction: 'up',
                            description: 'Cuộn lên',
                            priority: 0.5 // Ưu tiên rất thấp
                        });
                    }
                }
                
                // Sắp xếp theo ưu tiên (từ cao xuống thấp)
                return actions.sort((a, b) => b.priority - a.priority);
            }
            """
            
            detected_actions = self.browser.page.evaluate(js_detect_detail)
            return detected_actions
            
        except Exception as e:
            self.logger.error(f"Lỗi khi phát hiện phần tử tương tác: {str(e)}")
            return []
    
    def _filter_actions_by_objective(self, actions, objective, previous_actions):
        """
        Lọc các hành động phù hợp với mục tiêu
        
        Args:
            actions (list): Danh sách các hành động có thể thực hiện
            objective (str): Mục tiêu cần đạt được
            previous_actions (list): Các hành động đã thực hiện trước đó
            
        Returns:
            list: Danh sách các hành động phù hợp
        """
        if not objective:
            return actions  # Không lọc nếu không có mục tiêu
            
        # Chuyển đổi mục tiêu thành từ khóa
        objective_lower = objective.lower()
        
        # Các từ khóa phổ biến theo mục tiêu
        objective_keywords = {
            'đăng nhập': ['login', 'sign in', 'đăng nhập', 'tài khoản', 'username', 'email', 'password', 'mật khẩu'],
            'đăng ký': ['register', 'sign up', 'đăng ký', 'tạo tài khoản', 'create account'],
            'tìm kiếm': ['search', 'tìm kiếm', 'tìm', 'find', 'lookup'],
            'mua hàng': ['buy', 'purchase', 'mua', 'add to cart', 'thêm vào giỏ', 'giỏ hàng', 'checkout', 'thanh toán'],
            'liên hệ': ['contact', 'liên hệ', 'gửi tin nhắn', 'send message', 'support', 'hỗ trợ']
        }
        
        # Tìm từ khóa phù hợp với mục tiêu
        keywords = []
        for key, values in objective_keywords.items():
            if any(keyword in objective_lower for keyword in [key] + values):
                keywords.extend(values)
                
        if not keywords:
            # Nếu không khớp với mục tiêu nào cụ thể, sử dụng các từ trong objective
            keywords = [word for word in objective_lower.split() if len(word) > 3]
        
        # Tính điểm liên quan đến mục tiêu cho mỗi hành động
        for action in actions:
            relevance_score = 0
            
            # Phân tích văn bản của hành động
            action_text = ''
            if 'description' in action:
                action_text += ' ' + action['description'].lower()
            if 'text' in action:
                action_text += ' ' + action['text'].lower()
            if 'placeholder' in action:
                action_text += ' ' + (action['placeholder'] or '').lower()
            if 'label' in action:
                action_text += ' ' + (action['label'] or '').lower()
            if 'inputType' in action:
                action_text += ' ' + (action['inputType'] or '').lower()
            
            # Tính điểm dựa trên số từ khóa khớp
            for keyword in keywords:
                if keyword in action_text:
                    relevance_score += 1
            
            # Điều chỉnh điểm theo loại nút
            if action.get('type') == 'click' and action.get('buttonType'):
                button_type = action.get('buttonType')
                if 'đăng nhập' in objective_lower and button_type == 'login':
                    relevance_score += 3
                elif 'tìm kiếm' in objective_lower and button_type == 'search':
                    relevance_score += 3
                elif button_type == 'submit':
                    relevance_score += 1
            
            # Điều chỉnh điểm theo loại input
            if action.get('type') == 'type':
                input_type = action.get('inputType')
                if 'đăng nhập' in objective_lower:
                    if input_type == 'password':
                        relevance_score += 2
                    elif input_type == 'email' or input_type == 'text':
                        if any(k in action_text for k in ['email', 'username', 'tài khoản', 'user']):
                            relevance_score += 2
                elif 'tìm kiếm' in objective_lower and input_type == 'search':
                    relevance_score += 2
            
            # Lưu điểm liên quan
            action['relevance_score'] = relevance_score
        
        # Lọc các hành động có điểm liên quan > 0, hoặc trả về tất cả nếu không có gì liên quan
        relevant_actions = [a for a in actions if a.get('relevance_score', 0) > 0]
        
        # Loại bỏ các hành động đã thực hiện trước đó
        if previous_actions:
            previous_selectors = [pa.get('selector') for pa in previous_actions if 'selector' in pa]
            relevant_actions = [a for a in relevant_actions if a.get('selector') not in previous_selectors]
        
        # Nếu không tìm thấy hành động liên quan, trả về tất cả
        if not relevant_actions:
            return actions
            
        return relevant_actions
    
    def _choose_best_action(self, actions, objective):
        """
        Chọn hành động tốt nhất từ danh sách các hành động có thể thực hiện
        
        Args:
            actions (list): Danh sách các hành động có thể thực hiện
            objective (str): Mục tiêu cần đạt được
            
        Returns:
            dict: Hành động tốt nhất
        """
        if not actions:
            return None
            
        # Sắp xếp theo điểm liên quan (nếu có) và ưu tiên
        sorted_actions = sorted(
            actions, 
            key=lambda x: (x.get('relevance_score', 0), x.get('priority', 0)), 
            reverse=True
        )
        
        # Trả về hành động tốt nhất
        return sorted_actions[0]
    
    def _generate_context_aware_text(self, action, objective):
        """
        Tạo văn bản đầu vào phù hợp với ngữ cảnh
        
        Args:
            action (dict): Thông tin về hành động cần thực hiện
            objective (str): Mục tiêu cần đạt được
            
        Returns:
            str: Văn bản đầu vào phù hợp
        """
        # Nếu không có mục tiêu, sử dụng văn bản mặc định
        if not objective:
            if action.get('inputType') == 'search':
                return "từ khóa tìm kiếm mẫu"
            elif action.get('inputType') == 'email':
                return "example@gmail.com"
            elif action.get('inputType') == 'password':
                return "password123"
            return "văn bản mẫu"
            
        # Xác định loại input và tạo văn bản phù hợp
        input_type = action.get('inputType', '')
        placeholder = action.get('placeholder', '')
        label = action.get('label', '')
        description = action.get('description', '')
        
        objective_lower = objective.lower()
        
        # Đăng nhập
        if 'đăng nhập' in objective_lower or 'login' in objective_lower:
            if input_type == 'email' or 'email' in placeholder.lower() or 'email' in label.lower():
                return "example@gmail.com"
            elif input_type == 'password' or 'password' in placeholder.lower() or 'mật khẩu' in placeholder.lower():
                return "password123"
            elif 'user' in placeholder.lower() or 'tài khoản' in placeholder.lower() or 'username' in placeholder.lower():
                return "testuser"
                
        # Tìm kiếm
        elif 'tìm kiếm' in objective_lower or 'search' in objective_lower:
            # Trích xuất từ khóa từ mục tiêu
            search_words = objective_lower.replace('tìm kiếm', '').replace('search', '').strip()
            if search_words:
                return search_words
            return "từ khóa tìm kiếm"
            
        # Đăng ký
        elif 'đăng ký' in objective_lower or 'register' in objective_lower or 'sign up' in objective_lower:
            if input_type == 'email' or 'email' in placeholder.lower():
                return "newuser@gmail.com"
            elif input_type == 'password' or 'password' in placeholder.lower() or 'mật khẩu' in placeholder.lower():
                return "StrongPassword123"
            elif 'name' in placeholder.lower() or 'tên' in placeholder.lower():
                return "Nguyễn Văn A"
            elif 'user' in placeholder.lower() or 'tài khoản' in placeholder.lower() or 'username' in placeholder.lower():
                return "newuser" + str(int(time.time()) % 1000)
            elif 'phone' in placeholder.lower() or 'số điện thoại' in placeholder.lower() or 'sdt' in placeholder.lower():
                return "0912345678"
                
        # Liên hệ
        elif 'liên hệ' in objective_lower or 'contact' in objective_lower:
            if input_type == 'email' or 'email' in placeholder.lower():
                return "contact@gmail.com"
            elif 'name' in placeholder.lower() or 'tên' in placeholder.lower():
                return "Nguyễn Văn A"
            elif 'phone' in placeholder.lower() or 'số điện thoại' in placeholder.lower():
                return "0912345678"
            elif 'message' in placeholder.lower() or 'tin nhắn' in placeholder.lower() or input_type == 'textarea':
                return "Đây là tin nhắn liên hệ mẫu. Vui lòng liên hệ lại cho tôi qua email."
                
        # Trường hợp mặc định: sử dụng placeholder làm gợi ý
        if placeholder:
            if len(placeholder) < 20:
                return placeholder + " (mẫu)"
            else:
                return "Dữ liệu mẫu theo yêu cầu"
                
        # Không có thông tin đủ: tạo văn bản chung
        return "Dữ liệu mẫu"
    
    def _is_objective_completed(self, objective, previous_actions):
        """
        Kiểm tra xem mục tiêu đã hoàn thành chưa
        
        Args:
            objective (str): Mục tiêu cần đạt được
            previous_actions (list): Các hành động đã thực hiện
            
        Returns:
            bool: True nếu mục tiêu đã hoàn thành
        """
        if not objective:
            return len(previous_actions) > 0
            
        # Kiểm tra URL hiện tại
        current_url = self.browser.page.url
        objective_lower = objective.lower()
        
        # Kiểm tra dựa trên URL và mục tiêu
        if 'đăng nhập' in objective_lower or 'login' in objective_lower:
            # Kiểm tra các dấu hiệu đăng nhập thành công
            if 'account' in current_url or 'dashboard' in current_url:
                return True
                
            # Kiểm tra các phần tử trên trang
            js_check_logged_in = """
            () => {
                // Tìm các phần tử chỉ hiển thị khi đã đăng nhập
                const userElements = document.querySelectorAll(
                    '[class*="user"], [class*="account"], [class*="profile"], [id*="user"], [id*="account"]'
                );
                
                // Kiểm tra các nút đăng xuất
                const logoutButtons = Array.from(document.querySelectorAll('a, button')).filter(el => {
                    const text = (el.textContent || '').toLowerCase();
                    return text.includes('logout') || text.includes('log out') || text.includes('đăng xuất');
                });
                
                return {
                    hasUserElements: userElements.length > 0,
                    hasLogoutButton: logoutButtons.length > 0
                };
            }
            """
            
            login_check = self.browser.page.evaluate(js_check_logged_in)
            if login_check.get('hasUserElements') or login_check.get('hasLogoutButton'):
                return True
        
        # Kiểm tra xem đã thực hiện đủ nhiều hành động chưa (tối thiểu 3)
        if len(previous_actions) >= 3:
            # Đã click vào một nút liên quan đến mục tiêu
            submit_actions = [a for a in previous_actions if 
                             a.get('type') == 'click' and a.get('buttonType') in ['submit', 'search', 'login', 'next']]
            
            if submit_actions:
                return True
        
        return False

    # --- TỰ ĐỘNG KHÔI PHỤC CON TRỎ CHUỘT KHI CHUYỂN TRANG ---
    def _auto_restore_cursor_on_navigation(self):
        """Tự động khởi tạo lại con trỏ chuột khi chuyển trang mới"""
        if not self.browser or not self.browser.page:
            return
        try:
            def on_navigate(event=None):
                self.cursor_initialized = False
                self._init_visual_cursor()
                self.logger.info("Tự động khôi phục con trỏ chuột sau khi chuyển trang mới")
            # Gắn sự kiện chuyển trang
            if hasattr(self.browser.page, 'on'):
                self.browser.page.on('framenavigated', on_navigate)
                self.browser.page.on('load', on_navigate)
        except Exception as e:
            self.logger.error(f"Lỗi khi gắn auto-restore cursor: {str(e)}")

    def focus_input(self, selector):
        return self.safe_action(self._focus_input, selector)

    def _focus_input(self, selector):
        try:
            element = self.browser.page.query_selector(selector)
            if not element:
                self.logger.error(f"Không tìm thấy phần tử để focus: {selector}")
                return False
            self.browser.page.evaluate(
                "(selector) => { const el = document.querySelector(selector); if(el) el.focus(); }", selector
            )
            self.logger.info(f"Đã focus vào input: {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Lỗi khi focus input: {str(e)}")
            return False
