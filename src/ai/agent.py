import os
import time
from openai import OpenAI
from dotenv import load_dotenv

# Đảm bảo biến môi trường được tải
load_dotenv()

class AIAgent:
    """
    Agent trung tâm: nhận task, phân tích mục tiêu, chia nhỏ thành các bước thao tác DOM,
    giao tiếp với LLM, quản lý workflow/memory, tương tác với BrowserController.
    """
    def __init__(self, browser_controller, llm_model="gpt-4o", debug=False):
        self.browser = browser_controller
        self.llm_model = llm_model
        self.debug = debug
        self.memory = []  # Lưu các workflow thành công, selector tốt nhất
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.openai_api_key)

    def run_task(self, task, context=None):
        """
        Nhận task (mục tiêu), phân tích, chia nhỏ thành các bước, hỏi xác nhận người dùng trước khi thực thi.
        """
        if self.debug:
            print(f"[AIAgent] Nhận task: {task}")
        # 1. Lấy trạng thái DOM hiện tại
        html = self.browser.page.content() if self.browser.page else ""
        # 2. Sinh prompt cho LLM để phân tích task và sinh các bước thao tác
        while True:
            prompt = self._build_prompt(task, html, context)
            steps = self._ask_llm_for_steps(prompt)
            if self.debug:
                print(f"[AIAgent] Các bước sinh ra: {steps}")
            # 3. Hiển thị các bước cho người dùng xác nhận
            print("\n==== Các bước AI phân tích sẽ thực hiện ====")
            for idx, step in enumerate(steps, 1):
                print(f"Bước {idx}: {step}")
            print("==========================================")
            confirm = input("Các bước trên đã đúng ý bạn chưa? (y/n/mô tả lại): ").strip().lower()
            if confirm == 'y' or confirm == 'yes':
                break
            elif confirm == 'n' or confirm == 'no' or confirm == 'mô tả lại':
                task = input("Hãy mô tả lại ý định hoặc bổ sung chi tiết mong muốn: ")
                continue
            else:
                print("Vui lòng nhập 'y' để xác nhận hoặc 'n' để mô tả lại.")
        # 4. Thực thi từng bước, lưu lại kết quả
        results = []
        for step in steps:
            action = step.get("action")
            selector = step.get("selector")
            value = step.get("value")
            description = step.get("description")
            if self.debug:
                print(f"[AIAgent] Thực thi: {action} - {selector or description}")
            success = self.browser._do_step(step)
            results.append({"step": step, "success": success})
            if not success:
                if self.debug:
                    print(f"[AIAgent] Thất bại ở bước: {step}")
                break
        # 5. Lưu workflow thành công vào memory
        if all(r["success"] for r in results):
            self.memory.append({"task": task, "steps": steps})
        return results

    def _build_prompt(self, task, html, context=None):
        """
        Xây dựng prompt cho LLM để phân tích task và sinh các bước thao tác DOM.
        """
        prompt = f"""
Bạn là một AI agent chuyên tự động hóa trình duyệt.
Mục tiêu: {task}
{f'Bối cảnh: {context}' if context else ''}
Dưới đây là HTML hiện tại của trang:
```html
{html[:12000]}
```
Hãy phân tích và trả về danh sách các bước thao tác DOM (click, type, extract, ...), mỗi bước là một dict Python với các trường: action, selector (hoặc description), value (nếu cần).
Chỉ trả về list các dict, không giải thích.
"""
        return prompt

    def _ask_llm_for_steps(self, prompt):
        """
        Gửi prompt lên LLM để sinh các bước thao tác DOM.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.2
            )
            content = response.choices[0].message.content
            # Cố gắng parse list dict từ content
            import ast
            try:
                steps = ast.literal_eval(content)
                if isinstance(steps, list):
                    return steps
            except Exception:
                pass
            # Nếu không parse được, trả về mẫu đơn giản
            return []
        except Exception as e:
            if self.debug:
                print(f"[AIAgent] Lỗi khi hỏi LLM: {e}")
            return [] 