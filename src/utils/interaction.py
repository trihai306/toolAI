"""
User Interaction Module
Cung cấp các tiện ích để tương tác với người dùng
"""

class UserInteraction:
    """Cung cấp các phương thức để tương tác với người dùng"""
    
    @staticmethod
    def ask_yes_no_question(question):
        """Hỏi người dùng câu hỏi yes/no và trả về kết quả"""
        while True:
            response = input(f"{question} (yes/no): ").strip().lower()
            if response in ["yes", "y"]:
                return True
            elif response in ["no", "n"]:
                return False
            else:
                print("Please answer 'yes' or 'no'.")
    
    @staticmethod
    def get_user_input(prompt="What would you like to do next? "):
        """Lấy dữ liệu nhập từ người dùng với gợi ý nhất định"""
        return input(prompt).strip()
    
    @staticmethod
    def display_welcome_message():
        """Hiển thị thông báo chào mừng khi khởi động ứng dụng"""
        print("=== Browser Automation Agent ===")
        print("Browser Automation Agent is ready!")
        print("Type 'exit' to quit")
    
    @staticmethod
    def display_assistant_message(message):
        """Hiển thị thông báo từ trợ lý"""
        print(f"\nAssistant: {message}")
    
    @staticmethod
    def display_processing_message():
        """Hiển thị thông báo đang xử lý"""
        print("\nProcessing your request...")
    
    @staticmethod
    def display_subtask_message(subtask, index, total):
        """Hiển thị thông báo về subtask đang được thực hiện"""
        print(f"\n▶️ Bước {index}/{total}: {subtask}")
        
    @staticmethod
    def display_subtask_completion(subtask, index, total, success=True):
        """Hiển thị thông báo về subtask đã hoàn thành"""
        status = "✅" if success else "❌"
        print(f"  {status} Bước {index}/{total} hoàn thành: {subtask}")
    
    @staticmethod
    def display_completion_message():
        """Hiển thị thông báo khi hoàn thành tác vụ"""
        print("\nTask completed! You can continue with another request or type 'exit' to end.")
    
    @staticmethod
    def display_error_message(error):
        """Hiển thị thông báo lỗi"""
        print(f"\nError: {error}")
