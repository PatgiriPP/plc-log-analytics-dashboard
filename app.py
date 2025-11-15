import os
import re
import json
import pandas as pd
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. Initialization (Unchanged) ---
load_dotenv()
app = Flask(__name__)

# --- 2. Configure Gemini API (Unchanged) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in .env file. AI summary will be disabled.")
    genai.configure(api_key="DUMMY_KEY_PLEASE_REPLACE")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# --- 3. The Log Parser (Unchanged) ---
def parse_log_file(file_path, file_contents_string):
    """
    Parses the raw log file contents into a structured list of dictionaries.
    """
    
    # Regex to capture: [Timestamp] [Optional_Category] Message
    log_pattern = re.compile(r'\[(.*?)\]\s(?:\[(.*?)\]\s)?(.*)')
    
    # Regex for alarms with components
    alarm_pattern_with_component = re.compile(r'(K_|G_)(""".*?"""|".*?")\.(.*)')
    # Regex for simple alarms
    alarm_pattern_simple = re.compile(r'(K_|G_)(.*)')

    logger_name_match = re.search(r'^([A-Z0-9]+)', os.path.basename(file_path))
    logger_name = logger_name_match.group(1) if logger_name_match else "Unknown"

    parsed_data = []

    for line in file_contents_string.splitlines():
        line = line.strip().strip('"')
        
        log_match = log_pattern.match(line)
        
        if log_match:
            groups = log_match.groups()
            timestamp_str, category, message = groups
            
            # Set defaults. Message is group(3)
            state, component, description = None, None, message 
            
            if category is None:
                # This handles lines like: [21:53:09.764] 'Logger 5 "H1"...'
                category = "SYSTEM"

            if category == "ALARM":
                # Message is now the part *after* [ALARM], 
                
                alarm_match_comp = alarm_pattern_with_component.match(message)
                alarm_match_simple = alarm_pattern_simple.match(message)

                if alarm_match_comp:
                    # This will now match: K_"db5005".M401...
                    state_raw, component_raw, description_raw = alarm_match_comp.groups()
                    state = state_raw.replace('_', '') # Becomes 'K' or 'G'
                    component = component_raw.strip('"') # Becomes 'db5005'
                    description = description_raw # Becomes 'M401.Stepper controller error'
                
                elif alarm_match_simple:
                    # This will now match simple alarms like K_SomeError
                    state_raw, description_raw = alarm_match_simple.groups()
                    state = state_raw.replace('_', '')
                    description = description_raw
                    component = "General"
                else:
                    # If it's [ALARM] but matches neither regex
                    description = message if message else "Uncategorized Alarm"

            parsed_data.append({
                "TimestampStr": timestamp_str,
                "Logger": logger_name,
                "Category": category,
                "State": state,
                "Component": component,
                "Message": description
            })
            
    return parsed_data

# --- 4. The Analytics Engine (Unchanged) ---
def run_system_analysis(df):
    """
    Takes the combined, clean DataFrame and runs all analytics.
    Returns a dictionary of results.
    """
    results = {}
    
    # This step is crucial, it converts the parsed timestamp strings to datetime objects
    df['Timestamp'] = pd.to_datetime(df['TimestampStr'], format='%H:%M:%S.%f', errors='coerce')
    
    # 'State' will now correctly be 'K' for your alarms.
    active_alarms = df[(df['Category'] == 'ALARM') & (df['State'] == 'K')].copy()
    
    if not active_alarms.empty:
        # Use 'Message' (which is the description) for top alarms
        active_alarms['FullErrorMessage'] = active_alarms['Logger'] + ': ' + active_alarms['Message']
        results['top_alarms'] = active_alarms['FullErrorMessage'].value_counts().head(10).to_dict()
        
        # Use 'Component' (which is now correctly parsed) for top components
        active_alarms['FullComponentID'] = active_alarms['Logger'] + ': ' + active_alarms['Component'].fillna('Unknown')
        results['top_components'] = active_alarms['FullComponentID'].value_counts().head(10).to_dict()
    else:
        results['top_alarms'] = {"No active alarms found": 0}
        results['top_components'] = {"No failing components found": 0}

    # This searches the *entire* log (including 'SYSTEM' messages) for connection errors
    connection_errors = df[df['Message'].str.contains('Timeout|disconnected', case=False, na=False)]
    if not connection_errors.empty:
        results['connection_issues_by_logger'] = connection_errors['Logger'].value_counts().to_dict()
    else:
        results['connection_issues_by_logger'] = {"No connection issues": 0}

    # This chart should also work now, as active_alarms is no longer empty
    if not active_alarms.empty and not active_alarms['Timestamp'].isnull().all():
        # Resample by 5-minute intervals and count occurrences
        errors_over_time = active_alarms.set_index('Timestamp').resample('5min').count()['Category']
        errors_over_time = errors_over_time[errors_over_time > 0] # Only show intervals with errors
        
        results['errors_over_time'] = {
            "labels": errors_over_time.index.strftime('%H:%M').tolist(),
            "counts": errors_over_time.values.tolist()
        }
    else:
        results['errors_over_time'] = {"labels": [], "counts": []}
        
    results['stats'] = {
        "total_entries": len(df),
        "total_active_alarms": len(active_alarms) 
    }

    return results

# --- 5. The AI Function (FIXED) ---

