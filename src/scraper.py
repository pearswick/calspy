from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import os
import sys
import time
import logging
from urllib.parse import urlparse, parse_qs
import traceback
import argparse
from datetime import datetime, timedelta
import signal
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from src.version import __version__
import webbrowser  # Add to imports at top
from src.generate_calendar import generate_calendar

# Initialize Rich console with color support
console = Console(color_system="auto")
logger = None  # Will be initialized in setup_logging

# Global variables for tracking state
running = True
current_driver = None
collected_events = []
current_calendar_id = None

def signal_handler(signum, frame):
    """
    Handles shutdown signals (Ctrl+C)
    """
    global running
    print("\n\nShutdown requested. Cleaning up...")
    running = False

def setup_logging(debug_mode=False):
    """
    Sets up logging configuration
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), 'logs')  # Add os.getcwd() to ensure absolute path
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure logging
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Main log file
    main_handler = logging.FileHandler(os.path.join(logs_dir, 'scraper.log'))
    main_handler.setLevel(log_level)
    main_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(main_formatter)
    
    # Error log file
    error_handler = logging.FileHandler(os.path.join(logs_dir, 'scraper_errors.log'))
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n%(pathname)s:%(lineno)d\n')
    error_handler.setFormatter(error_formatter)
    
    # Console output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Setup logger
    logger = logging.getLogger('scraper')
    logger.setLevel(log_level)
    logger.addHandler(main_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger

def setup_driver():
    """
    Sets up and returns undetected Chrome driver
    """
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = uc.Chrome(options=options)
        driver.implicitly_wait(10)
        return driver
        
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def extract_calendar_id(url):
    """
    Extracts calendar ID from the URL
    """
    try:
        logger.debug(f"Extracting calendar ID from URL: {url}")
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        calendar_id = query_params.get('src', [None])[0]
        if not calendar_id:
            raise ValueError("Could not extract calendar ID from URL")
        
        logger.debug(f"Extracted calendar ID: {calendar_id}")
        return calendar_id
    
    except Exception as e:
        logger.error(f"Error extracting calendar ID: {str(e)}")
        raise

def create_calendar_directory(calendar_id):
    """
    Creates directory structure for storing calendar data
    """
    try:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        base_dir = os.path.join(os.getcwd(), 'calendars', calendar_id, timestamp)
        logger.debug(f"Creating directory: {base_dir}")
        os.makedirs(base_dir, exist_ok=True)
        return base_dir
    
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
        raise

def wait_for_calendar_load(driver):
    """
    Waits for calendar to load and returns True if successful
    """
    try:
        logger.debug("Current URL: " + driver.current_url)
        logger.debug("Waiting for page to load...")
        
        # Wait for any of these common calendar elements
        selectors = [
            "div[role='main']",  # Main calendar container
            "div[role='grid']",  # Calendar grid
            "div[role='presentation']",  # Calendar presentation
            "table.calendar-table",  # Calendar table
            "div[class*='calendar']"  # Any div with calendar in class name
        ]
        
        for selector in selectors:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logger.debug(f"Found element with selector: {selector}")
                return True
            except:
                continue
        
        # If we get here, none of the selectors worked
        logger.error("Could not find any calendar elements")
        
        # Let's log the page source for debugging
        logger.debug("Page source:")
        logger.debug(driver.page_source[:1000] + "...")  # First 1000 chars
        
        return False
        
    except Exception as e:
        logger.error(f"Error waiting for calendar: {str(e)}")
        return False

def parse_month_events(soup):
    """
    Parses events from the current month view with standardized datetime format
    """
    events = []
    try:
        event_elements = soup.find_all('div', {'role': 'button', 'class': 'KF4T6b'})
        logger.debug(f"Found {len(event_elements)} potential event elements")
        
        for event in event_elements:
            try:
                event_info = event.find('span', class_='XuJrye')
                if not event_info:
                    continue
                    
                event_text = event_info.text.strip()
                parts = event_text.split(', ')
                if len(parts) < 3:
                    logger.debug(f"Skipping event with insufficient parts: {event_text}")
                    continue
                
                # Initialize event details
                time_str = parts[0]
                title = parts[1]
                date_str = parts[-1]
                location = ''
                description = []
                
                # Extract details and location
                details_span = event.find('span', class_='WBi6vc')
                if details_span:
                    description.append(details_span.text.strip())
                
                for part in parts:
                    if part.startswith('Location: '):
                        location = part.replace('Location: ', '').strip()
                    elif ('Calendar:' not in part and 
                          part != title and 
                          not any(month in part for month in [
                              'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December'
                          ])):
                        if part not in description:
                            description.append(part)
                
                events.append({
                    'datetime': f"{date_str} {time_str}",
                    'summary': title.strip(),
                    'description': ' | '.join(filter(None, description)),
                    'location': location,
                    'attendees': []
                })
                logger.debug(f"Parsed event: {title} on {date_str} {time_str}")
                
            except Exception as e:
                logger.warning(f"Could not parse an event completely: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error parsing month events: {e}")
    
    return events

def save_progress(events, calendar_id, final=False):
    """
    Saves current progress to a JSON file
    """
    if not events:
        return
        
    try:
        # Create base directory for this calendar
        base_dir = os.path.join(os.getcwd(), 'calendars', calendar_id)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
            
        # Create timestamp directory
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        timestamp_dir = os.path.join(base_dir, timestamp)
        os.makedirs(timestamp_dir, exist_ok=True)
        
        # Save to the timestamp directory
        status = 'final' if final else 'partial'
        json_path = os.path.join(timestamp_dir, f'calendar_data_{status}.json')
        
        data = {
            'calendar_id': calendar_id,
            'scrape_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'scrape_status': status,
            'events': events
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if not final:
            console.print(f"\nProgress saved: [green]{len(events)} events[/] written to [blue]{json_path}[/]")
    
    except Exception as e:
        logger.error(f"Error saving progress: {str(e)}")

def cleanup():
    """
    Performs cleanup operations before shutdown
    """
    global current_driver, collected_events, current_calendar_id
    
    if collected_events and current_calendar_id:
        print("\nSaving collected events before shutdown...")
        save_progress(collected_events, current_calendar_id)
        
        # Generate HTML using available data (partial or final)
        try:
            html_path = generate_calendar(current_calendar_id, use_partial=True, console=console)
            
            # Open the generated HTML file in default browser
            try:
                webbrowser.open('file://' + os.path.abspath(html_path))
                console.print("[green]Opening calendar in your default browser...[/]")
            except Exception as e:
                logger.error(f"Could not open browser: {str(e)}")
            
            # Only remove partial file if we have a successful final save
            base_dir = os.path.join(os.getcwd(), 'calendars', current_calendar_id)
            latest_dir = max([os.path.join(base_dir, d) for d in os.listdir(base_dir)], key=os.path.getmtime)
            final_file = os.path.join(latest_dir, 'calendar_data_final.json')
            partial_file = os.path.join(latest_dir, 'calendar_data_partial.json')
            
            if os.path.exists(final_file) and os.path.exists(partial_file):
                os.remove(partial_file)
        except Exception as e:
            logger.error(f"Error during HTML generation: {str(e)}")
    
    if current_driver:
        print("Closing browser...")
        try:
            current_driver.quit()
        except OSError as e:
            if "[WinError 6] The handle is invalid" not in str(e):
                logger.error(f"Error during driver cleanup: {str(e)}")
        except Exception as e:
            logger.error(f"Error during driver cleanup: {str(e)}")
        current_driver = None
    
    console.print("[green]Cleanup complete. Thanks for using calspy![/]")

def scrape_direction(driver, max_empty_months=18, target_months=None):
    """
    Scrapes calendar in one direction (backwards)
    """
    events = []
    months_traversed = 0
    empty_months_count = 0
    start_date = datetime.now()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        scrape_task = progress.add_task(
            "Scraping calendar...",
            total=target_months if target_months else None
        )
        
        while running:
            try:
                # Get current month first
                current_month = None
                try:
                    month_element = driver.find_element(By.CLASS_NAME, "UyW9db")
                    current_month = month_element.text
                except:
                    pass
                
                if not current_month:
                    try:
                        month_element = driver.find_element(By.CSS_SELECTOR, "[role='heading'][class*='month']")
                        current_month = month_element.text
                    except:
                        pass
                
                if not current_month:
                    try:
                        month_element = driver.find_element(By.CSS_SELECTOR, "[aria-label*='February'], [aria-label*='March']")
                        current_month = month_element.get_attribute('aria-label').split(',')[0]
                    except:
                        pass
                
                if not current_month:
                    raise Exception("Could not find month element using any method")
                
                # Calculate date and parse events
                click_date = start_date - timedelta(days=30.44 * months_traversed)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                month_events = parse_month_events(soup)
                
                # Update empty months counter (only if not using target_months)
                if not target_months:
                    if not month_events:
                        empty_months_count += 1
                        logger.debug(f"No events found in {current_month}. Empty month count: {empty_months_count}")
                    else:
                        empty_months_count = 0
                
                events.extend(month_events)
                collected_events.extend(month_events)
                
                # Update progress description
                progress.update(
                    scrape_task,
                    description=f"[cyan]{click_date.strftime('%B %Y')}[/] | [yellow]{current_month}[/] | "
                              f"Months: {months_traversed} | "
                              f"Events: {len(events)}"
                )
                
                # Check stop conditions
                if target_months and months_traversed >= target_months:
                    console.print(f"\n[yellow]Reached target of {target_months} months. Stopping scrape.[/]")
                    break
                elif not target_months and empty_months_count >= max_empty_months:
                    console.print(f"\n[yellow]Found {empty_months_count} consecutive empty months. Stopping scrape.[/]")
                    break
                
                # Try to navigate backward
                prev_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Previous']")
                if not prev_button.is_enabled():
                    console.print("\n[yellow]Reached the beginning of available calendar data[/]")
                    break
                    
                prev_button.click()
                time.sleep(2)
                months_traversed += 1
                progress.advance(scrape_task)
                
            except Exception as e:
                logger.error(f"Error during scraping: {str(e)}")
                break
    
    return events

def fetch_calendar_data(url, max_empty_months=18, target_months=None):
    """
    Fetches calendar data using undetected-chromedriver.
    Returns the collected events.
    """
    global current_driver, running, collected_events
    collected_events = []  # Reset collected events at start
    
    try:
        with Progress(SpinnerColumn(), TextColumn("[cyan]Starting Chrome driver...[/]")) as progress:
            progress.add_task("", total=None)
            current_driver = setup_driver()
        
        with Progress(SpinnerColumn(), TextColumn("[cyan]Loading calendar URL...[/]")) as progress:
            progress.add_task("", total=None)
            logger.debug(f"Accessing URL: {url}")
            current_driver.get(url)
            
            if not wait_for_calendar_load(current_driver):
                raise Exception("Calendar failed to load")
        
        console.print("[green]Calendar loaded successfully[/]")
        time.sleep(5)  # Give extra time for JavaScript to run
        
        # Scrape backwards only
        scrape_direction(current_driver, max_empty_months, target_months)
        return collected_events

    except Exception as e:
        logger.error(f"Error during calendar scraping: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    finally:
        # Always save progress before closing
        if collected_events:  # Check if we have any events to save
            console.print("\nSaving final data...")
            save_progress(collected_events, current_calendar_id, final=True)
        
        if current_driver:
            try:
                logger.debug("Closing Chrome driver")
                current_driver.quit()
                current_driver = None
            except Exception as e:
                logger.warning(f"Error closing Chrome driver: {str(e)}")
    
    return collected_events

def main():
    global collected_events, current_calendar_id, logger
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    parser = argparse.ArgumentParser(description='Scrape Google Calendar events')
    parser.add_argument('-debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-months', type=int, help='Number of months to scrape (overrides empty months check)')
    args = parser.parse_args()
    
    logger = setup_logging(args.debug)
    
    try:
        ascii_art = f"""
