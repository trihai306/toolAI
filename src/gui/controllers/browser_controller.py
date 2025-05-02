from src.gui.models.browser_model import BrowserModel
from src.automation.browser_controller import BrowserController
from src.main import BrowserAutomationAgent

class BrowserAppController:
    def __init__(self, model: BrowserModel):
        self.model = model

    def start_browser(self, browser_type="chromium", use_existing=False):
        from src.automation.browser_controller import BrowserController
        current_browser_controller = BrowserController.get_current_instance()
        if use_existing and current_browser_controller and current_browser_controller.browser is not None:
            try:
                if hasattr(current_browser_controller, 'page') and current_browser_controller.page:
                    _ = current_browser_controller.page.url
                    if self.model.agent is None:
                        self.model.agent = BrowserAutomationAgent(
                            browser_controller=current_browser_controller,
                            browser_type=browser_type,
                            headless=False,
                            human_like=True
                        )
                    else:
                        self.model.agent.browser = current_browser_controller
                    self.model.set_browser_running(True)
                    return {"success": True, "message": "Đã kết nối với trình duyệt hiện có"}
            except Exception:
                pass
        # Khởi động mới
        self.model.agent = BrowserAutomationAgent(
            browser_type=browser_type,
            headless=False,
            human_like=True
        )
        browser_config = {
            "headless": False,
            "user_agent": None,
            "viewport_size": {"width": 1280, "height": 800},
            "locale": "vi-VN"
        }
        if self.model.agent.browser.start_browser(**browser_config):
            self.model.set_browser_running(True)
            return {"success": True, "message": "Browser khởi động thành công"}
        else:
            self.model.set_browser_running(False)
            return {"success": False, "message": "Không thể khởi động browser"}

    def stop_browser(self):
        if self.model.agent:
            try:
                self.model.agent._cleanup()
                self.model.set_browser_running(False)
                return {"success": True, "message": "Browser stopped successfully"}
            except Exception as e:
                return {"success": False, "message": f"Error stopping browser: {str(e)}"}
        self.model.set_browser_running(False)
        return {"success": True, "message": "Browser was not running"}

    def run_command(self, command: str):
        if not self.model.is_browser_running or not self.model.agent or not hasattr(self.model.agent, 'browser'):
            start_result = self.start_browser()
            if not start_result.get("success"):
                return {"success": False, "message": "Browser is not running and could not be started"}
        self.model.set_status("running")
        self.model.clear_output()
        self.model.add_command(command)
        try:
            parsed = self.model.agent.parse_user_command_ai(command)
            if not parsed:
                self.model.set_status("error")
                return {"success": False, "message": "Could not parse command"}
            url = parsed.get("url")
            steps = parsed.get("steps", [])
            self.model.add_output(f"Navigating to {url}...")
            success = self.model.agent.navigate_to(url)
            if not success:
                self.model.set_status("error")
                return {"success": False, "message": f"Failed to navigate to {url}"}
            if steps:
                self.model.add_output("Executing workflow steps:")
                for idx, step in enumerate(steps, 1):
                    action = step.get('action', '')
                    selector = step.get('selector', '')
                    description = step.get('description', '') or step.get('text', '')
                    value = step.get('value', '')
                    step_description = f"Step {idx}: {action} {selector or description}"
                    self.model.add_output(step_description)
                    # (Có thể bổ sung thực thi từng bước ở đây)
            self.model.set_status("idle")
            return {"success": True, "message": "Command executed successfully"}
        except Exception as e:
            self.model.set_status("error")
            return {"success": False, "message": str(e)} 