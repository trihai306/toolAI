from src.gui.models.sqlite_model import SQLiteModel

class BrowserModel:
    def __init__(self):
        self.is_browser_running = False
        self.current_status = "idle"
        self.process_output = []
        self.command_history = []
        self.agent = None
        self.sqlite = SQLiteModel()

    def set_browser_running(self, running: bool):
        self.is_browser_running = running

    def add_command(self, command: str):
        self.command_history.append(command)
        self.sqlite.add_command(command)

    def set_status(self, status: str):
        self.current_status = status

    def add_output(self, message: str):
        self.process_output.append(message)

    def clear_output(self):
        self.process_output = [] 