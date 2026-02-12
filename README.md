# LifeLine Blood Donations

A Django web app for managing blood donation workflows, including donors, patients, and hospital interactions.

## Tech Stack
- Python
- Django
- SQLite (default for local development)
- HTML/CSS/JS

## Local Setup (Defaults)
1. Create and activate a virtual environment.
2. Install dependencies. If you do not have a `requirements.txt` yet, install Django:
   - `pip install django`
   - (Optional) `pip freeze > requirements.txt`
3. Run migrations:
   - `python manage.py migrate`
4. Create an admin user:
   - `python manage.py createsuperuser`
5. Start the server:
   - `python manage.py runserver`

## Project Structure
- `core/`: main app (models, views, forms, migrations)
- `lifeline_project/`: Django project settings and URLs
- `templates/`: HTML templates
- `core/static/`: static assets

## Notes
- `db.sqlite3` is excluded from version control by `.gitignore`.
- `sent_emails/` is excluded from version control by `.gitignore`.
