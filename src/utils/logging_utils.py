"""
Logging Utilities
Cung cấp các tiện ích để xử lý logging với hỗ trợ Unicode
"""

import logging
import sys

def configure_unicode_logging(log_file="browser_automation.log", log_level=logging.INFO):
    """
    Cấu hình logging với hỗ trợ Unicode
    
    Args:
        log_file (str): Tên file log
        log_level: Mức độ log (default: INFO)
    """
    # File handler với UTF-8
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Console handler với xử lý lỗi encoding
    console_handler = EncodingSafeStreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Thiết lập root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Xóa các handlers hiện có để tránh trùng lặp
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Thêm handlers mới
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

class EncodingSafeStreamHandler(logging.StreamHandler):
    """
    Stream handler xử lý an toàn cho lỗi Unicode
    """
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Thay thế các ký tự không thể mã hóa
            msg = self.format(record)
            try:
                stream = self.stream
                # Sử dụng errors='replace' để thay thế các ký tự không thể mã hóa bằng '?'
                safe_msg = msg.encode('cp1252', errors='replace').decode('cp1252')
                stream.write(safe_msg + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
        except Exception:
            self.handleError(record)

def get_logger(name, log_file=None, log_level=logging.INFO):
    """
    Lấy logger với xử lý Unicode
    
    Args:
        name (str): Tên logger
        log_file (str, optional): Tên file log riêng (nếu khác mặc định)
        log_level: Mức độ log
        
    Returns:
        Logger: Logger đã cấu hình
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Nếu logger chưa có handlers
    if not logger.handlers:
        # Sử dụng file log riêng nếu được cung cấp
        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(file_handler)
            
        # Thêm console handler nếu chưa có trong root logger
        if not any(isinstance(h, EncodingSafeStreamHandler) for h in logging.getLogger().handlers):
            console_handler = EncodingSafeStreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
    
    return logger
