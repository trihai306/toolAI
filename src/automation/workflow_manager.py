"""
Workflow Manager Module
Quản lý việc ghi lại, lưu trữ và chạy các quy trình làm việc tự động
"""

import os
import yaml
import json
import time
from pathlib import Path
from datetime import datetime
import threading

class WorkflowManager:
    """Quản lý các quy trình làm việc tự động"""
    
    def __init__(self, browser_controller, workflows_dir="../workflows", data_dir="../data", debug=False):
        """Khởi tạo workflow manager với browser controller"""
        self.browser = browser_controller
        self.workflows_dir = Path(workflows_dir)
        self.data_dir = Path(data_dir)
        self.current_workflow = {}
        self.workflow_steps = []
        self.debug = debug
        self._workflow_threads = {}
        self._workflow_states = {}
        self._workflow_logs = {}
        
        # Đảm bảo các thư mục tồn tại
        os.makedirs(self.workflows_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
    
    def start_workflow(self, name, description=""):
        """Bắt đầu một quy trình làm việc mới"""
        self.current_workflow = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "steps": []
        }
        self.workflow_steps = []
        return True
    
    def record_step(self, action, params):
        """Ghi lại một bước trong quy trình làm việc hiện tại"""
        if not self.current_workflow:
            print("No active workflow to record step.")
            return False
            
        step = {
            "action": action,
            "params": params,
            "timestamp": datetime.now().isoformat()
        }
        self.workflow_steps.append(step)
        return True
    
    def save_workflow(self, custom_filename=None):
        """Lưu quy trình làm việc hiện tại vào file"""
        if not self.current_workflow:
            print("No active workflow to save.")
            return False
        
        # Cập nhật các bước trong workflow
        self.current_workflow["steps"] = self.workflow_steps
        
        # Tạo tên file dựa trên tên workflow
        if custom_filename:
            filename = custom_filename
        else:
            safe_name = self.current_workflow['name'].lower().replace(' ', '_')
            filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
        
        filepath = self.workflows_dir / filename
        
        # Lưu vào file YAML
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(self.current_workflow, f, default_flow_style=False, allow_unicode=True)
            return str(filepath)
        except Exception as e:
            print(f"Error saving workflow: {str(e)}")
            return False
    
    def load_workflow(self, filename):
        """Tải một quy trình làm việc từ file"""
        filepath = self.workflows_dir / filename
        
        if not filepath.exists():
            print(f"Workflow file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                workflow = yaml.safe_load(f)
            return workflow
        except Exception as e:
            print(f"Error loading workflow: {str(e)}")
            return None
    
    def list_workflows(self):
        """Liệt kê tất cả các quy trình làm việc đã lưu"""
        workflows = []
        
        if not self.workflows_dir.exists():
            return workflows
        
        for filepath in self.workflows_dir.glob("*.yaml"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    workflow = yaml.safe_load(f)
                workflows.append({
                    "filename": filepath.name,
                    "name": workflow.get("name", "Unknown"),
                    "description": workflow.get("description", ""),
                    "created_at": workflow.get("created_at", ""),
                    "steps_count": len(workflow.get("steps", []))
                })
            except Exception as e:
                print(f"Error loading workflow {filepath.name}: {str(e)}")
        
        return workflows
    
    def _get_log_file(self, workflow_name):
        log_path = self.data_dir / f"workflow_{workflow_name}.log"
        return open(log_path, "a", encoding="utf-8")

    def run_workflow(self, workflow, data=None, resume=False, max_retry=2):
        if not workflow:
            print("No workflow provided.")
            return False
        workflow_name = workflow.get('name', 'unknown')
        log_file = self._get_log_file(workflow_name)
        log_file.write(f"[START] {workflow_name} at {time.ctime()}\n")
        start_time = time.time()
        state_file = self.data_dir / f"state_{workflow_name}.json"
        step_idx = 0
        if resume and state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                step_idx = state.get("last_step", 0)
        steps = workflow["steps"]
        success = True
        for i, step in enumerate(steps):
            if i < step_idx:
                continue
            action = step["action"]
            params = step["params"].copy()
            if data:
                params = self._substitute_params(params, data)
            retry = 0
            while retry <= max_retry:
                try:
                    log_file.write(f"[STEP {i}] {action} {params}\n")
                    self._execute_step(action, params)
                    break
                except Exception as e:
                    log_file.write(f"[ERROR] Step {i} {action}: {e}\n")
                    retry += 1
                    if retry > max_retry:
                        log_file.write(f"[FAIL] Step {i} {action} failed after {max_retry} retries\n")
                        success = False
                        break
            # Lưu state sau mỗi bước
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump({"last_step": i+1}, f)
            if not success:
                break
            time.sleep(0.5)
        end_time = time.time()
        log_file.write(f"[END] {workflow_name} at {time.ctime()} - {'SUCCESS' if success else 'FAIL'} - Duration: {end_time-start_time:.2f}s\n")
        log_file.close()
        # Báo cáo tổng kết
        print(f"Workflow {workflow_name} {'thành công' if success else 'thất bại'} trong {end_time-start_time:.2f} giây. Xem log chi tiết tại {log_file.name}")
        return success

    def run_workflow_async(self, workflow, data=None, resume=False, max_retry=2):
        workflow_name = workflow.get('name', 'unknown')
        t = threading.Thread(target=self.run_workflow, args=(workflow, data, resume, max_retry), daemon=True)
        t.start()
        self._workflow_threads[workflow_name] = t
        return t

    def pause_workflow(self, workflow_name):
        # Đơn giản: chỉ lưu state, không thực sự pause thread (cần thiết kế thêm nếu muốn pause thực)
        print(f"[PAUSE] Workflow {workflow_name} đã lưu state, có thể resume sau.")

    def resume_workflow(self, workflow_name):
        workflow_file = self.workflows_dir / f"{workflow_name}.yaml"
        workflow = self.load_workflow(workflow_file.name)
        if workflow:
            self.run_workflow(workflow, resume=True)

    def stop_workflow(self, workflow_name):
        # Không thể dừng thread Python an toàn, chỉ cảnh báo
        print(f"[STOP] Không thể dừng thread workflow {workflow_name} an toàn. Hãy thiết kế lại nếu cần dừng thực sự.")
    
    def _substitute_params(self, params, data):
        """Thay thế các placeholder trong params bằng dữ liệu thực tế"""
        new_params = {}
        
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                data_key = value[2:-2].strip()
                if data_key in data:
                    new_params[key] = data[data_key]
                else:
                    new_params[key] = value  # Giữ nguyên nếu không tìm thấy
            else:
                new_params[key] = value
        
        return new_params
    
    def _execute_step(self, action, params):
        """Thực hiện một bước trong quy trình làm việc"""
        print(f"Executing: {action} with params {params}")
        
        if action == "navigate":
            self.browser.navigate_to(params["url"])
        elif action == "click":
            # Kiểm tra xem có mô tả phần tử không
            if "description" in params:
                self.browser.click_element(params["selector"], params["description"])
            else:
                self.browser.click_element(params["selector"])
        elif action == "type":
            # Kiểm tra xem có mô tả phần tử không
            if "description" in params:
                self.browser.type_text(params["selector"], params["text"], params["description"])
            else:
                self.browser.type_text(params["selector"], params["text"])
        elif action == "wait":
            # Kiểm tra xem có mô tả phần tử không
            if "description" in params:
                self.browser.wait_for_selector(params["selector"], params.get("timeout", 30000), params["description"])
            else:
                self.browser.wait_for_selector(params["selector"], params.get("timeout", 30000))
        elif action == "screenshot":
            self.browser.take_screenshot(params.get("filename"))
        elif action == "extract_text":
            # Kiểm tra xem có mô tả phần tử không
            if "description" in params:
                self.browser.extract_text(params["selector"], params["description"])
            else:
                self.browser.extract_text(params["selector"])
        elif action == "find_and_click":
            self.browser.interact_by_description(params["description"], action="click")
        elif action == "find_and_type":
            self.browser.interact_by_description(params["description"], action="type", value=params["text"])
        else:
            print(f"Unknown action: {action}")
            return False
        
        return True
