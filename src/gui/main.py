"""
Main entry point for the Browser Automation GUI
Uses PyWebView to create a desktop application
"""

import os
import sys
import time
import threading
import logging
import webview
import socket
from contextlib import closing

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Import app and server functions from src.gui.app
from src.gui.app import app, run_server, stop_browser

# Configure logging
try:
    from src.utils.logging_utils import configure_unicode_logging
    configure_unicode_logging("gui_main.log", logging.INFO)
except ImportError:
    logging.basicConfig(
        filename="gui_main.log",
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

logger = logging.getLogger("GUIMain")

def find_free_port():
    """Find a free port to use for the Flask server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def start_gui():
    """Start the GUI application"""
    try:
        # Find free port
        port = find_free_port()
        logger.info(f"Using port: {port}")
        
        # Start Flask server in a separate thread
        server_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=port, debug=False, threaded=True))
        server_thread.daemon = True
        server_thread.start()
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Create the window with the correct URL
        url = f"http://127.0.0.1:{port}"
        logger.info(f"Starting PyWebView with URL: {url}")
        
        webview.create_window(
            'Browser Automation Manager',
            url,
            width=1200,
            height=800,
            min_size=(800, 600),
            text_select=True
        )
        
        # Start the webview
        webview.start(debug=True)
        
    except Exception as e:
        logger.error(f"Error starting GUI: {str(e)}")
        print(f"Error starting GUI: {str(e)}")
    finally:
        # Clean up when the window is closed
        stop_browser()

def main():
    """Main entry point"""
    try:
        print("Starting Browser Automation GUI...")
        start_gui()
    except KeyboardInterrupt:
        print("Application terminated by user")
        stop_browser()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
