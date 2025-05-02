import json
import logging

class WorkflowDynamic:
    def __init__(self, workflow_json, context=None, debug=False):
        if isinstance(workflow_json, str):
            self.workflow = json.loads(workflow_json)
        else:
            self.workflow = workflow_json
        self.context = context or {}
        self.debug = debug
        self.current_step = 0
        self.stopped = False

    def run(self):
        steps = self.workflow.get('steps', [])
        while self.current_step < len(steps) and not self.stopped:
            step = steps[self.current_step]
            if self.debug:
                logging.info(f"[WorkflowDynamic] Bước {self.current_step}: {step}")
            action = step.get('action')
            cond = step.get('if')
            if cond and not self._eval_condition(cond):
                self.current_step += 1
                continue
            self._execute_action(action, step)
            # Điều kiện nhảy bước, lặp lại, dừng
            if step.get('goto') is not None:
                self.current_step = step['goto']
            elif step.get('repeat'):
                pass  # Có thể lặp lại theo điều kiện
            else:
                self.current_step += 1

    def _eval_condition(self, cond):
        # Đánh giá điều kiện dựa trên context
        try:
            return eval(cond, {}, self.context)
        except Exception as e:
            if self.debug:
                logging.warning(f"[WorkflowDynamic] Lỗi điều kiện: {e}")
            return False

    def _execute_action(self, action, step):
        # Tùy chỉnh action, ví dụ click, nhập text, gọi hàm...
        if self.debug:
            logging.info(f"[WorkflowDynamic] Thực thi action: {action}")
        # Ví dụ: cập nhật context
        if 'set' in step:
            for k, v in step['set'].items():
                self.context[k] = v
        # ... thực thi action thực tế ở đây

    def stop(self):
        self.stopped = True

    def resume(self):
        self.stopped = False
        self.run() 