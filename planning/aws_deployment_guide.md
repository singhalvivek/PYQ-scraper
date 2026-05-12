# Running the Scraper on AWS EC2

If you want to close your laptop and let an AWS server handle the scraping overnight, you can deploy this script to an Amazon EC2 instance. 

Here is the step-by-step guide to setting it up:

## Step 1: Connect to your Instance
Open PowerShell on your Windows machine and connect using SSH and your downloaded `.pem` key:
```bash
ssh -i "E:\Downloads\pyq-scraper.pem" ubuntu@54.80.146.204
```

## Step 2: Setup the Server & Upload Code
**INSIDE THE SSH SESSION (Ubuntu):**
Update the packages and install python virtual environment tools:
```bash
sudo apt update
sudo apt install python3-venv python3-pip zip -y
```

**ON YOUR LOCAL WINDOWS MACHINE:**
Instead of setting up Git, the easiest way to move your code is to zip your local files and transfer them. 
Open a **new** PowerShell window, navigate to your `PYQ-scraper` folder, and run:
```bash
# Don't zip the venv or pycache (In powershell)
Compress-Archive -Path scraper_db.py, requirements.txt, .env -DestinationPath scraper_code.zip

# Send it to AWS using SCP
scp -i "E:\Downloads\pyq-scraper.pem" scraper_code.zip ubuntu@54.80.146.204:~/
```

## Step 3: Run the Script in the Background
Back in your **AWS SSH session (Ubuntu)**, unzip the code, set up the environment, and run it:
```bash
# Unzip the code
unzip scraper_code.zip -d pyq-scraper
cd pyq-scraper

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# kill previous instance of scraper_db.py
pkill -f scraper_db.py

# Install dependencies
pip install -r requirements.txt

# Run the script in the background using nohup
nohup python3 scraper_db.py > scraper.log 2>&1 &
```

### What does `nohup` do?
`nohup` (no hang up) runs your script in the background and prevents it from stopping when you disconnect your SSH session. It redirects all output (including those 404 errors) to a file named `scraper.log`.

## Step 4: Go to Sleep!
You can safely type `exit` to close your SSH connection and turn off your laptop. The EC2 instance will keep running the script.

**In the morning:**
1. Connect back to the EC2 instance via SSH.
2. Check the logs to see if it finished:
   ```bash
   cat ~/pyq-scraper/scraper.log
   ```
3. Check your MongoDB Atlas and S3 buckets to see all your imported data!
