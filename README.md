# AI Web Browsing Agent

An autonomous web browsing agent powered by Selenium, undetected_chromedriver, and GPT-4o. This agent can navigate websites, interact with elements, and complete tasks with minimal human intervention.

## Features

- **AI-Driven Navigation**: Uses GPT-4o to make decisions about where to click, hover, or scroll
- **Anti-Bot Detection**: Uses undetected_chromedriver to bypass common bot detection systems
- **Smart URL Selection**: LLM analyzes all possible links to choose the most relevant for your task
- **Multi-Strategy Interaction**: Multiple approaches to find and interact with elements
- **Comprehensive Element Finding**: Searches in main DOM, iframes, and shadow DOM
- **Automatic Selector Repair**: Fixes LLM-generated selectors to improve success rate
- **Visual Change Detection**: Uses screenshots to verify successful interactions
- **Advanced Logging**: Detailed logs for tracking actions and diagnosing issues

## Architecture

The project consists of two main components:

1. **Backend**: 
   - `backend/app/browser_agent.py`: Core agent logic for browser control and AI decisions
   
2. **Frontend**: 
   - `frontend/app.py`: Streamlit-based UI for setting tasks and viewing progress

## Requirements

- Python 3.10+ (recommended, may work with 3.8+)
- Chrome browser installed
- OpenAI API key with access to GPT-4o

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-web-browsing.git
   cd ai-web-browsing
   ```

2. Create a virtual environment:
   ```bash
   python -m venv ai-web-agent
   source ai-web-agent/bin/activate  # On Windows: ai-web-agent\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install streamlit undetected-chromedriver==3.5.3 --no-deps selenium webdriver-manager openai python-dotenv Pillow numpy
   ```

4. Set up your API key by creating a `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

1. Start the Streamlit interface:
   ```bash
   streamlit run frontend/app.py
   ```

2. Enter a URL and task instructions (e.g., "Find credit cards with no annual fee")

3. Click "Execute Task" and watch the agent:
   - Navigate to the website
   - Analyze the page content
   - Make decisions about which actions to take
   - Perform clicks, hovers, and scrolls
   - Complete your task

## How It Works

1. **Initialization**: Sets up an undetected Chrome browser instance
2. **Navigation**: Loads the specified URL
3. **Analysis**: The LLM analyzes the page content and decides what to do next
4. **Action Execution**: The agent performs the selected action:
   - Clicking links or buttons
   - Hovering over elements (especially for navigation menus)
   - Scrolling the page to find more content
5. **Iteration**: The agent repeats the analysis and action until the task is complete

## Key Capabilities

### Smart URL Selection

When the agent encounters multiple potential links to click, it sends all extracted URLs to the LLM with the original task. The LLM analyzes each URL and selects the most relevant one for the task.

### Multi-Domain Element Finding

The agent looks for elements across:
- Main document DOM
- All iframes
- Shadow DOM elements
- Dynamically generated content

### Self-Healing Selectors

If a selector fails, the agent will:
1. Try to repair it (e.g., converting exact match to contains)
2. Generate alternative selectors
3. Use different strategies to find elements

### Advanced Click Strategies

The agent uses multiple approaches to click elements:
1. Direct Selenium click
2. ActionChains click
3. JavaScript click
4. Removing overlays and retrying

## Troubleshooting

- **Navigation Failure**: Try running with `headless=False` to see what's happening
- **Selector Issues**: Check logs for element not found errors, might need to adjust selector format
- **Bot Detection**: Some sites have advanced protection, try visible mode (headless=False)

## License

MIT License 