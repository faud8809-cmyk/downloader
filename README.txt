Media Downloader - Flask starter project

Included:
- Responsive public landing page
- Direct video file download route (public HTTP(S) URLs, limited to 100 MB)
- Admin login
- API settings panel (name, platform, endpoint, key, enabled toggle)
- API configuration saved locally in api_settings.json
- API credentials are masked in the admin list

Run on Windows:
1. Extract this ZIP.
2. Open the extracted folder in File Explorer.
3. Click address bar, type cmd, press Enter.
4. Run:
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   py app.py
5. Visit http://127.0.0.1:5000

Admin:
Visit http://127.0.0.1:5000/admin
Default password: change-this-password

Set a stronger password before use:
In the same CMD window, before running the server:
set ADMIN_PASSWORD=your-strong-password
set FLASK_SECRET_KEY=replace-with-a-long-random-secret
Then run py app.py

Important:
- API entries are stored, but no generic API call is implemented. Each API provider has its own format and needs a provider-specific adapter.
- This starter supports direct video-file links only, not social media page extraction.
- Use only videos you own or have permission to download and follow platform/provider terms.
- This is a local development project, not production-ready. Do not expose Flask's development server to the public internet.
