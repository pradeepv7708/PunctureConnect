# PunctureConnect

A responsive, animated Flask + MySQL prototype for discovering puncture repair shops and sending service requests.

## Features
- Dark premium black/neon-green interface
- Responsive desktop and mobile layout
- CSS keyframe animations, reveal-on-scroll and hover effects
- Leaflet map with OpenStreetMap tiles
- Browser geolocation (requires localhost or HTTPS and user permission)
- Shop filtering and sorting
- Customer/provider account roles
- Password hashing
- Booking requests and customer booking history
- Sample Erode shop records seeded automatically

## Requirements
- Python 3.10+
- MySQL Server
- A modern browser

## Setup (Linux / Ubuntu)
```bash
# 1. Open the project folder
cd punctureconnect

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install packages
pip install -r requirements.txt

# 4. Configure MySQL credentials
cp .env.example .env
```

Edit `.env` with your MySQL username and password. Export the values before running, or load them with your preferred environment-variable tool. For a quick local run:
```bash
export SECRET_KEY='use-a-long-random-value'
export DB_HOST='localhost'
export DB_USER='root'
export DB_PASSWORD='your_mysql_password'
export DB_NAME='punctureconnect'
```

Make sure MySQL is running:
```bash
sudo systemctl start mysql
```

Run the app:
```bash
python app.py
```
Open http://127.0.0.1:5000

The app creates the `punctureconnect` database and tables and inserts demonstration shops on first run.

## Important prototype notes
- The shop list includes demonstration records around Erode. Verify and replace these with real providers before public launch.
- The booking form currently sends a request and stores it in MySQL. Provider notifications, live status updates, payment processing and production-grade provider workflows are not included yet.
- The provider role is collected at registration but provider-specific management screens are intentionally not included in this first version.
- Map tiles and fonts are loaded from third-party services, so an internet connection is needed for those visual assets.
- Use HTTPS for deployment and browser geolocation. Never publish your `.env` file or real database credentials.
