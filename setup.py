#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
from setuptools import setup, find_packages, Command

# Current directory path
HERE = os.path.abspath(os.path.dirname(__file__))

# Read file content
def read_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# Read requirements.txt
def read_requirements():
    with open(os.path.join(HERE, "requirements.txt"), "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# Create .env file from .env.example if it doesn't exist
def create_env_file():
    env_file = os.path.join(HERE, ".env")
    env_example_file = os.path.join(HERE, ".env.example")
    
    if not os.path.exists(env_file) and os.path.exists(env_example_file):
        shutil.copy2(env_example_file, env_file)
        print("Created .env file from .env.example")
        print("Please update OPENAI_API_KEY in the .env file")

# Create directories if they don't exist
def create_directories():
    for directory in ["workflows", "data"]:
        dir_path = os.path.join(HERE, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Created directory {directory}")

class InstallPlaywrightCommand(Command):
    """Install Playwright drivers"""
    description = "Install Playwright drivers"
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        print("Installing Playwright drivers...")
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
            print("Successfully installed Playwright drivers")
        except subprocess.CalledProcessError:
            print("Error installing Playwright drivers")
            print("Please try manual installation: python -m playwright install")

class RunAgentCommand(Command):
    """Start Browser Automation Agent"""
    description = "Start Browser Automation Agent"
    user_options = []
    
    def initialize_options(self):
        pass
    
    def finalize_options(self):
        pass
    
    def run(self):
        print("Starting Browser Automation Agent...")
        try:
            subprocess.run([sys.executable, os.path.join(HERE, "src", "main.py")], check=True)
        except subprocess.CalledProcessError:
            print("Error starting Agent")
        except KeyboardInterrupt:
            print("\nExited Agent")

class RunWorkflowCommand(Command):
    """Run Workflow with Data"""
    description = "Run Workflow with Data"
    user_options = [
        ('workflow=', 'w', 'Workflow filename (e.g., google_search_example.yaml)'),
        ('data=', 'd', 'Data filename (e.g., search_terms.json)'),
    ]
    
    def initialize_options(self):
        self.workflow = None
        self.data = None
    
    def finalize_options(self):
        if not self.workflow:
            self.workflow = "google_search_example.yaml"
        if not self.data:
            self.data = "search_terms.json"
    
    def run(self):
        print(f"Running workflow {self.workflow} with data {self.data}...")
        try:
            subprocess.run([
                sys.executable, 
                os.path.join(HERE, "src", "run_workflow_batch.py"),
                self.workflow,
                self.data
            ], check=True)
        except subprocess.CalledProcessError:
            print("Error running workflow")
        except KeyboardInterrupt:
            print("\nExited workflow")

# Execute additional setup steps
create_env_file()
create_directories()

setup(
    name="browser-automation-agent",
    version="0.1.0",
    description="Browser automation project with Playwright and OpenAI Agents",
    long_description=read_file(os.path.join(HERE, "README.md")),
    long_description_content_type="text/markdown",
    author="AI Assistant",
    author_email="user@example.com",
    url="https://github.com/yourusername/browser-automation-agent",
    packages=find_packages(),
    py_modules=[
        "src.main", 
        "src.run_workflow_batch"
    ],
    install_requires=read_requirements(),
    python_requires=">=3.8",
    cmdclass={
        "install_playwright": InstallPlaywrightCommand,
        "run_agent": RunAgentCommand,
        "run_workflow": RunWorkflowCommand,
    },
    entry_points={
        "console_scripts": [
            "browser-agent=src.main:main",
            "workflow-runner=src.run_workflow_batch:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    license="MIT",
)

# Installation complete notification
print("\n===== Installation Complete! =====")
print("\nTo complete setup, run the following commands:")
print("1. pip install -e .")
print("2. python setup.py install_playwright")
print("\nThen you can:")
print("- Run Agent: python setup.py run_agent")
print("- Run Workflow: python setup.py run_workflow --workflow=google_search_example.yaml --data=search_terms.json")
print("\nYou can also use the direct commands after installation:")
print("- browser-agent")
print("- workflow-runner google_search_example.yaml search_terms.json")
