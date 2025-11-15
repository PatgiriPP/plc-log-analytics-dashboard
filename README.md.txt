1. Create the environment (this only needs to be done once):

Bash :

python3 -m venv venv
Activate the environment. This is crucial.

On Windows (PowerShell):

PowerShell

.\venv\Scripts\Activate.ps1
On macOS/Linux:

Bash :

source venv/bin/activate
You'll know it's active because your terminal prompt will change to show (venv).

2. Install Dependencies
While your (venv) is active, run this command in the same Code terminal to install all the required libraries:

Bash

pip install -r requirements.txt

3. Create Your .env File for the API Key
You will do this using the Code File Explorer.

In the File Explorer panel on the left, right-click in the empty space.

Select New File.

Name the file exactly .env (starting with a dot).

Open the .env.example file to see the format.

In your new .env file, add your API key:

GEMINI_API_KEY="YOUR_API_KEY_GOES_HERE"
Save the .env file. app.py is designed to automatically load this file.

4. Run the Application
Now you're ready to start the server.

Make sure your (venv) is still active in the Code terminal.

Run the app.py file directly:

Bash :

python app.py
