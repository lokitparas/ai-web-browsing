# AI Web Browsing Agent

An autonomous AI agent that, given a URL and a task in natural language, can browse the webpage and perform tasks.

## Features

- **Natural Language Instructions**: Tell the agent what you want to do on a website
- **Autonomous Navigation**: The agent can scroll, click, and analyze webpages
- **Real-time Screenshots**: See what the agent sees as it browses
- **Powered by GPT-4o**: Uses OpenAI's advanced language model for decision making

## Architecture

- **Backend**: Python FastAPI application with Playwright for web automation
- **Frontend**: React/Next.js application with a modern UI
- **Communication**: WebSockets for real-time updates

## Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- OpenAI API key

## Setup

### Backend

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```
   playwright install
   ```

4. Create a .env file from the example:
   ```
   cp .env.example .env
   ```

5. Add your OpenAI API key to the .env file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Frontend

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install Node.js dependencies:
   ```
   npm install
   # or
   yarn
   ```

## Running the Application

### Backend

1. Start the FastAPI server:
   ```
   cd backend
   python run.py
   ```

### Frontend

1. Start the Next.js development server:
   ```
   cd frontend
   npm run dev
   # or
   yarn dev
   ```

2. Open your browser and navigate to http://localhost:3000

## Usage

1. Enter a URL of the website you want to navigate
2. Provide a natural language instruction for what you want the agent to do
3. Click "Start Browsing" and watch as the agent attempts to complete your task
4. The left panel shows the chat history and the right panel displays screenshots of what the agent sees

## Limitations

- The agent may struggle with highly dynamic websites or complex interactions
- Navigation is limited to scrolling and clicking
- Some websites may block automated browsers
- The agent works best with clear, specific instructions

## License

MIT 