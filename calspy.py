"""
Main entry point for the calendar scraping and processing tool.
Handles the scraping of Google Calendar data and HTML generation.
"""

from src.scraper import main as scraper_main
from src.generate_calendar import generate_calendar
import sys
import argparse
from src.version import __version__

def main():
    parser = argparse.ArgumentParser(description='Calendar scraping and processing tool')
    parser.add_argument('-v', '--version', action='version', version=f'calspy {__version__}')
    args = parser.parse_args()

    try:
        scraper_main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
