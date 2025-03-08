import random
import os
import time
import base64
import numpy as np
import logging
from io import BytesIO
from PIL import Image
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from openai import OpenAI
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('BrowserAgent')

# Create OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class BrowserAgent:
    def __init__(self, headless=True):
        # Configure and initialize undetected_chromedriver
        logger.info("Initializing undetected Chrome browser")
        options = uc.ChromeOptions()
        if headless:
            logger.info("Running in headless mode")
            options.add_argument('--headless')
        else:
            logger.info("Running in visible mode")
        
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1280,800')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the undetected_chromedriver
        logger.info("Starting Chrome instance...")
        self.driver = uc.Chrome(options=options)
        self.driver.set_window_size(1280, 800)
        logger.info("Chrome started successfully")
        
        # Set a reasonable page load timeout
        self.driver.set_page_load_timeout(30)
        
        # Store state
        self.action_history = []
        self.current_url = ""
        self.last_screenshot = None
        logger.info("Browser agent initialized and ready")
    
    def navigate(self, url):
        """Navigate to URL using undetected_chromedriver"""
        try:
            logger.info(f"Navigating to URL: {url}")
            self.driver.get(url)
            
            # Wait for the page to load
            logger.info("Waiting for page to load...")
            time.sleep(2)
            
            self.current_url = url
            self.action_history.append(f"Navigated to {url}")
            logger.info(f"Successfully loaded URL: {url}")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {str(e)}")
            self.action_history.append(f"Navigation error: {e}")
            return False
    
    def screenshot(self):
        """Take a screenshot with undetected_chromedriver"""
        logger.debug("Taking screenshot")
        screenshot_bytes = self.driver.get_screenshot_as_png()
        self.last_screenshot = screenshot_bytes
        return screenshot_bytes
    
    def get_screenshot_base64(self):
        """Get screenshot as base64 for embedding in prompts"""
        logger.debug("Taking base64 screenshot for AI model")
        screenshot_bytes = self.driver.get_screenshot_as_png()
        self.last_screenshot = screenshot_bytes
        
        # Convert to JPEG and optimize for size
        img = Image.open(BytesIO(screenshot_bytes))
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        logger.debug("Screenshot processed and encoded")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    def _compare_screenshots(self, before_screenshot, after_screenshot, threshold=0.05):
        """Compare two screenshots and return True if they are different enough"""
        logger.debug(f"Comparing screenshots with threshold {threshold}")
        if before_screenshot is None or after_screenshot is None:
            logger.debug("One screenshot is None, considering them different")
            return True
            
        # Convert to numpy arrays for comparison
        img1 = np.array(Image.open(BytesIO(before_screenshot)).convert('RGB'))
        img2 = np.array(Image.open(BytesIO(after_screenshot)).convert('RGB'))
        
        # Check if dimensions match
        if img1.shape != img2.shape:
            logger.debug("Screenshot dimensions don't match, considering them different")
            return True
            
        # Calculate difference
        diff = np.abs(img1.astype(np.float32) - img2.astype(np.float32)) / 255.0
        diff_score = np.mean(diff)
        
        logger.debug(f"Screenshot difference score: {diff_score}")
        return diff_score > threshold
    
    def _validate_selector(self, selector):
        """Validate if a selector is likely to work and fix common issues"""
        # Fix common LLM hallucination patterns
        if selector.startswith('a[href="') or selector.startswith('a[href=\''):
            # The LLM often hallucinates exact href values, try to use contains instead
            modified = selector.replace('href="', 'href*="').replace("href='", "href*='")
            logger.info(f"🔧 Modified selector from {selector} to {modified} (using contains)")
            return modified
            
        # Fix attribute contains syntax for Selenium compatibility
        if '*=' in selector and not selector.startswith('//'):
            # Selenium CSS selectors use [attr*=value] format, not [attr*="value"]
            modified = selector.replace('*="', '*=').replace("*='", "*=").replace(']', "']")
            if modified != selector:
                logger.info(f"🔧 Modified selector from {selector} to {modified} (fixing contains syntax)")
                return modified
        
        return selector
        
    def _check_element_exists(self, selector):
        """Check if any elements matching the selector exist in the page"""
        try:
            # First check in main document
            elements = self._find_elements_in_document(selector)
            if elements:
                logger.info(f"✓ Found {len(elements)} elements matching {selector} in main document")
                return elements
                
            # If not found, check in all frames
            elements = self._find_elements_in_frames(selector)
            if elements:
                logger.info(f"✓ Found {len(elements)} elements matching {selector} in frames")
                return elements
                
            # If still not found, check in shadow DOMs
            elements = self._find_elements_in_shadow_dom(selector)
            if elements:
                logger.info(f"✓ Found {len(elements)} elements matching {selector} in shadow DOM")
                return elements
                
            # If nothing found, try generating alternative selectors
            alt_elements, alt_selector = self._find_with_alternative_selectors(selector)
            if alt_elements:
                logger.info(f"✓ Found {len(alt_elements)} elements matching alternative selector {alt_selector}")
                return alt_elements
                
            logger.warning(f"❌ No elements found matching {selector} in entire page")
            
            # Last resort: dump all links on page for debugging
            self._debug_dump_page_links()
            
            return []
            
        except Exception as e:
            logger.error(f"Error checking if element exists: {e}")
            return []
            
    def _find_elements_in_document(self, selector):
        """Find elements in the main document"""
        try:
            by = By.XPATH if selector.startswith('//') else By.CSS_SELECTOR
            return self.driver.find_elements(by, selector)
        except Exception as e:
            logger.warning(f"Error finding elements in document: {e}")
            return []
            
    def _find_elements_in_frames(self, selector):
        """Find elements in all iframes"""
        all_elements = []
        try:
            # Get all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            logger.info(f"Found {len(iframes)} iframes to search")
            
            # Save current context
            main_content = self.driver.current_window_handle
            
            for i, iframe in enumerate(iframes):
                try:
                    logger.info(f"Switching to iframe {i+1}/{len(iframes)}")
                    self.driver.switch_to.frame(iframe)
                    
                    by = By.XPATH if selector.startswith('//') else By.CSS_SELECTOR
                    elements = self.driver.find_elements(by, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements in iframe {i+1}")
                        all_elements.extend(elements)
                        
                except Exception as e:
                    logger.warning(f"Error searching iframe {i+1}: {e}")
                    
                # Switch back to main content
                self.driver.switch_to.default_content()
                
            return all_elements
            
        except Exception as e:
            logger.warning(f"Error searching frames: {e}")
            # Make sure we're back in the main context
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return all_elements
            
    def _find_elements_in_shadow_dom(self, selector):
        """Find elements in shadow DOMs"""
        try:
            # Execute JavaScript to search in shadow DOMs
            shadow_elements = self.driver.execute_script(f"""
                function getAllShadowHosts(root) {{
                    const hosts = [];
                    const walker = document.createTreeWalker(
                        root, NodeFilter.SHOW_ELEMENT, null, false
                    );
                    
                    while(walker.nextNode()) {{
                        if (walker.currentNode.shadowRoot) {{
                            hosts.push(walker.currentNode);
                        }}
                    }}
                    
                    return hosts;
                }}
                
                function findElementsInShadowDom(selector) {{
                    const allElements = [];
                    const shadowHosts = getAllShadowHosts(document.body);
                    
                    for (const host of shadowHosts) {{
                        try {{
                            const elements = host.shadowRoot.querySelectorAll(selector);
                            if (elements.length > 0) {{
                                console.log('Found elements in shadow DOM:', elements.length);
                                for (const el of elements) {{
                                    allElements.push(el);
                                }}
                            }}
                        }} catch(e) {{
                            console.error('Error searching shadow DOM:', e);
                        }}
                    }}
                    
                    return allElements;
                }}
                
                return findElementsInShadowDom("{selector}");
            """)
            
            if shadow_elements and len(shadow_elements) > 0:
                logger.info(f"Found {len(shadow_elements)} elements in shadow DOM")
                return shadow_elements
                
            return []
            
        except Exception as e:
            logger.warning(f"Error searching shadow DOM: {e}")
            return []
            
    def _find_with_alternative_selectors(self, selector):
        """Try to find elements with alternative selectors"""
        # Generate alternative selectors
        alternatives = []
        
        # Strip attributes from a more complex selector
        if '[' in selector and not selector.startswith('//'):
            base_selector = selector.split('[')[0]
            alternatives.append(base_selector)
        
        # For links, try text content
        if 'a[' in selector or selector == 'a':
            # Extract the text we're looking for
            text_match = None
            if 'contains(text()' in selector:
                match = re.search(r"contains\(text\(\),\s*['\"]([^'\"]+)['\"]", selector)
                if match:
                    text_match = match.group(1)
            elif "href*=" in selector:
                # Try to extract meaningful text from the URL
                href_part = selector.split("href*=")[1].strip("'[]\"")
                parts = href_part.split('/')
                if parts:
                    text_match = parts[-1].replace('-', ' ').replace('_', ' ')
                    
            if text_match:
                # Try variations of link by text
                alternatives.append(f"//a[contains(text(), '{text_match}')]")
                alternatives.append(f"//a[contains(., '{text_match}')]")
                
                # Try links with inner elements containing text
                alternatives.append(f"//a[.//*[contains(text(), '{text_match}')]]")
                
        # For buttons, try button texts
        if 'button[' in selector or selector == 'button':
            text_match = None
            if 'contains(text()' in selector:
                match = re.search(r"contains\(text\(\),\s*['\"]([^'\"]+)['\"]", selector)
                if match:
                    text_match = match.group(1)
                    
            if text_match:
                alternatives.append(f"//button[contains(text(), '{text_match}')]")
                alternatives.append(f"//button[.//*[contains(text(), '{text_match}')]]")
                alternatives.append(f"//*[@role='button' and contains(text(), '{text_match}')]")
                
        # For ids, try partial id matching
        if '#' in selector:
            id_part = selector.split('#')[1].split(' ')[0].split('[')[0]
            alternatives.append(f"//*[contains(@id, '{id_part}')]")
            
        # Try each alternative
        for alt in alternatives:
            logger.info(f"Trying alternative selector: {alt}")
            try:
                by = By.XPATH if alt.startswith('//') else By.CSS_SELECTOR
                elements = self.driver.find_elements(by, alt)
                if elements:
                    return elements, alt
            except:
                pass
                
        return [], None
        
    def _debug_dump_page_links(self):
        """Dump all links on the page for debugging when an element can't be found"""
        try:
            logger.info("🔍 Debugging - dumping all page links:")
            links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Found {len(links)} links on page")
            
            for i, link in enumerate(links[:20]):  # Limit to first 20 for brevity
                try:
                    href = link.get_attribute('href')
                    text = link.text
                    logger.info(f"Link {i+1}: href='{href}', text='{text}'")
                except:
                    pass
                    
            # Also get buttons
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            logger.info(f"Found {len(buttons)} buttons on page")
            
            for i, button in enumerate(buttons[:10]):  # Limit to first 10
                try:
                    text = button.text
                    logger.info(f"Button {i+1}: text='{text}'")
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Error dumping debug info: {e}")
    
    def _extract_relevant_url(self, extracted_urls, current_task):
        """Use LLM to determine the most relevant URL for the current task"""
        if not extracted_urls or len(extracted_urls) == 0:
            logger.info("No URLs to analyze for relevance")
            return None
            
        logger.info(f"Asking LLM to select most relevant URL from {len(extracted_urls)} options for task: {current_task}")
        
        # Prepare a prompt for the LLM
        url_list = "\n".join([f"{i+1}. {url}" for i, url in enumerate(extracted_urls)])
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that helps select the most relevant URL for a given task."},
                    {"role": "user", "content": f"""
I'm working on this task: "{current_task}"

Here are URLs extracted from the current page:
{url_list}

Please analyze these URLs and select the SINGLE most relevant one for my task.
If none of the URLs seem directly relevant to the task, respond with "NONE".

Return ONLY the full URL if you find a relevant one, or just "NONE" if none are relevant.
Do NOT include any explanation or additional text in your response.
"""}
                ],
                max_tokens=100,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            
            # Check if the response is "NONE" or an actual URL
            if result == "NONE":
                logger.info("LLM determined no URLs are relevant to the current task")
                return None
                
            # Validate that the returned value is one of our extracted URLs
            if result in extracted_urls:
                logger.info(f"🎯 LLM selected relevant URL: {result}")
                return result
            else:
                # Try to find a close match (in case of small differences)
                for url in extracted_urls:
                    if url in result or result in url:
                        logger.info(f"🎯 LLM selected relevant URL (partial match): {url}")
                        return url
                        
                logger.warning(f"LLM returned a URL that wasn't in our list: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting URL relevance from LLM: {e}")
            return None
            
    def _extract_url_from_element(self, selector, current_task=None):
        """Extract URL from an element if it's a link and filter for relevance if task provided"""
        logger.debug(f"Extracting URL from element: {selector}")
        
        # First validate and possibly improve the selector
        selector = self._validate_selector(selector)
        
        try:
            # Find all matching elements using our comprehensive search
            elements = self._check_element_exists(selector)
            if not elements:
                logger.warning(f"No elements found matching selector: {selector}")
                return None
                
            extracted_urls = []
            
            for i, element in enumerate(elements):
                # Extract href for anchor tags
                if element.tag_name == 'a':
                    href = element.get_attribute('href')
                    if href and href != "javascript:void(0);":
                        logger.info(f"📌 Extracted URL #{i+1}: {href} (from href attribute)")
                        extracted_urls.append(href)
                        continue
                
                # Look for onclick attributes with URLs
                onclick = element.get_attribute('onclick')
                if onclick and 'location' in onclick:
                    import re
                    match = re.search(r"(?:location\.href|window\.location|location)\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                    if match:
                        url = match.group(1)
                        logger.info(f"📌 Extracted URL #{i+1}: {url} (from onclick attribute)")
                        extracted_urls.append(url)
                        continue
                
                # Look for data-url attributes
                data_url = element.get_attribute('data-url')
                if data_url:
                    logger.info(f"📌 Extracted URL #{i+1}: {data_url} (from data-url attribute)")
                    extracted_urls.append(data_url)
                    continue
                
                # Try to find nested links
                child_links = element.find_elements(By.TAG_NAME, 'a')
                if child_links:
                    for j, link in enumerate(child_links):
                        href = link.get_attribute('href')
                        if href and href != "javascript:void(0);":
                            logger.info(f"📌 Extracted URL #{i+1}.{j+1}: {href} (from nested link)")
                            extracted_urls.append(href)
            
            # Filter out javascript:void(0) and other non-navigable URLs
            valid_urls = [url for url in extracted_urls if url 
                          and not url.startswith('javascript:')
                          and url != '#'
                          and url != '']
                          
            # If we have a task, use LLM to pick the most relevant URL
            if current_task and len(valid_urls) > 0:
                relevant_url = self._extract_relevant_url(valid_urls, current_task)
                if relevant_url:
                    return relevant_url
            
            # Return the first valid URL found if we couldn't get a relevant one
            for url in valid_urls:
                if url and (url.startswith('http') or url.startswith('/')):
                    return url
                    
            if not valid_urls:
                logger.warning(f"No valid URLs found in any matching elements for selector: {selector}")
                
            return None
        except Exception as e:
            logger.error(f"Error extracting URL: {str(e)}")
            self.action_history.append(f"Error extracting URL: {e}")
            return None
    
    def _try_click_strategies(self, selector, max_attempts=3, current_task=None):
        """Try multiple strategies to click an element"""
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
        
        logger.info(f"🔍 Attempting to interact with element: {selector}")
        
        # First validate and possibly improve the selector
        selector = self._validate_selector(selector)
        
        # STRATEGY 0: Wait for dynamic content to load
        logger.info("Ensuring page is fully loaded before interaction")
        self._wait_for_page_load()
        
        # STRATEGY 0.5: Extract URL and try direct navigation first
        target_url = self._extract_url_from_element(selector, current_task)
        if target_url:
            logger.info(f"🌐 FOUND TARGET URL: {target_url}")
            self.action_history.append(f"Element has URL: {target_url}")
            
            # Try direct navigation as the FIRST strategy if we have a URL
            if target_url.startswith('http') or target_url.startswith('/'):
                logger.info(f"🚀 STRATEGY: Direct navigation to extracted URL: {target_url}")
                try:
                    current_url = self.driver.current_url
                    full_url = target_url
                    
                    # Handle relative URLs
                    if target_url.startswith('/'):
                        from urllib.parse import urlparse
                        parsed = urlparse(current_url)
                        base_url = f"{parsed.scheme}://{parsed.netloc}"
                        full_url = base_url + target_url
                        logger.info(f"Converting relative URL to absolute: {full_url}")
                    
                    # Navigate directly to the target URL
                    self.navigate(full_url)
                    
                    # If we got here, navigation was successful
                    logger.info(f"✅ Direct navigation successful to: {full_url}")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Direct navigation failed: {str(e)}")
                    # Continue with other strategies
        
        # Try alternative selectors if possible
        selectors_to_try = [selector]
        
        # If using CSS selector, generate an XPath alternative
        if not selector.startswith('//'):
            # For links with aria-label, try an XPath alternative
            if 'aria-label' in selector:
                aria_value = selector.split('aria-label=')[1].strip('"\'[]')
                xpath_alt = f"//a[contains(@aria-label, '{aria_value}')]"
                selectors_to_try.append(xpath_alt)
                
                # Also try by text content
                text_xpath = f"//a[contains(text(), '{aria_value}')]"
                selectors_to_try.append(text_xpath)
            
            # If it's a link with class, try more generic XPath
            if 'a[class' in selector:
                class_val = selector.split('class')[1].split('=')[1].strip('"\'[]')
                xpath_alt = f"//a[contains(@class, '{class_val}')]"
                selectors_to_try.append(xpath_alt)
                
            # For buttons, try button text alternatives
            if 'button' in selector:
                if 'aria-label' in selector:
                    aria_value = selector.split('aria-label=')[1].strip('"\'[]')
                    btn_text_xpath = f"//button[contains(text(), '{aria_value}')]"
                    selectors_to_try.append(btn_text_xpath)
        
        logger.info(f"Will try the following selectors: {selectors_to_try}")
        
        # Try each selector with each strategy
        for attempt_selector in selectors_to_try:
            by = By.XPATH if attempt_selector.startswith('//') else By.CSS_SELECTOR
            logger.info(f"Attempting with selector: {attempt_selector}")
            
            # Also extract URL from alternative selectors
            if attempt_selector != selector:
                alt_url = self._extract_url_from_element(attempt_selector, current_task)
                if alt_url and alt_url != target_url:
                    logger.info(f"🌐 Found alternative URL: {alt_url} from selector {attempt_selector}")
                    if alt_url.startswith('http') or alt_url.startswith('/'):
                        logger.info(f"🚀 Trying navigation to alternative URL: {alt_url}")
                        try:
                            # Handle relative URLs
                            if alt_url.startswith('/'):
                                from urllib.parse import urlparse
                                parsed = urlparse(self.driver.current_url)
                                base_url = f"{parsed.scheme}://{parsed.netloc}"
                                full_url = base_url + alt_url
                                logger.info(f"Converting relative URL to absolute: {full_url}")
                                self.navigate(full_url)
                            else:
                                self.navigate(alt_url)
                            logger.info(f"✅ Navigation successful to alternative URL: {alt_url}")
                            return True
                        except Exception as e:
                            logger.warning(f"⚠️ Navigation to alternative URL failed: {str(e)}")
            
            # Take a screenshot before clicking to compare later
            before_screenshot = self.screenshot()
            
            # STRATEGY 1: Find all matching elements and try clicking each one
            elements = self._check_element_exists(attempt_selector)
            if elements:
                try:
                    logger.info(f"🖱️ STRATEGY: Found {len(elements)} matching elements, attempting clicks")
                    
                    for i, element in enumerate(elements):
                        try:
                            # Check if element is visible and clickable
                            if element.is_displayed():
                                logger.info(f"Element {i+1} is displayed, attempting to click")
                                # Scroll to element
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
                                time.sleep(0.5)
                                
                                # Try regular click
                                logger.info(f"Attempting direct click on element {i+1}")
                                element.click()
                                logger.info(f"Direct click successful on element {i+1}")
                                time.sleep(1)
                                
                                # Check if page changed
                                after_screenshot = self.screenshot()
                                if self._compare_screenshots(before_screenshot, after_screenshot):
                                    logger.info("✅ Page visually changed after click")
                                    return True
                                elif self.driver.current_url != self.current_url:
                                    logger.info(f"✅ URL changed to {self.driver.current_url} after click")
                                    return True
                                
                                logger.info("Page didn't change, trying next element")
                            else:
                                logger.info(f"Element {i+1} is not displayed, skipping")
                        except Exception as e:
                            logger.warning(f"Error clicking element {i+1}: {e}")
                except Exception as e:
                    logger.warning(f"Error during element click attempts: {e}")
            else:
                logger.warning(f"No elements found with our comprehensive search")
            
            # STRATEGY 2: JavaScript click all matching elements
            try:
                logger.info(f"🖱️ STRATEGY: JavaScript click all matching elements with {attempt_selector}")
                # Execute JavaScript to click all matching elements
                result = self.driver.execute_script(f"""
                    var elements = document.querySelectorAll("{attempt_selector}");
                    var clickCount = 0;
                    for(var i=0; i<elements.length; i++) {{
                        try {{
                            elements[i].scrollIntoView({{block: 'center'}});
                            elements[i].click();
                            clickCount++;
                        }} catch(e) {{
                            console.error("Click error:", e);
                        }}
                    }}
                    return clickCount;
                """)
                logger.info(f"JavaScript executed, clicked {result} elements")
                
                # Check if page changed
                time.sleep(1)
                after_screenshot = self.screenshot()
                if self._compare_screenshots(before_screenshot, after_screenshot):
                    logger.info("✅ Page visually changed after JavaScript click")
                    return True
                elif self.driver.current_url != self.current_url:
                    logger.info(f"✅ URL changed to {self.driver.current_url} after JavaScript click")
                    return True
            except Exception as e:
                logger.warning(f"JavaScript click error: {e}")
        
        # If we have a URL, try navigating directly as a final fallback
        if target_url:
            logger.info(f"🔄 All click strategies failed, trying final direct navigation to: {target_url}")
            try:
                # Handle relative URLs
                if target_url.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(self.driver.current_url)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    full_url = base_url + target_url
                    logger.info(f"Converting relative URL to absolute: {full_url}")
                    self.navigate(full_url)
                else:
                    self.navigate(target_url)
                logger.info(f"✅ Final fallback navigation successful to: {target_url}")
                return True
            except Exception as e:
                logger.error(f"❌ Final fallback navigation failed: {e}")
        
        logger.error(f"❌ All click strategies failed for all selectors")
        return False

    def perform_action(self, action, selector=None, amount=None, current_task=None):
        """Perform browser actions using Selenium"""
        # Add delay between actions (1-3 seconds)
        delay = random.uniform(1, 3)
        logger.info(f"Waiting {delay:.1f} seconds before next action")
        time.sleep(delay)
        
        try:
            if action == "hover" and selector:
                logger.info(f"Hovering over element: {selector}")
                # Store current screenshot for comparison
                before_screenshot = self.screenshot()
                
                # Wait for element to be present
                element = self._wait_for_element(selector)
                if element is None:
                    logger.error(f"Failed to find element for hover: {selector}")
                    self.action_history.append(f"Failed to find element for hover: {selector}")
                    return False
                
                # Hover over element
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(element).perform()
                self.action_history.append(f"Hovered over element: {selector}")
                logger.info(f"Successfully hovered over element: {selector}")
                
                # Give some time for hover effects to appear
                logger.info("Waiting for hover effects to appear")
                time.sleep(1.5)
                
                # Take another screenshot and compare
                after_screenshot = self.screenshot()
                
                # Check if the hover caused visible changes
                if self._compare_screenshots(before_screenshot, after_screenshot):
                    logger.info("Hover action caused visible changes")
                    self.action_history.append("Hover action caused visible changes")
                    return True
                else:
                    logger.info("Hover action did not cause visible changes")
                    self.action_history.append("Hover action did not cause visible changes")
                    # If no changes, try clicking if it's a navigation element
                    target_url = self._extract_url_from_element(selector, current_task)
                    if target_url:
                        logger.info(f"Element has URL: {target_url}, clicking after hover")
                        self.action_history.append(f"Element has URL: {target_url}, clicking after hover")
                        return self.perform_action("click", selector=selector, current_task=current_task)
                    return True
                
            elif action == "click" and selector:
                logger.info(f"Clicking element: {selector}")
                # Store current URL before clicking
                current_url = self.driver.current_url
                
                # Try multiple approaches to find and click the element
                success = self._try_click_strategies(selector, current_task=current_task)
                
                if not success:
                    logger.error(f"All click strategies failed for: {selector}")
                    self.action_history.append(f"All click strategies failed for: {selector}")
                    return False
                
                # Wait a moment for any page loads/AJAX
                logger.info("Waiting for page to process click")
                time.sleep(2)
                
                # Check if URL changed (navigation occurred)
                new_url = self.driver.current_url
                if new_url != current_url:
                    self.current_url = new_url
                    logger.info(f"Navigation occurred to: {new_url}")
                    self.action_history.append(f"Navigation occurred to: {new_url}")
                    
                    # Wait for the page to stabilize
                    self._wait_for_page_load()
                
                return True
                
            elif action == "scroll" and amount:
                logger.info(f"Scrolling page by {amount} pixels")
                # Execute JavaScript to scroll
                self.driver.execute_script(f"window.scrollBy(0, {amount});")
                self.action_history.append(f"Scrolled page by {amount} pixels")
                time.sleep(0.5)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Action failed: {action} - {str(e)}")
            self.action_history.append(f"Action failed: {action} - {str(e)}")
            return False
    
    def _wait_for_page_load(self, timeout=10):
        """Wait for page to be fully loaded"""
        try:
            logger.info("Waiting for page to fully load")
            # Wait for the document to be in 'complete' state
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            
            # Give a moment for any animations to settle
            time.sleep(1)
            logger.info("Page load complete")
            return True
        except Exception as e:
            logger.error(f"Error waiting for page to load: {e}")
            self.action_history.append(f"Error waiting for page to load: {e}")
            return False
    
    def _wait_for_element(self, selector, timeout=5):
        """Wait for element to be present and return it"""
        try:
            logger.debug(f"Waiting for element: {selector}")
            # Determine if selector is XPath or CSS
            if selector.startswith('//'):
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            logger.debug(f"Element found: {selector}")
            return element
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            return None
        except Exception as e:
            logger.error(f"Error waiting for element: {e}")
            self.action_history.append(f"Error waiting for element: {e}")
            return None
    
    def get_html(self):
        """Get the HTML content of the page"""
        logger.debug("Getting page HTML content")
        return self.driver.page_source
    
    def get_ai_decision(self, html_content, conversation_history):
        """Use GPT-4o to decide the next action"""
        time.sleep(1)
        logger.info("Requesting next action from AI model")
        # Get latest screenshot as base64 for prompt
        screenshot_base64 = self.get_screenshot_base64()
        
        # Truncate HTML to avoid token limits
        html_truncated = html_content[:8000] + "..." if len(html_content) > 8000 else html_content
        
        # Get current URL
        current_url = self.driver.current_url
        
        # Prepare history summary - limit to last 10 actions
        action_summary = "\n".join(self.action_history[-10:]) if self.action_history else "No actions taken yet."
        
        logger.info("Sending request to OpenAI for next action decision")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history + [{
                "role": "system",
                "content": f"""
Current URL: {current_url}
Recent Actions:
{action_summary}

Current HTML (truncated):
{html_truncated}

I've attached a screenshot of the current state of the webpage.

Based on the screenshot, HTML content, and previous actions, determine the next best action to complete the user's task.

NAVIGATION MENU STRATEGY:
For navigation menu items, ALWAYS try hovering first before clicking, as many menus reveal options on hover.
If you've already hovered over an element and saw no changes, then try clicking it.

Available actions:
1. Hover: Identify an element to hover over (provide CSS selector or XPath) - Example: "action: hover, selector: .dropdown-menu"
2. Click: Identify a specific element to click (provide CSS selector or XPath) - Example: "action: click, selector: #submit-button"
3. Scroll: Scroll the page to see more content (specify amount in pixels, positive for down, negative for up) - Example: "action: scroll, amount: 500"
4. Complete: If you believe the task is complete - Example: "action: complete"

For hover and click actions, analyze the HTML to provide the EXACT CSS selector or XPath for the element.
Be specific and ensure your action directly contributes to the task.

Return your decision in a consistent format:
action: [action type]
selector: [CSS selector or XPath for the element] (only for click/hover)
amount: [scroll amount in pixels] (only for scroll)
reasoning: [brief explanation of why this action]
"""
            }],
            max_tokens=1500
        )
        logger.info("Received AI model response")
        return response.choices[0].message.content
    
    def close(self):
        """Close the browser"""
        try:
            logger.info("Closing browser")
            self.driver.quit()
            logger.info("Browser closed successfully")
        except:
            logger.warning("Error while closing browser")
            pass
    
    def _extract_body_content(self):
        """Extract only the content inside the body tag from the current page"""
        try:
            logger.debug("Extracting body content from page")
            # Use JavaScript to extract just the body content
            body_content = self.driver.execute_script("return document.body ? document.body.innerHTML : '';")
            return body_content
        except Exception as e:
            logger.error(f"Error extracting body content: {e}")
            self.action_history.append(f"Error extracting body content: {e}")
            # Fallback to regexp if execute_script fails
            html = self.get_html()
            body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
            if body_match:
                return body_match.group(1)
            return html  # Return full HTML as fallback
    
    def save_page_content(self, filename=None):
        """Save only the body content of the current page to a file"""
        logger.info("Saving page body content to file")
        body_content = self._extract_body_content()
        
        if not filename:
            # Generate filename based on current URL and timestamp
            import datetime
            clean_url = self.current_url.replace('https://', '').replace('http://', '').replace('/', '_')
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_content_{clean_url}_{timestamp}.html"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(body_content)
            logger.info(f"Successfully saved body content to {filename}")
            self.action_history.append(f"Saved body content to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving body content: {e}")
            self.action_history.append(f"Error saving body content: {e}")
            return None 