# AI Email Generator

A Django web application that writes professional emails with the help of an AI (LLM) API.
The user enters the purpose, recipient, tone, language and key points; the AI returns a **subject** and a **body**,
which can be edited, improved, shortened, made more formal/friendly, regenerated, copied and saved.

**Tech stack:** Python, Django, MySQL, HTML, CSS, JavaScript, an OpenAI-compatible AI API.

## Features

- Registration, login, logout (Django's built-in authentication + password validation)
- Dashboard with live statistics (total emails, emails generated today, recent emails) from MySQL
- AI email generation: purpose (incl. custom), recipient, tone, language (English / Hindi / Hinglish), key points, extra instructions
- Editor with **Copy subject / Copy email / Save**
- Working AI buttons: **Improve, Make Shorter, Make More Formal, Make Friendly, Regenerate**
- Email history with search (subject, purpose), filters (purpose, tone, date), reset, pagination
- View / edit / delete (POST + confirmation) / copy / reuse-as-template
- Every user sees only their own emails
- Django admin for users and generated emails
- Friendly errors for: invalid login, invalid form data, missing API key, API failure, timeout, database problems
- Responsive layout (desktop, laptop, mobile)

## Project structure

```
AI-Email-Generator/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── db/setup_mysql.sql          # creates the MySQL database and user
│   ├── project/                    # settings, urls, wsgi, asgi
│   └── email_generator/            # the app
│       ├── models.py               # GeneratedEmail model
│       ├── forms.py                # register / generate / edit / filter forms
│       ├── views.py                # all page logic
│       ├── services.py             # AI API call + prompt + response parsing
│       ├── urls.py, admin.py, tests.py
│       ├── migrations/
│       └── management/commands/seed_demo_emails.py   # optional demo data
├── templates/                      # HTML templates
├── static/                         # css/style.css, js/main.js
├── requirements.txt
├── .gitignore
└── README.md
```

## How it works

```
User form -> Django view -> services.generate_email() -> AI API
          -> parse "SUBJECT: ... BODY: ..." -> save GeneratedEmail in MySQL -> editor page
```

The prompt tells the AI to answer in a fixed `SUBJECT:` / `BODY:` format. `services.parse_email()` splits that reply.
The AI buttons send the current text to `/emails/<id>/ai/` (a small JSON endpoint) and put the AI's answer back into the editor;
nothing is overwritten in the database until you press **Save Email**.

## Requirements

- Python 3.10 or newer
- MySQL Server 8.x (with the `mysql` command available in your PATH)
- An API key for an OpenAI-compatible AI service (see "AI API setup")

## Installation (Windows PowerShell)

```powershell
# 1. Go to the project folder
cd AI-Email-Generator

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate
#    If PowerShell blocks activation, run once:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Install packages
pip install -r requirements.txt
```

If `mysqlclient` fails to install, upgrade pip first (`python -m pip install --upgrade pip`) and use a supported
Python version (3.10 - 3.13). Recent versions ship Windows wheels, so no compiler is normally needed.

## MySQL setup

1. Open `backend\db\setup_mysql.sql` and change `ChangeThisPassword123!` to a password of your choice.
2. Run the script as the MySQL root user:

```powershell
Get-Content backend\db\setup_mysql.sql | mysql -u root -p
```

(In Command Prompt you can use `mysql -u root -p < backend\db\setup_mysql.sql`.)

This creates the database `ai_email_generator` (utf8mb4, so Hindi text works) and the user `email_user`.
Prefer doing it by hand? Run these inside the `mysql` shell:

```sql
CREATE DATABASE ai_email_generator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'email_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ai_email_generator.* TO 'email_user'@'localhost';
GRANT ALL PRIVILEGES ON `test_ai_email_generator`.* TO 'email_user'@'localhost';
FLUSH PRIVILEGES;
```

## Configure the .env file

```powershell
cd backend
copy .env.example .env
notepad .env
```

Fill in `DB_PASSWORD` (same as in MySQL), `AI_API_KEY`, and a `SECRET_KEY`. To generate a secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

The `.env` file is listed in `.gitignore`, so your keys never go to GitHub.

## AI API setup

The app calls any **OpenAI-compatible chat-completions API**. Configure it with three values in `.env`:

| Variable      | Meaning                                  | Example                                               |
|---------------|------------------------------------------|-------------------------------------------------------|
| `AI_API_KEY`  | Your secret key                          | `sk-...`                                              |
| `AI_API_URL`  | Chat-completions endpoint                | `https://api.openai.com/v1/chat/completions`          |
| `AI_MODEL`    | Model name offered by that provider      | `gpt-4o-mini`                                         |

Other providers with OpenAI-compatible endpoints (check their documentation for the current URL and model names):

- **Groq:** `https://api.groq.com/openai/v1/chat/completions`
- **Google Gemini:** `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`

Only the key, URL and model in `.env` change; no code changes are needed. Restart the server after editing `.env`.

## Run the project

```powershell
cd backend
python manage.py makemigrations     # nothing to do if migrations are up to date
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ to use the app and http://127.0.0.1:8000/admin/ for the admin panel.

## Optional demo data

The app starts with an empty database. To add a demo user with a few sample emails (no AI call is made):

```powershell
python manage.py seed_demo_emails
```

Login: `demo` / `Demo@12345`. Use `--username` and `--password` to change them.

## Run the tests

```powershell
python manage.py test
```

The tests mock the AI call, so no API key or internet is needed. Django creates a temporary `test_ai_email_generator`
database (the SQL script above grants the permission for this).

## Troubleshooting

| Problem | Fix |
|---|---|
| "The AI service is not configured yet" | `AI_API_KEY` is empty in `backend\.env`. Add it and restart the server. |
| "The AI service rejected the request" | Wrong key, or the model name is not available for your account. |
| "usage limit was reached" | Provider rate limit or quota; wait or check your plan. |
| `Access denied for user` | `DB_USER` / `DB_PASSWORD` in `.env` do not match the MySQL user. |
| `Unknown database` | Run the MySQL setup step. |
| CSS not loading | Run from the `backend` folder with `DEBUG=True`. |

Technical details of any AI/database failure are written to the server console only, never shown to users.
