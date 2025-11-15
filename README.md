PLC Log Analytics Dashboard (with AI Summary)


This is a Flask web application designed to help maintenance teams and plant managers analyze complex PLC (Programmable Logic Controller) log files.

It aggregates data from multiple log files, performs a system-wide analysis to identify critical faults, and uses the Google Gemini API to generate an expert, human-readable summary of system health and actionable fixes.



Core Features

- Drag-and-Drop File Upload: A simple web interface to upload multiple .txt or .csv log files at once.
- Robust Log Parser: A custom Python parser built to handle complex PLC log formats, including alarms with component IDs (e.g., K_"db5005".M401...) and simple system alarms.
- Pandas-Powered Analytics: The backend uses Pandas to instantly aggregate all log entries and calculate key statistics:
    - Top 10 Most Frequent Alarms
    - Top 10 Most Failing Components
    - Connection Issues by Logger
    - An Error-over-Time Timeline
- AI-Powered Summary: Uses the Google Gemini API with a specialized prompt (acting as a "Senior PLC Maintenance Analyst") to generate an Executive Summary and Actionable Fixes for non-technical stakeholders.
- Interactive Dashboard: Uses Chart.js to visualize all analytics in a clean, easy-to-read dashboard.
- Smart Loading: The dashboard loads instantly with all charts. The AI summary is then fetched separately on-demand, preventing page timeouts on large analyses.

How It Works

The application operates in two stages to ensure a fast user experience:

1.  Stage 1: Instant Analysis (Server-Side)
    - You upload your log files to the /analyze route.
    - The Flask server parses all files into a single, massive Pandas DataFrame.
    - The run_system_analysis function crunches the data to find top alarms, components, etc.
    - The server *immediately* renders the dashboard.html template, passing all this data to the charts.

2.  Stage 2: On-Demand AI Summary (Client-Side)
    - Once the dashboard page loads, a JavaScript function automatically sends the analysis data (the charts and stats) to a separate API endpoint: /get_summary.
    - This route is the only part of the app that contacts the Google Gemini API.
    - The AI generates the detailed report, which is then sent back to the dashboard and displayed in the "AI Summary" card.

This two-step process ensures the user isn't stuck on a loading screen waiting for the (slower) AI API call to finish.

Technology Stack

- Backend: Flask
- Data Analysis: Pandas
- AI: Google Gemini (google-generativeai)
- Frontend: HTML, Chart.js, JavaScript
- Environment: python-dotenv

---

Installation & Setup

You must have Python 3.9 or newer to install the google-generativeai library.

1. Clone the Repository

```bash
git clone [https://github.com/YOUR_USERNAME/plc-log-analytics-dashboard.git](https://github.com/YOUR_USERNAME/plc-log-analytics-dashboard.git)
cd plc-log-analytics-dashboard
