from flask import Blueprint, request, jsonify
from src.gui.models.browser_model import BrowserModel
from src.gui.controllers.browser_controller import BrowserAppController

browser_bp = Blueprint('browser', __name__)
model = BrowserModel()
controller = BrowserAppController(model)

@browser_bp.route('/api/start-browser', methods=['POST'])
def api_start_browser():
    data = request.json
    result = controller.start_browser(
        browser_type=data.get('browser_type', 'chromium'),
        use_existing=data.get('use_existing', False)
    )
    return jsonify(result)

@browser_bp.route('/api/stop-browser', methods=['POST'])
def api_stop_browser():
    result = controller.stop_browser()
    return jsonify(result)

@browser_bp.route('/api/run-command', methods=['POST'])
def api_run_command():
    command = request.json.get('command', '')
    result = controller.run_command(command)
    return jsonify(result)

@browser_bp.route('/api/command-status', methods=['GET'])
def api_command_status():
    return jsonify({
        "status": model.current_status,
        "output": model.process_output,
        "is_browser_running": model.is_browser_running
    })

@browser_bp.route('/api/command-history', methods=['GET'])
def api_command_history():
    history = model.sqlite.get_history()
    return jsonify({"history": [{"command": cmd, "created_at": ts} for cmd, ts in history]}) 