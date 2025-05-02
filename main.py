#!/usr/bin/env python
"""
Browser Automation Manager - Main Entry Point
Integrated entry point for Browser Automation Tool with GUI

Usage:
  python main.py               # Start with GUI
  python main.py --cli         # Start in CLI mode
  python main.py --install     # Install dependencies
"""

import os
import sys
import argparse
import logging
import traceback
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('browser_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

def run_gui_mode():
    """Run the application in GUI mode with integrated GUI"""
    try:
        logger.info("Starting Browser Automation Tool in GUI mode")
        print("Starting Browser Automation Tool with integrated GUI...")
        
        # Import GUI integration module
        from src.gui.main import main as start_gui
        
        # Start GUI
        start_gui()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        print("\nApplication terminated by user")
    except Exception as e:
        logger.error(f"Error in GUI mode: {str(e)}")
        print(f"\nError: {str(e)}")
        traceback.print_exc()

def run_cli_mode():
    """Run the application in CLI mode (original behavior)"""
    try:
        logger.info("Starting Browser Automation Tool in CLI mode")
        print("Starting Browser Automation Tool in CLI mode...")
        
        # Import the original main function
        from src.main import main as original_main
        
        # Run the original main function
        original_main()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        print("\nApplication terminated by user")
    except Exception as e:
        logger.error(f"Error in CLI mode: {str(e)}")
        print(f"\nError: {str(e)}")
        traceback.print_exc()

def run_install_dependencies():
    """Install all required dependencies"""
    import subprocess
    
    try:
        print("Installing dependencies...")
        
        # Install basic dependencies
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        # Install GUI-specific dependencies
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask==2.0.1", "werkzeug==2.0.1", "pywebview==4.2.2"])
        
        # Install Playwright
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        
        # Install browser binaries
        subprocess.check_call([sys.executable, "-m", "playwright", "install"])
        
        print("All dependencies installed successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
        
    return True

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Browser Automation Tool with GUI')
    
    # Add arguments
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode (without GUI)')
    parser.add_argument('--install', action='store_true', help='Install dependencies')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Run in appropriate mode
    if args.install:
        run_install_dependencies()
    elif args.cli:
        run_cli_mode()
    else:
        run_gui_mode()

if __name__ == "__main__":
    main()