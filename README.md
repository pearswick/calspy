# calspy v0.1.0

 ██████╗ █████╗ ██╗     ███████╗██████╗ ██╗   ██╗
██╔════╝██╔══██╗██║     ██╔════╝██╔══██╗╚██╗ ██╔╝
██║     ███████║██║     ███████╗██████╔╝ ╚████╔╝ 
██║     ██╔══██║██║     ╚════██║██╔═══╝   ╚██╔╝  
╚██████╗██║  ██║███████╗███████║██║        ██║   
 ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝        ╚═╝   


calspy is a tool for investigative journalists and OSINT researchers to scrape events from a public Google Calendar.

## Overview

calspy works by mimicking human action in a web browser, automating the process of clicking through each month to find events. The tool stops scraping when it has found 18 consecutive months with no events.

## Features

- Scrapes both future and past events
- Saves data in structured JSON format
- Handles calendar navigation automatically
- Configurable time range (default 5 years in each direction)
- Stores results in organized directory structure
- Error logging for troubleshooting

## Requirements

- Python 3.x
- Chrome browser installed
- Some basic knowledge of the command line

## Installation

1. Create and activate a virtual environment (recommended)

```bash
pip install -r requirements.txt
```

## Usage

Basic usage (will stop after finding 18 consecutive empty months):
```bash
python calspy.py
```

Scrape exactly N months into the past:
```bash
# Scrape exactly 24 months
python calspy.py -months 24

# Scrape exactly 36 months with debug logging
python calspy.py -months 36 -debug
```

When prompted, paste the public Google Calendar URL.

## Technical Details

The scraper works in three main phases:

1. **Initial Setup**
   - Uses undetected-chromedriver to avoid detection
   - Creates a headless browser session
   - Extracts calendar ID from the provided URL
   - Creates directory structure for data storage

2. **Scraping Process**
   - Starts at current month
   - Scrapes backward in time until year limit reached
   - Uses Selenium WebDriver for navigation
   - Uses BeautifulSoup for HTML parsing

3. **Data Processing**
   - Parses event details including:
     - Date and time
     - Event title
     - Description
     - Location
     - Attendees
   - Saves structured data as JSON

## Output Structure

Events are saved in:
```
calendars/
  [calendar_id]/
    [YYYYMMDD_HHMMSS]/
      calendar_data.json
```

JSON structure:
```json
{
  "calendar_id": "example@gmail.com",
  "scrape_timestamp": "2024-03-14 12:34:56",
  "events": [
    {
      "datetime": "2024-03-14 10:00 AM",
      "summary": "Event Title",
      "description": "Event Description",
      "location": "Event Location",
      "attendees": []
    }
  ]
}
```


## Command Line Arguments

- `-months`: Number of months to scrape (overrides empty months check)
- `-debug`: Enable debug logging (outputs to scraper.log)


## Error Handling

- Errors are logged to scraper_errors.log
- Debug mode (-debug) provides detailed logging in scraper.log
- The script handles common issues like:
  - Navigation failures
  - Network timeouts
  - Parse errors

## Requirements

- Python 3.7+
- Chrome browser installed
- Public Google Calendar URL

## Limitations

- Works only with public Google Calendars
- Requires Chrome browser
- May be affected by Google Calendar UI changes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

