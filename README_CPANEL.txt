cPanel Setup Python App deployment (Flask)

1. In cPanel -> Setup Python App, create an application. Choose a supported Python version (3.10+ if available).
2. Set Application root to a folder such as media_downloader (NOT public_html). Choose your desired Application URL.
3. After creating the app, open its Application root folder in File Manager and upload this ZIP, then Extract. Files should be directly in the application root: app.py, passenger_wsgi.py, requirements.txt, templates/, static/.
4. In the Python app page, set Startup file: passenger_wsgi.py and Entry point: application (if these fields are shown).
5. Install dependencies using the app's virtualenv command shown in cPanel: pip install -r requirements.txt.
6. Set environment variables in the app settings if available: ADMIN_PASSWORD to a strong, unique password; FLASK_SECRET_KEY to a long random secret. Do NOT keep the default admin password.
7. Click Restart. Visit the application URL. Admin login: /admin.

Note: This demo currently supports direct video-file URLs only; the API settings panel stores API configurations but does not implement provider-specific downloading. Only download content you own or have permission to download, and use platform APIs according to their terms.