def get_ai_summary(analysis_results):
    """
    Sends the analysis results to the Gemini API for a summary.
    This is now a synchronous (blocking) function.
    """
    if not GEMINI_API_KEY or "DUMMY" in GEMINI_API_KEY:
        return "* AI Summary is disabled. Please add your `GEMINI_API_KEY` to the `.env` file. *"
        
    system_prompt = (
        "You are an expert Senior PLC Maintenance Analyst. Your audience is a non-technical plant manager.\n"
        "Your goal is to provide a detailed, actionable report—not a vague summary. Use simple language. Avoid technical jargon where possible.\n"
        "Analyze the data I provide and structure your response in the following markdown format:\n\n"
        "## 1. Executive Summary\n"
        "- **Main Problem:** A one-sentence summary of the main problem.\n"
        "- **System Health:** (e.g., 'Critical', 'Unstable', 'Healthy')\n\n"
        "## 2. Detailed Problem Analysis\n"
        "- **Where is the problem?** Analyze the 'top_components' data. Point to the specific loggers and components that are failing most often (e.g., 'The KRW1 logger, component db5005, is the main issue.')\n"
        "- **What is the problem?** Analyze the 'top_alarms' data. Explain what the most common alarms mean in simple terms (e.g., 'Runtime error means the component is crashing,' 'Occupied Error means a sensor is stuck or blocked.')\n"
        "- **Is the network stable?** Analyze the 'connection_issues_by_logger' data. Explain what this means for production (e.g., 'Logger H119 is very unstable, which means we are blind to problems in that area.')\n\n"
        "## 3. Actionable Fixes (For the Team)\n"
        "Provide a numbered list of clear, physical actions the maintenance team should take.\n"
        "1.  **Priority 1 (Must-Do):** What is the first thing the team must investigate? (Be specific, e.g., 'Check the power supply and network cable for Logger H119.')\n"
        "2.  **Priority 2 (Should-Do):** What is the second most important fix?\n"
        "3.  **Priority 3 (Monitor):** What should the team keep an eye on?"
    )
    
    # --- THIS IS THE FIX ---
    # The nested call was a typo. This is the correct syntax.
    model = genai.GenerativeModel(
        'models/gemini-pro-latest'
    )
    
    # We are keeping the prompt inside the user query
    user_query = f"""
    {system_prompt}

    Here is the data from the PLC log analysis. Please provide your detailed report.

    Analyzed Data:
    {json.dumps(analysis_results, indent=2)}
    """

    try:
        # --- FIX 2: Changed 'await model.generate_content_async' to 'model.generate_content' ---
        response = model.generate_content(user_query)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return f"Error: Could not get AI summary. {e}"

# --- 6. Flask Routes (Unchanged) ---

@app.route('/')
def index():
    """Renders the main upload page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_logs():
    """
    This is now a FAST and SYNC route.
    It only does the Pandas analysis and loads the dashboard.
    """
    files = request.files.getlist('log_files')
    if not files or files[0].filename == '':
        return render_template('index.html', error="No files selected. Please upload at least one log file.")

    all_parsed_data = []
    file_count = 0

    for file in files:
        if file.filename:
            try:
                # Try to read as 'utf-8', fall back to 'latin-1'
                try:
                    file_contents = file.read().decode('utf-8')
                except UnicodeDecodeError:
                    file.seek(0)
                    file_contents = file.read().decode('latin-1')
            except Exception as e:
                print(f"Error reading file {file.filename}: {e}")
                return render_template('index.html', error=f"Failed to read file {file.filename}: {e}")

            try:
                # The fixed parser is called here
                parsed_data = parse_log_file(file.filename, file_contents)
                all_parsed_data.extend(parsed_data)
                file_count += 1
            except Exception as e:
                print(f"Error parsing file {file.filename}: {e}")
                return render_template('index.html', error=f"Failed to parse file {file.filename}: {e}")

    if not all_parsed_data:
        return render_template('index.html', error="No data could be parsed from the files.")

    # --- Run Analytics (Fast) ---
    master_df = pd.DataFrame(all_parsed_data)
    
    # This will now produce a dictionary with actual data
    analysis_results = run_system_analysis(master_df)
    
    # Add file stats to the results
    analysis_results['stats']['files_processed'] = file_count
    
    # Render the dashboard template, passing the analytics data
    # The AI summary is NOT generated yet.
    return render_template('dashboard.html', data=analysis_results)


# --- 7. NEW Route for on-demand AI Summary (Unchanged) ---
@app.route('/get_summary', methods=['POST'])
def get_summary():
    """
    This is a new, separate API route that the dashboard will call.
    This route's only job is to get the AI summary, which is slow.
    """
    try:
        # Get the analytics data from the dashboard's JavaScript
        analysis_data = request.json
        if not analysis_data:
            return jsonify({"summary": "Error: No analysis data received."}), 400
            
        # --- FIX 3: Removed 'asyncio.run()' and called the function directly ---
        ai_summary = get_ai_summary(analysis_data)
        
        # Return the summary as JSON
        return jsonify({"summary": ai_summary})
        
    except Exception as e:
        print(f"Error in /get_summary: {e}")
        # This will now return the *actual* error to the frontend
        return jsonify({"summary": f"Error generating summary: {e}"}), 500

# --- 8. Standard Flask Run Command (Unchanged) ---
if __name__ == '__main__':
    # This allows you to run with "python app.py"
    # The default port is 5000.
    app.run(debug=True, port=5000)