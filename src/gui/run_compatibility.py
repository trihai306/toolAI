"""
Compatibility version of the entry point for the GUI application
Uses fixed versions of Flask and Werkzeug
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

# Import app instead of app.py to avoid Werkzeug issues
from app_compatibility import app, run_server, stop_browser

# Configure basic logging
logging.basicConfig(
    filename="gui_compatibility.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("GUICompatibility")

def find_free_port():
    """Find a free port to use for the Flask server"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def start_gui():
    """Start the GUI application with compatibility fixes"""
    try:
        print("Starting Browser Automation GUI (Compatibility Mode)...")
        
        # Find free port
        port = find_free_port()
        logger.info(f"Using port: {port}")
        
        # Start Flask server in a separate thread
        server_thread = threading.Thread(target=lambda: app.run(host='127.0.0.1', port=port, debug=False, threaded=True))
        server_thread.daemon = True
        server_thread.start()
        
        # Give the server a moment to start
        print(f"Starting Flask server on port {port}...")
        time.sleep(2)
        
        # Create the window with the correct URL
        url = f"http://127.0.0.1:{port}"
        print(f"Opening PyWebView window with URL: {url}")
        
        # Try to create a window with fallbacks for compatibility
        try:
            webview.create_window(
                'Browser Automation Manager',
                url,
                width=1200,
                height=800,
                min_size=(800, 600)
            )
            webview.start(debug=True)
        except Exception as e:
            logger.error(f"Error starting PyWebView: {str(e)}")
            print(f"Error starting PyWebView: {str(e)}")
            print("Please open this URL in your browser manually: " + url)
            
            # Keep the server running even if PyWebView fails
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Server stopped by user")
        
    except Exception as e:
        logger.error(f"Error starting GUI: {str(e)}")
        print(f"Error starting GUI: {str(e)}")
    finally:
        # Clean up when the window is closed
        stop_browser()

if __name__ == "__main__":
    try:
        start_gui()
    except KeyboardInterrupt:
        print("Application terminated by user")
        stop_browser()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        print(f"Error: {str(e)}")
