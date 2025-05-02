# toolAI Documentation

## Project Structure

The project is organized into the following directories:

- **/src**: Main source code
  - **/ai**: AI-related components including element finders and page observer
  - **/automation**: Browser automation and control components
  - **/utils**: Utility functions and helpers
  - **/tests**: Unit and integration tests

- **/data**: Data files and resources
  - **/screenshots**: Screenshots captured during automation
  - **/downloads**: Downloaded files
  - **/json_data**: JSON configuration and data files
  - **/videos**: Video recordings of automation (when enabled)

- **/logs**: Log files
  - **browser_automation.log**: Main log file for the browser automation

- **/workflows**: YAML workflow definition files
  - Define automation sequences that can be executed by the system

- **/docs**: Documentation and guides

## Key Components

### AI Components (/src/ai)

- **enhanced_element_finder.py**: Uses AI to find elements on a webpage based on natural language descriptions
- **page_observer**: Monitors and analyzes web page changes in real-time
- **ai_element_finder.py**: Legacy version of element finder
- **ai_engine_manager.py**: Manages different AI engines and their configurations

### Automation Components (/src/automation)

- **browser_controller.py**: Core controller for browser interactions
- **workflow_manager.py**: Executes workflows defined in YAML files
- **session_manager.py**: Manages browser sessions
- **helpers/**: Helper modules for various automation tasks

### Configuration Files

- **.env**: Environment variables and configuration
- **.env.example**: Example environment file template
- **requirements.txt**: Python dependencies

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in required API keys
3. Run a sample workflow: `python src/main.py --workflow workflows/google_search_example.yaml`

## Advanced Usage

See example workflows in the `/workflows` directory for advanced usage patterns.
