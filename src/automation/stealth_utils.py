import random
import logging

USER_AGENTS = [
    # Danh sách user-agent phổ biến
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    # ... thêm nữa
]

class StealthConfig:
    def __init__(self, level=2):
        self.level = level  # 1: nhẹ, 2: vừa, 3: mạnh

    def apply(self, page):
        # Fake user-agent
        ua = random.choice(USER_AGENTS)
        page.set_user_agent(ua)
        # Fake timezone
        if self.level >= 2:
            page.evaluate("Intl.DateTimeFormat = function() { return {resolvedOptions: () => ({timeZone: 'Asia/Ho_Chi_Minh'})} }")
        # Fake WebGL
        if self.level >= 3:
            page.evaluate("Object.defineProperty(WebGLRenderingContext.prototype, 'getParameter', {value: () => 'NVIDIA'})")
        # Fake plugin
        page.evaluate("navigator.plugins.length = 3")
        # Chặn fingerprint phổ biến
        page.evaluate("window.navigator.webdriver = false")
        logging.info(f"[Stealth] Đã áp dụng stealth level {self.level}")

    def detect_bot(self, page):
        # Kiểm tra các dấu hiệu bị phát hiện là bot
        res = page.evaluate("navigator.webdriver")
        if res:
            logging.warning("[Stealth] Có thể bị phát hiện là bot!")
        return res 