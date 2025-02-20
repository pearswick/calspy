import requests
from icalendar import Calendar
import sys

def fetch_calendar_ics(url):
    """
    Fetches the ICS file content from the given URL.
    Returns the raw iCal data as text.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching calendar: {e}")
        sys.exit(1)

def parse_ics(ics_data):
    """
    Parses the ICS data into an icalendar Calendar object.
    Returns the Calendar object.
    """
    try:
        return Calendar.from_ical(ics_data)
    except Exception as e:
        print(f"Error parsing calendar data: {e}")
        sys.exit(1)

def extract_calendar_data(cal):
    """
    Extracts relevant information from calendar events.
    Returns a list of dictionaries containing event details.
    """
    events = []
    
    for component in cal.walk('VEVENT'):
        start_dt = component.get('DTSTART').dt if component.get('DTSTART') else None
        summary = component.get('SUMMARY', 'No Title')
        description = component.get('DESCRIPTION', 'No Description')
        attendees = component.get('ATTENDEE', [])
        
        # Convert attendees to list if it's a single value
        if not isinstance(attendees, list):
            attendees = [attendees]
            
        # Clean up attendee emails
        attendee_list = [str(a).replace('mailto:', '') for a in attendees if str(a)]
        
        events.append({
            'datetime': start_dt,
            'summary': summary,
            'description': description,
            'attendees': attendee_list
        })
    
    return events

def save_to_file(events, filename='target_calendar.txt'):
    """
    Saves the calendar data to a text file for testing purposes.
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for event in events:
                f.write("=== Event ===\n")
                f.write(f"Date/Time: {event['datetime']}\n")
                f.write(f"Summary: {event['summary']}\n")
                f.write(f"Description: {event['description']}\n")
                f.write("Attendees:\n")
                for attendee in event['attendees']:
                    f.write(f"  - {attendee}\n")
                f.write("\n")
        print(f"Calendar data has been saved to {filename}")
    except IOError as e:
        print(f"Error saving to file: {e}")
        sys.exit(1)

def main():
    # Get calendar URL from user
    print("Please enter your public Google Calendar URL (ICS format):")
    calendar_url = input().strip()
    
    if not calendar_url:
        print("No URL provided. Exiting...")
        sys.exit(1)
    
    print("Fetching calendar data...")
    ics_data = fetch_calendar_ics(calendar_url)
    
    print("Parsing calendar data...")
    cal = parse_ics(ics_data)
    
    print("Extracting events...")
    events = extract_calendar_data(cal)
    
    if not events:
        print("No events found in the calendar.")
        sys.exit(0)
    
    print(f"Found {len(events)} events.")
    save_to_file(events)

if __name__ == "__main__":
    main()