[cyan] ██████╗ █████╗ ██╗     ███████╗██████╗ ██╗   ██╗
██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗╚██╗ ██╔╝[/]    [white]calspy🗓️🕵️[/][dim]v{__version__}[/]
[cyan]██║     ███████║██║     ███████╗██████╔╝ ╚████╔╝[/]     [white](c) 2024 pearswick[/]
[cyan]██║     ██╔══██║██║     ╚════██║██╔═══╝   ╚██╔╝[/]      [white]Google Calendar scraper[/]
[cyan]╚██████╗██║  ██║███████╗███████║██║        ██║[/]       [white]consult readme for help[/]
[cyan] ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝        ╚═╝[/]   
[dim]Press Ctrl+C at any time to save progress and exit[/]"""
        
        console.print(ascii_art)
        console.print("\nPlease enter the public Google Calendar URL:")
        calendar_url = input().strip()
        
        if not calendar_url:
            console.print("[red]No URL provided[/]")
            sys.exit(1)
        
        logger.debug(f"URL received: {calendar_url}")
        current_calendar_id = extract_calendar_id(calendar_url)
        console.print(f"[green]Extracting data for calendar:[/] {current_calendar_id}")
        
        if args.months:
            console.print(f"[green]Will scrape exactly {args.months} months[/]")
        else:
            console.print("[green]Will scrape until finding 18 consecutive empty months[/]")
            
        events = fetch_calendar_data(calendar_url, max_empty_months=18, target_months=args.months)
        
        if not events:
            console.print("[yellow]No events found in the calendar.[/]")
            sys.exit(0)
        
        console.print(f"\n[green]Found {len(events)} events total[/]")
        
        if running:  # Only save as final if we weren't interrupted
            save_progress(events, current_calendar_id, final=True)
            console.print("[green]Scraping completed successfully![/]")
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)
    
    finally:
        cleanup()

if __name__ == "__main__":
    main() 