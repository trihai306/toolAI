import threading
from .browser_controller import BrowserController

class SessionManager:
    def __init__(self, debug=False):
        self.sessions = {}
        self.lock = threading.Lock()
        self.debug = debug

    def create_session(self, session_id, **kwargs):
        with self.lock:
            if session_id in self.sessions:
                raise Exception(f"Session {session_id} đã tồn tại")
            self.sessions[session_id] = BrowserController(debug=self.debug, **kwargs)
            if self.debug:
                print(f"[SessionManager] Tạo session {session_id}")
        return self.sessions[session_id]

    def close_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                try:
                    self.sessions[session_id].close()
                except Exception:
                    pass
                del self.sessions[session_id]
                if self.debug:
                    print(f"[SessionManager] Đã đóng session {session_id}")

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def list_sessions(self):
        return list(self.sessions.keys())

    def switch_session(self, session_id):
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} không tồn tại")
        return self.sessions[session_id]

    def get_status(self):
        return {sid: str(sess) for sid, sess in self.sessions.items()} 