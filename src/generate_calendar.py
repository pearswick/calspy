from jinja2 import Environment, FileSystemLoader
import json
import os

def load_calendar_data(calendar_id, use_partial=False, console=None):
    """
    Load calendar data from JSON file
    use_partial: if True, will try to load partial data if final data is not available
    console: Rich console object for pretty printing
    """
    try:
        # Find the latest timestamp directory for this calendar
        base_dir = os.path.join(os.getcwd(), 'calendars', calendar_id)
        if not os.path.exists(base_dir):
            raise FileNotFoundError(f"No data directory found for calendar: {calendar_id}")
            
        timestamp_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        if not timestamp_dirs:
            raise FileNotFoundError(f"No data found in calendar directory: {calendar_id}")
            
        latest_dir = max([os.path.join(base_dir, d) for d in timestamp_dirs], key=os.path.getmtime)
        
        # Try final data first, fall back to partial if requested
        final_path = os.path.join(latest_dir, 'calendar_data_final.json')
        partial_path = os.path.join(latest_dir, 'calendar_data_partial.json')
        
        if os.path.exists(final_path):
            with open(final_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif use_partial and os.path.exists(partial_path):
            if console:
                console.print("[yellow]Using partial data for calendar generation...[/]")
            else:
                print("Using partial data for calendar generation...")
            with open(partial_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise FileNotFoundError(f"No calendar data found for {calendar_id}")
            
    except Exception as e:
        raise Exception(f"Error loading calendar data: {str(e)}")

def generate_calendar(calendar_id, use_partial=False, console=None):
    """
    Generate HTML calendar from JSON data
    use_partial: if True, will try to use partial data if final data is not available
    console: Rich console object for pretty printing
    Returns: path to generated HTML file
    """
    try:
        # Get the absolute path to the template directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'templates')
        
        # Debug print to see what paths we're working with
        print(f"Looking for template in: {template_dir}")
        
        # Set up Jinja environment
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template('calendar_display_template.html')
        
        # Load calendar data and get the directory path
        data = load_calendar_data(calendar_id, use_partial, console)
        base_dir = os.path.join(os.getcwd(), 'calendars', calendar_id)
        timestamp_dir = max([os.path.join(base_dir, d) for d in os.listdir(base_dir)], key=os.path.getmtime)
        
        # Render template with data
        html_output = template.render(test_data=data)
        
        # Generate output filename and save in the timestamp directory
        output_filename = f"{calendar_id}.html"
        output_path = os.path.join(timestamp_dir, output_filename)
        
        # Write to output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        if console:
            console.print(f"[green]Calendar HTML has been generated as:[/] [blue]{output_path}[/]")
        else:
            print(f"Calendar HTML has been generated as: {output_path}")
        
        return output_path
    except Exception as e:
        print(f"ERROR: Error during HTML generation: {str(e)}")
        # Print more detailed error information
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generate_calendar.py <calendar_id>")
        sys.exit(1)
    generate_calendar(sys.argv[1]) 