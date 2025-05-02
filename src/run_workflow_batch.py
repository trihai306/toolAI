"""
Workflow Batch Runner
Chạy một workflow với nhiều bộ dữ liệu khác nhau từ file JSON
"""

import os
import sys
import json
import time
from pathlib import Path

from automation import BrowserController, WorkflowManager
from utils import UserInteraction

def run_workflow_with_data_file(workflow_filename, data_filename):
    """
    Run a workflow with data from a JSON file
    """
    # Khởi tạo các thành phần cần thiết
    browser = BrowserController()
    workflow = WorkflowManager(browser)
    ui = UserInteraction()
    
    # Đường dẫn đến các file
    workflows_dir = Path("../workflows")
    data_dir = Path("../data")
    
    workflow_path = workflows_dir / workflow_filename
    data_path = data_dir / data_filename
    
    # Kiểm tra file tồn tại
    if not workflow_path.exists():
        print(f"Workflow file not found: {workflow_path}")
        return False
    
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        return False
    
    # Tải workflow
    loaded_workflow = workflow.load_workflow(workflow_filename)
    if not loaded_workflow:
        print(f"Error loading workflow from file: {workflow_filename}")
        return False
    
    # Tải dữ liệu
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return False
    
    # Khởi động trình duyệt
    print("Starting browser...")
    browser.start_browser(headless=False)
    print("Browser is ready!")
    
    try:
        # Chạy workflow với từng dữ liệu
        i = 0
        while i < len(data_list):
            data = data_list[i]
            print(f"\nRunning workflow {i+1}/{len(data_list)} with data: {data}")
            
            # Cho phép xem trước và xác nhận trước khi chạy
            if i > 0:
                continue_run = ui.ask_yes_no_question("Continue with next data item?")
                if not continue_run:
                    if ui.ask_yes_no_question("Do you want to stop the batch run completely?"):
                        print("Stopping batch run.")
                        break
                    else:
                        print("Skipping this data and moving to the next one.")
                        i += 1
                        continue
            
            # Xác nhận trước khi chạy
            print(f"Preparing to run workflow '{loaded_workflow['name']}' with data: {data}")
            ready_to_run = ui.ask_yes_no_question("Are you ready to run this workflow?")
            if not ready_to_run:
                skip_data = ui.ask_yes_no_question("Do you want to skip this data?")
                if skip_data:
                    print(f"Skipping data: {data}")
                    i += 1
                    continue
                else:
                    print("Returning to main menu.")
                    break
            
            # Chạy workflow với dữ liệu hiện tại
            print(f"Running workflow '{loaded_workflow['name']}'...")
            workflow.run_workflow(loaded_workflow, data)
            
            # Phản hồi sau khi hoàn thành
            print(f"Workflow '{loaded_workflow['name']}' completed!")
            
            if i == len(data_list) - 1:  # Nếu là mục cuối cùng
                if ui.ask_yes_no_question("All data has been processed. Do you want to run again from the beginning?"):
                    i = 0  # Reset về đầu
                    continue
                else:
                    print("Completed all workflow runs.")
                    break
            
            # Hỏi có muốn tiếp tục không
            if ui.ask_yes_no_question("Continue with next data item?"):
                i += 1  # Chuyển đến dữ liệu tiếp theo
            else:
                # Hỏi có muốn kết thúc không
                if ui.ask_yes_no_question("Do you want to end the session?"):
                    print("Ending session.")
                    break
                else:
                    # Hỏi có muốn quay lại mục trước không
                    if i > 0 and ui.ask_yes_no_question("Do you want to go back to the previous data?"):
                        i -= 1
                    # Ngược lại giữ nguyên vị trí hiện tại và hỏi lại
        
        # Sau khi hoàn thành, hỏi người dùng có muốn giữ trình duyệt mở không
        keep_browser = ui.ask_yes_no_question("Do you want to keep the browser open for other tasks?")
        if not keep_browser:
            print("Closing browser...")
            browser.close_browser()
            print("Browser closed.")
        else:
            print("Browser remains open. You can use it for other tasks.")
            
    except KeyboardInterrupt:
        print("\nInterrupt detected (Ctrl+C). Stopping workflow...")
        keep_browser_open = ui.ask_yes_no_question("Do you want to keep the browser open?")
        if not keep_browser_open:
            browser.close_browser()
    except Exception as e:
        print(f"\nError running workflow: {str(e)}")
        browser.close_browser()
    
    return True


def main():
    """Main entry point for batch runner"""
    if len(sys.argv) < 3:
        print("Usage: python run_workflow_batch.py <workflow_filename> <data_filename>")
        print("Example: python run_workflow_batch.py google_search_example.yaml search_terms.json")
        return
    
    workflow_filename = sys.argv[1]
    data_filename = sys.argv[2]
    
    run_workflow_with_data_file(workflow_filename, data_filename)


if __name__ == "__main__":
    main()
