"""
Simple Tkinter GUI for Browser Automation Agent
This standalone application doesn't require Flask or PyWebView
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import time

# Add the parent directory to sys.path so we can import from src
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

class SimpleBrowserAutomationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Browser Automation Manager - Simple Mode")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)
        
        # Variables
        self.browser_running = False
        self.command_history = []
        self.process = None
        
        # Configure style
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5, font=('Segoe UI', 9))
        self.style.configure("TLabel", font=('Segoe UI', 9))
        self.style.configure("TFrame", background="#f0f0f0")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a notebook with tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Browser Control
        self.browser_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.browser_tab, text="Điều khiển trình duyệt")
        self._setup_browser_tab()
        
        # Tab 2: Command History
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="Lịch sử lệnh")
        self._setup_history_tab()
        
        # Tab 3: Settings
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Cài đặt")
        self._setup_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind events
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Try import Browser Automation Agent
        try:
            from src.main import BrowserAutomationAgent
            self.browser_automation_available = True
            self.status_var.set("Đã tải thành công module BrowserAutomationAgent")
        except ImportError as e:
            self.browser_automation_available = False
            self.status_var.set("Không thể tải module BrowserAutomationAgent. Chạy dưới chế độ hạn chế.")
            messagebox.showwarning(
                "Lỗi import module", 
                f"Không thể tải module BrowserAutomationAgent: {str(e)}\n\n"
                "Ứng dụng sẽ chạy ở chế độ hạn chế, chỉ có thể khởi động trình duyệt."
            )
    
    def _setup_browser_tab(self):
        """Set up the browser control tab"""
        # Top frame for browser control
        top_frame = ttk.Frame(self.browser_tab)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Browser type selection
        ttk.Label(top_frame, text="Loại trình duyệt:").pack(side=tk.LEFT, padx=5, pady=5)
        self.browser_type = tk.StringVar(value="chromium")
        browser_combo = ttk.Combobox(top_frame, textvariable=self.browser_type, width=15)
        browser_combo['values'] = ('chromium', 'firefox', 'webkit')
        browser_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Headless mode checkbox
        self.headless_var = tk.BooleanVar(value=False)
        headless_check = ttk.Checkbutton(top_frame, text="Chế độ headless", variable=self.headless_var)
        headless_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Start/Stop button
        self.browser_button = ttk.Button(top_frame, text="Khởi động trình duyệt", command=self.toggle_browser)
        self.browser_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Screenshot button
        self.screenshot_button = ttk.Button(top_frame, text="Chụp màn hình", command=self.take_screenshot, state=tk.DISABLED)
        self.screenshot_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Middle frame for command input
        mid_frame = ttk.Frame(self.browser_tab)
        mid_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mid_frame, text="Nhập lệnh:").pack(anchor=tk.W, padx=5, pady=2)
        
        # Command input
        self.command_input = scrolledtext.ScrolledText(mid_frame, height=4)
        self.command_input.pack(fill=tk.X, padx=5, pady=5)
        
        # Run command button
        button_frame = ttk.Frame(mid_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status indicator
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(side=tk.LEFT)
        
        self.status_indicator = ttk.Label(status_frame, text="⚫ Trình duyệt: Chưa chạy", foreground="red")
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        
        # Run button
        self.run_button = ttk.Button(button_frame, text="Chạy lệnh", command=self.run_command, state=tk.DISABLED)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        # Bottom frame for output
        bottom_frame = ttk.LabelFrame(self.browser_tab, text="Kết quả thực thi")
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(bottom_frame)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.output_text.config(state=tk.DISABLED)
    
    def _setup_history_tab(self):
        """Set up the command history tab"""
        # History frame
        history_frame = ttk.Frame(self.history_tab)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # History listbox with scrollbar
        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(history_frame, yscrollcommand=scrollbar.set)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar.config(command=self.history_listbox.yview)
        
        # Button frame
        button_frame = ttk.Frame(self.history_tab)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Use selected command button
        use_button = ttk.Button(button_frame, text="Sử dụng lệnh đã chọn", command=self.use_selected_command)
        use_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Clear history button
        clear_button = ttk.Button(button_frame, text="Xóa lịch sử", command=self.clear_history)
        clear_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Double-click binding
        self.history_listbox.bind("<Double-1>", lambda event: self.use_selected_command())
    
    def _setup_settings_tab(self):
        """Set up the settings tab"""
        # Settings frame
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Cài đặt chung")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Web Server settings
        server_frame = ttk.Frame(settings_frame)
        server_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(server_frame, text="Port máy chủ web:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_var = tk.StringVar(value="5000")
        port_entry = ttk.Entry(server_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Debugging options
        debug_frame = ttk.LabelFrame(self.settings_tab, text="Gỡ lỗi")
        debug_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Enable verbose logging
        self.verbose_logging = tk.BooleanVar(value=False)
        verbose_check = ttk.Checkbutton(debug_frame, text="Ghi log chi tiết", variable=self.verbose_logging)
        verbose_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Show browser console
        self.show_console = tk.BooleanVar(value=False)
        console_check = ttk.Checkbutton(debug_frame, text="Hiển thị console trình duyệt", variable=self.show_console)
        console_check.pack(anchor=tk.W, padx=5, pady=5)
        
        # Save settings button
        save_button = ttk.Button(self.settings_tab, text="Lưu cài đặt", command=self.save_settings)
        save_button.pack(side=tk.RIGHT, padx=5, pady=10)
        
        # Run compatibility check button
        check_button = ttk.Button(self.settings_tab, text="Kiểm tra tương thích", command=self.run_compatibility_check)
        check_button.pack(side=tk.LEFT, padx=5, pady=10)
    
    def log_output(self, message):
        """Add message to output text area"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
    
    def toggle_browser(self):
        """Start or stop the browser"""
        if not self.browser_running:
            self.start_browser()
        else:
            self.stop_browser()
    
    def start_browser(self):
        """Start the browser"""
        # Disable button while starting
        self.browser_button.config(state=tk.DISABLED)
        self.status_var.set("Đang khởi động trình duyệt...")
        
        # Clear output
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        # Get settings
        browser_type = self.browser_type.get()
        headless = self.headless_var.get()
        
        # Start in a separate thread
        threading.Thread(target=self._start_browser_thread, args=(browser_type, headless), daemon=True).start()
    
    def _start_browser_thread(self, browser_type, headless):
        """Thread function to start the browser"""
        try:
            # Try direct import
            if self.browser_automation_available:
                from src.main import BrowserAutomationAgent
                self.log_output(f"Khởi tạo BrowserAutomationAgent ({browser_type}, headless={headless})...")
                
                # Create agent
                agent = BrowserAutomationAgent(
                    browser_type=browser_type,
                    headless=headless,
                    human_like=False
                )
                
                # Configure browser
                browser_config = {
                    "headless": headless,
                    "user_agent": None,
                    "viewport_size": {"width": 1280, "height": 800},
                    "locale": "vi-VN"
                }
                
                # Start browser
                if agent.browser.start_browser(**browser_config):
                    self.agent = agent
                    self.browser_running = True
                    self.log_output("Trình duyệt đã khởi động thành công!")
                    
                    # Update UI
                    self.root.after(0, self._update_ui_browser_started)
                else:
                    self.log_output("Không thể khởi động trình duyệt!")
                    messagebox.showerror("Lỗi", "Không thể khởi động trình duyệt!")
                    self.root.after(0, lambda: self.browser_button.config(state=tk.NORMAL))
            else:
                # Fall back to command-line
                self.log_output("Khởi động trình duyệt qua command line...")
                
                # Prepare command
                python_exe = sys.executable
                headless_arg = "--headless" if headless else ""
                cmd = [python_exe, "src/main.py", "--browser", browser_type]
                
                if headless:
                    cmd.append("--headless")
                
                # Run process
                self.process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    text=True, 
                    bufsize=1,
                    cwd=current_dir
                )
                
                # Read output
                self.browser_running = True
                self.log_output(f"Đã bắt đầu quá trình với PID {self.process.pid}")
                
                for line in iter(self.process.stdout.readline, ''):
                    if line:
                        self.log_output(line.rstrip())
                
                # When process ends
                self.process.stdout.close()
                self.process.wait()
                
                if self.process.returncode != 0:
                    self.log_output(f"Quá trình kết thúc với mã lỗi: {self.process.returncode}")
                    self.browser_running = False
                    self.root.after(0, lambda: self.browser_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.status_indicator.config(text="⚫ Trình duyệt: Chưa chạy", foreground="red"))
                else:
                    self.log_output("Trình duyệt đã tắt")
                    self.browser_running = False
                    self.root.after(0, lambda: self.browser_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.status_indicator.config(text="⚫ Trình duyệt: Chưa chạy", foreground="red"))
                
                self.root.after(0, lambda: self.browser_button.config(text="Khởi động trình duyệt"))
                self.root.after(0, lambda: self.screenshot_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.run_button.config(state=tk.DISABLED))
                
        except Exception as e:
            self.log_output(f"Lỗi khi khởi động trình duyệt: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi khởi động trình duyệt: {str(e)}")
            self.root.after(0, lambda: self.browser_button.config(state=tk.NORMAL))
            self.browser_running = False
    
    def _update_ui_browser_started(self):
        """Update UI after browser has started"""
        self.browser_button.config(text="Dừng trình duyệt", state=tk.NORMAL)
        self.screenshot_button.config(state=tk.NORMAL)
        self.run_button.config(state=tk.NORMAL)
        self.status_indicator.config(text="⚫ Trình duyệt: Đang chạy", foreground="green")
        self.status_var.set("Trình duyệt đang chạy")
    
    def stop_browser(self):
        """Stop the browser"""
        if not self.browser_running:
            return
        
        self.browser_button.config(state=tk.DISABLED)
        self.status_var.set("Đang dừng trình duyệt...")
        
        # Stop in a separate thread
        threading.Thread(target=self._stop_browser_thread, daemon=True).start()
    
    def _stop_browser_thread(self):
        """Thread function to stop the browser"""
        try:
            if hasattr(self, 'agent'):
                self.log_output("Dừng trình duyệt...")
                self.agent._cleanup()
                self.browser_running = False
                delattr(self, 'agent')
                self.log_output("Trình duyệt đã dừng thành công!")
            elif hasattr(self, 'process') and self.process:
                self.log_output("Dừng quá trình trình duyệt...")
                self.process.terminate()
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
                self.browser_running = False
                self.log_output("Quá trình trình duyệt đã bị kết thúc!")
            
            # Update UI
            self.root.after(0, self._update_ui_browser_stopped)
            
        except Exception as e:
            self.log_output(f"Lỗi khi dừng trình duyệt: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi dừng trình duyệt: {str(e)}")
            self.root.after(0, lambda: self.browser_button.config(state=tk.NORMAL))
    
    def _update_ui_browser_stopped(self):
        """Update UI after browser has stopped"""
        self.browser_button.config(text="Khởi động trình duyệt", state=tk.NORMAL)
        self.screenshot_button.config(state=tk.DISABLED)
        self.run_button.config(state=tk.DISABLED)
        self.status_indicator.config(text="⚫ Trình duyệt: Chưa chạy", foreground="red")
        self.status_var.set("Trình duyệt đã dừng")
    
    def take_screenshot(self):
        """Take a screenshot of the browser"""
        if not self.browser_running or not hasattr(self, 'agent'):
            messagebox.showinfo("Thông báo", "Trình duyệt chưa chạy!")
            return
        
        self.screenshot_button.config(state=tk.DISABLED)
        self.status_var.set("Đang chụp màn hình...")
        
        # Take screenshot in a separate thread
        threading.Thread(target=self._take_screenshot_thread, daemon=True).start()
    
    def _take_screenshot_thread(self):
        """Thread function to take a screenshot"""
        try:
            self.log_output("Đang chụp màn hình...")
            screenshot_path = self.agent.browser.take_screenshot()
            
            if screenshot_path:
                self.log_output(f"Đã chụp ảnh màn hình: {screenshot_path}")
                
                # Try to open the image
                try:
                    if sys.platform == 'win32':
                        os.startfile(screenshot_path)
                    else:
                        import subprocess
                        subprocess.call(['xdg-open', screenshot_path])
                except Exception as e:
                    self.log_output(f"Không thể mở ảnh: {str(e)}")
            else:
                self.log_output("Không thể chụp ảnh màn hình!")
        except Exception as e:
            self.log_output(f"Lỗi khi chụp màn hình: {str(e)}")
            messagebox.showerror("Lỗi", f"Lỗi khi chụp màn hình: {str(e)}")
        finally:
            self.root.after(0, lambda: self.screenshot_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set("Sẵn sàng"))
    
    def run_command(self):
        """Run a command in the browser"""
        if not self.browser_running or not hasattr(self, 'agent'):
            messagebox.showinfo("Thông báo", "Trình duyệt chưa chạy!")
            return
        
        command = self.command_input.get(1.0, tk.END).strip()
        if not command:
            messagebox.showinfo("Thông báo", "Vui lòng nhập lệnh!")
            return
        
        # Disable UI while running
        self.run_button.config(state=tk.DISABLED)
        self.command_input.config(state=tk.DISABLED)
        self.status_var.set("Đang thực thi lệnh...")
        
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
            self.history_listbox.insert(tk.END, command)
        
        # Clear output
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state=tk.DISABLED)
        
        # Run command in a separate thread
        threading.Thread(target=self._run_command_thread, args=(command,), daemon=True).start()
    
    def _run_command_thread(self, command):
        """Thread function to run a command"""
        try:
            self.log_output(f"Thực thi lệnh: {command}")
            
            # Parse command
            if hasattr(self.agent, 'parse_user_command_ai'):
                self.log_output("Đang phân tích lệnh...")
                parsed = self.agent.parse_user_command_ai(command)
                
                if not parsed:
                    self.log_output("Không thể phân tích lệnh. Vui lòng thử lại!")
                    self.root.after(0, self._update_ui_command_finished)
                    return
                
                url = parsed.get("url")
                steps = parsed.get("steps", [])
                
                # Navigate to URL
                self.log_output(f"Đang điều hướng đến {url}...")
                success = self.agent.navigate_to(url)
                
                if success:
                    self.log_output(f"Đã điều hướng thành công đến {url}")
                    time.sleep(2)  # Allow page to load
                else:
                    self.log_output(f"Không thể điều hướng đến {url}")
                    self.root.after(0, self._update_ui_command_finished)
                    return
                
                # Execute steps
                if steps:
                    self.log_output("Thực thi các bước workflow:")
                    
                    for idx, step in enumerate(steps, 1):
                        action = step.get('action', '')
                        selector = step.get('selector', '')
                        description = step.get('description', '') or step.get('text', '')
                        value = step.get('value', '')
                        
                        step_description = f"Bước {idx}: "
                        if action == 'type':
                            step_description += f"Nhập '{value}' vào {selector or description}"
                        elif action == 'click':
                            step_description += f"Click vào {selector or description}"
                        elif action == 'find_and_click':
                            step_description += f"Tìm và click vào '{description}'"
                        elif action == 'scroll':
                            step_description += f"Cuộn trang {step.get('direction', 'down')}"
                        elif action == 'wait':
                            step_description += f"Đợi {step.get('time', 1.0)} giây"
                        else:
                            step_description += f"{action} | {step}"
                        
                        self.log_output(step_description)
                    
                    # Try to execute workflow
                    try:
                        if hasattr(self.agent.browser, 'execute_workflow'):
                            success = self.agent.browser.execute_workflow(steps)
                            if success:
                                self.log_output("Tất cả các bước đã được thực thi thành công!")
                            else:
                                self.log_output("Lỗi khi thực thi các bước workflow!")
                        else:
                            # Manual execution
                            self.log_output("Không tìm thấy phương thức execute_workflow, thực thi thủ công...")
                            
                            for step in steps:
                                action = step.get('action', '').lower()
                                
                                if action == 'click' and 'selector' in step:
                                    self.agent.browser.page.click(step['selector'])
                                    self.log_output(f"Đã click vào {step['selector']}")
                                
                                elif action == 'type' and 'selector' in step and 'value' in step:
                                    self.agent.browser.page.fill(step['selector'], step['value'])
                                    self.log_output(f"Đã nhập '{step['value']}' vào {step['selector']}")
                                
                                elif action == 'wait':
                                    wait_time = float(step.get('time', 1.0))
                                    self.log_output(f"Đợi {wait_time} giây...")
                                    time.sleep(wait_time)
                            
                            self.log_output("Hoàn thành thực thi thủ công!")
                    
                    except Exception as e:
                        self.log_output(f"Lỗi khi thực thi workflow: {str(e)}")
                else:
                    self.log_output("Không có bước nào để thực thi!")
            else:
                self.log_output("Không tìm thấy phương thức parse_user_command_ai!")
        
        except Exception as e:
            self.log_output(f"Lỗi khi thực thi lệnh: {str(e)}")
        
        finally:
            self.root.after(0, self._update_ui_command_finished)
    
    def _update_ui_command_finished(self):
        """Update UI after command has finished"""
        self.run_button.config(state=tk.NORMAL)
        self.command_input.config(state=tk.NORMAL)
        self.status_var.set("Sẵn sàng")
    
    def use_selected_command(self):
        """Use the selected command from history"""
        selected = self.history_listbox.curselection()
        if not selected:
            return
        
        command = self.history_listbox.get(selected[0])
        self.command_input.delete(1.0, tk.END)
        self.command_input.insert(tk.END, command)
        
        # Switch to browser tab
        self.notebook.select(0)
    
    def clear_history(self):
        """Clear command history"""
        if not self.command_history:
            return
        
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa toàn bộ lịch sử lệnh?"):
            self.command_history.clear()
            self.history_listbox.delete(0, tk.END)
    
    def save_settings(self):
        """Save settings"""
        # In a real application, you would save to a config file
        messagebox.showinfo("Thông báo", "Đã lưu cài đặt!")
    
    def run_compatibility_check(self):
        """Run a compatibility check"""
        self.log_output("Đang kiểm tra tương thích...")
        
        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        self.log_output(f"Python version: {python_version}")
        
        # Check for required modules
        required_modules = ["tkinter", "threading", "subprocess"]
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
                self.log_output(f"✓ Module {module} đã được cài đặt")
            except ImportError:
                self.log_output(f"✗ Thiếu module {module}")
                missing_modules.append(module)
        
        # Check for optional modules
        optional_modules = ["flask", "webview", "playwright", "openai"]
        
        for module in optional_modules:
            try:
                __import__(module)
                self.log_output(f"✓ Module tùy chọn {module} đã được cài đặt")
            except ImportError:
                self.log_output(f"⚠ Module tùy chọn {module} chưa được cài đặt")
        
        # Check for src module
        try:
            import src
            self.log_output("✓ Module src đã được tìm thấy")
        except ImportError:
            self.log_output("✗ Không thể import module src")
            missing_modules.append("src")
        
        # Display result
        if missing_modules:
            messagebox.showwarning(
                "Kiểm tra tương thích", 
                f"Thiếu các module: {', '.join(missing_modules)}.\n\n"
                "Một số chức năng có thể không hoạt động đúng."
            )
        else:
            messagebox.showinfo(
                "Kiểm tra tương thích", 
                "Tất cả các module cần thiết đã được cài đặt.\n\n"
                "Hệ thống có thể hoạt động đúng."
            )
    
    def on_close(self):
        """Handle window close event"""
        if self.browser_running:
            if messagebox.askyesno("Xác nhận", "Trình duyệt đang chạy. Bạn có muốn thoát không?"):
                self.stop_browser()
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = SimpleBrowserAutomationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
