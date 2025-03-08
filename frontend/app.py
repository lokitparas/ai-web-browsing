import streamlit as st
import sys
import os
import re
from PIL import Image
from io import BytesIO
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add backend path explicitly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.browser_agent import BrowserAgent

st.title("Autonomous Web Browsing Agent")

url = st.text_input("Enter URL:")
instruction = st.text_area("Enter Task Instructions:")

# Advanced options
with st.expander("Advanced Options", expanded=False):
    headless = st.checkbox("Run browser in headless mode", value=True, 
                          help="Enable to hide the browser window (more stable). Disable to see the browser in action (better for avoiding detection).")
    
    st.info("Using undetected_chromedriver to bypass bot detection. Showing the browser (headless=False) may help with sites that have advanced anti-bot measures.")

# Get API key from loaded environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize session state if not already done
if "action_history" not in st.session_state:
    st.session_state.action_history = []

# Function to parse AI response
def parse_ai_response(response_text):
    result = {}
    # Extract action type
    action_match = re.search(r'action:\s*(\w+)', response_text, re.IGNORECASE)
    if action_match:
        result["action"] = action_match.group(1).lower()
    
    # Extract selector if present
    selector_match = re.search(r'selector:\s*([^\n]+)', response_text, re.IGNORECASE)
    if selector_match:
        result["selector"] = selector_match.group(1).strip()
    
    # Extract amount if present
    amount_match = re.search(r'amount:\s*(-?\d+)', response_text, re.IGNORECASE)
    if amount_match:
        result["amount"] = int(amount_match.group(1))
    
    # Extract reasoning if present
    reasoning_match = re.search(r'reasoning:\s*([^\n]+)', response_text, re.IGNORECASE)
    if reasoning_match:
        result["reasoning"] = reasoning_match.group(1).strip()
    
    return result

if st.button("Execute Task"):
    try:
        with st.spinner("Initializing undetected Chrome browser..."):
            # Create browser agent with specified headless setting
            agent = BrowserAgent(headless=headless)
            st.success("Browser initialized successfully - using undetected_chromedriver for enhanced bot protection")
        
        with st.spinner(f"Navigating to {url}..."):
            navigation_success = agent.navigate(url)
            
        if not navigation_success:
            st.error("Failed to navigate to the URL. The site may be blocking automated access.")
            agent.close()
            st.stop()

        screenshot_bytes = agent.screenshot()
        img = Image.open(BytesIO(screenshot_bytes))
        st.image(img, caption="Initial Screenshot")
        st.session_state.action_history.append(f"Navigated to {url}")

        html_content = agent.get_html()

        conversation_history = [
            {"role": "system", "content": "You are an autonomous web browsing agent."},
            {"role": "user", "content": f"Browse this website: {url}\nTask: {instruction}"}
        ]

        for i in range(10):
            with st.spinner("AI is analyzing the page..."):
                next_action_text = agent.get_ai_decision(html_content=agent.get_html(), conversation_history=conversation_history)
            
            # Display the AI's thought process
            with st.expander(f"Step {i+1}: AI Decision", expanded=True):
                st.write(next_action_text)
            
            # Parse the AI response
            parsed_action = parse_ai_response(next_action_text)
            
            # Add to conversation history for context
            conversation_history.append({"role": "assistant", "content": next_action_text})
            
            # Execute the action
            action_completed = False
            if parsed_action.get("action") == "click":
                selector = parsed_action.get("selector")
                if selector:
                    st.write(f"Clicking element: {selector}")
                    with st.spinner("Performing click action..."):
                        action_completed = agent.perform_action("click", selector=selector, current_task=instruction)
            elif parsed_action.get("action") == "hover":
                selector = parsed_action.get("selector")
                if selector:
                    st.write(f"Hovering over element: {selector}")
                    with st.spinner("Performing hover action..."):
                        action_completed = agent.perform_action("hover", selector=selector, current_task=instruction)
            elif parsed_action.get("action") == "scroll":
                amount = parsed_action.get("amount", 500)  # Default to 500 pixels if not specified
                st.write(f"Scrolling by {amount} pixels")
                with st.spinner("Performing scroll action..."):
                    action_completed = agent.perform_action("scroll", amount=amount)
            elif parsed_action.get("action") == "complete":
                st.success("Task completed successfully!")
                
                # Save only the body content when task is complete
                with st.spinner("Saving page content..."):
                    content_filename = agent.save_page_content()
                    if content_filename:
                        st.success(f"Saved page body content to {content_filename}")
                        
                        # Show a preview of the saved content
                        with open(content_filename, 'r', encoding='utf-8') as f:
                            body_content = f.read()
                            with st.expander("Preview of saved body content", expanded=False):
                                st.code(body_content[:2000] + ("..." if len(body_content) > 2000 else ""), language="html")
                break
                
            if not action_completed:
                st.warning("Action could not be completed. The agent will try to recover.")

            # Display updated screenshot after action
            try:
                screenshot_bytes = agent.screenshot()
                img = Image.open(BytesIO(screenshot_bytes))
                st.image(img, caption=f"Screenshot after step {i+1}")
            except Exception as e:
                st.error(f"Error taking screenshot: {e}")
                st.warning("Attempting to refresh page state...")
                try:
                    agent.navigate(agent.current_url)
                    screenshot_bytes = agent.screenshot()
                    img = Image.open(BytesIO(screenshot_bytes))
                    st.image(img, caption=f"Screenshot after recovery")
                except:
                    st.error("Could not recover browser state.")
            
            # Add user feedback for AI
            conversation_history.append({
                "role": "user", 
                "content": "What should I do next to continue with the task?"
            })
    except Exception as e:
        st.error(f"An error occurred: {e}")
    finally:
        # Close the browser when done
        try:
            agent.close()
        except:
            pass 