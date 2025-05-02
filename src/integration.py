"""
Integration Module
Tự động tích hợp các phiên bản sửa lỗi vào dự án
"""

import os
import sys
import logging
import time
import shutil
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("integration.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Integration")

def backup_file(file_path):
    """Tạo bản sao lưu của tệp"""
    backup_path = f"{file_path}.bak"
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Đã sao lưu: {file_path} -> {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Không thể sao lưu {file_path}: {str(e)}")
        return False

def replace_file(original_path, fixed_path):
    """Thay thế tệp gốc bằng phiên bản sửa lỗi"""
    try:
        # Sao lưu tệp gốc
        if not backup_file(original_path):
            return False
            
        # Thay thế tệp
        shutil.copy2(fixed_path, original_path)
        logger.info(f"Đã thay thế: {original_path}")
        return True
    except Exception as e:
        logger.error(f"Không thể thay thế {original_path}: {str(e)}")
        return False
        
def update_import_statement(file_path, old_import, new_import):
    """Cập nhật câu lệnh import trong tệp"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        updated_content = content.replace(old_import, new_import)
        
        if content != updated_content:
            # Sao lưu tệp gốc
            if not backup_file(file_path):
                return False
                
            # Ghi nội dung đã cập nhật
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
                
            logger.info(f"Đã cập nhật import trong {file_path}")
            return True
        else:
            logger.info(f"Không cần cập nhật import trong {file_path}")
            return True
    except Exception as e:
        logger.error(f"Không thể cập nhật import trong {file_path}: {str(e)}")
        return False

def integrate_fixed_classes():
    """Tích hợp tất cả các lớp đã sửa lỗi vào dự án"""
    # Đường dẫn cơ sở
    base_dir = Path(__file__).parent
    
    # Danh sách các tệp cần tích hợp
    integrations = [
        {
            "original": base_dir / "ai" / "page_observer" / "page_observer_safe.py",
            "fixed": base_dir / "ai" / "page_observer" / "page_observer_fixed.py",
            "imports_to_update": [
                {
                    "files": [base_dir / "ai" / "enhanced_element_finder.py"],
                    "old": "from .page_observer import PageObserverSafe",
                    "new": "from .page_observer.page_observer_fixed import PageObserverFixed"
                }
            ]
        },
        {
            "original": base_dir / "ai" / "enhanced_element_finder.py",
            "fixed": base_dir / "ai" / "enhanced_element_finder_fixed.py",
            "imports_to_update": [
                {
                    "files": [base_dir / "automation" / "browser_controller.py"],
                    "old": "from ai.enhanced_element_finder import EnhancedElementFinder",
                    "new": "from ai.enhanced_element_finder_fixed import EnhancedElementFinderFixed"
                }
            ]
        },
        {
            "original": base_dir / "automation" / "browser_controller.py",
            "fixed": base_dir / "automation" / "browser_controller_fixed.py",
            "imports_to_update": [
                {
                    "files": [base_dir / "main.py"],
                    "old": "from automation import BrowserController",
                    "new": "from automation.browser_controller_fixed import BrowserControllerFixed as BrowserController"
                }
            ]
        }
    ]
    
    # Thực hiện tích hợp
    for integration in integrations:
        # Thay thế tệp
        if not replace_file(integration["original"], integration["fixed"]):
            logger.warning(f"Đã bỏ qua cập nhật import cho {integration['original']}")
            continue
            
        # Cập nhật câu lệnh import
        for import_update in integration.get("imports_to_update", []):
            for file_path in import_update["files"]:
                update_import_statement(file_path, import_update["old"], import_update["new"])
    
    logger.info("Đã hoàn thành tích hợp các lớp đã sửa lỗi")


def run_test():
    """Chạy bài kiểm tra để xác nhận các sửa lỗi đã hoạt động"""
    try:
        logger.info("Đang chạy bài kiểm tra...")
        
        # Thêm thư mục gốc vào sys.path
        base_dir = Path(__file__).parent
        sys.path.append(str(base_dir))
        
        # Import và chạy bài kiểm tra
        from tests.test_element_finder import main as run_element_finder_test
        run_element_finder_test()
        
        logger.info("Bài kiểm tra đã hoàn thành")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi chạy bài kiểm tra: {str(e)}")
        return False

def main():
    """Hàm chính để chạy tích hợp"""
    logger.info("=== BẮT ĐẦU QUÁ TRÌNH TÍCH HỢP ===")
    
    # Tích hợp các lớp đã sửa lỗi
    integrate_fixed_classes()
    
    # Chạy bài kiểm tra
    run_test()
    
    logger.info("=== HOÀN THÀNH QUÁ TRÌNH TÍCH HỢP ===")
    
if __name__ == "__main__":
    main()
