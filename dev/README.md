# sivihack26

## Workflow Overview
```mermaid
flowchart TD
    %% Define styles
    classDef frontend fill:#3178C6,stroke:#fff,stroke-width:2px,color:#fff;
    classDef backend fill:#092E20,stroke:#fff,stroke-width:2px,color:#fff;
    classDef database fill:#3EBD93,stroke:#fff,stroke-width:2px,color:#1C1C1C;
    classDef ai fill:#74AA9C,stroke:#fff,stroke-width:2px,color:#1C1C1C;
    classDef user fill:#F9F9F9,stroke:#333,stroke-width:2px;

    %% Nodes
    User([🧑‍💻 User / Hackathon Judge]):::user
    
    subgraph Vercel [Frontend: Vercel]
        UI[⚛️ React Vite UI]:::frontend
    end
    
    subgraph Render [Backend: Render.com]
        Django[🐍 Django API]:::backend
        AILogic[🧠 AI Prompt Engine]:::backend
        Django <--> AILogic
    end
    
    subgraph Supabase [Database: Supabase]
        Postgres[(🐘 PostgreSQL)]:::database
    end
    
    subgraph External [External Services]
        LLM[🤖 OpenAI / Claude API]:::ai
    end

    %% Connections
    User -->|Clicks 'Analyze' / Enters Data| UI
    UI <-->|HTTP POST / JSON Payload| Django
    Django <-->|psycopg2 / SQL Queries| Postgres
    AILogic <-->|Context & API Key| LLM
    UI -->|Displays AI Results| User
```

## 1. Setup Frontend
## 2. Setup Backend

### 2.1 Initialize the Environment

#### For MacOS
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate 
```

#### For Windows
```powershell
cd backend
python3 -m venv .venv
.venv\Scripts\Activate 
```

### 2.2 Install Core Dependencies

```bash
pip install django django-ninja django-cors-headers psycopg2-binary dj-database-url python-dotenv
```

### 2.3 Create the Django Project

```bash
django-admin startproject core .
```

### 2.4 Create backend/.env
To set up environment variables (store Supabase credentials)
```python
DATABASE_URL=postgresql://postgres.klkonowudkyejakogfth:[password]@aws-1-eu-west-1.pooler.supabase.com:6543/postgres
```

### 2.5 Adjust core/settings.py 
To connect database & allow React to communicate with API

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders', # Add this
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # MUST be at the very top
    'django.middleware.security.SecurityMiddleware',
    # ... keep the rest exactly the same
]

# Allow React (running on localhost:5173) to fetch data from Django
CORS_ALLOW_ALL_ORIGINS = True
```

Replace the default SQLite DATABASES block with Supabase:
```python
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
```

### 2.6 Migrate & Run
```bash
python manage.py migrate
python manage.py runserver
```
Successful setup would look like this:
```bash
(.venv) seannie@Seannies-Mac-Pro backend % python manage.py migrate
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying sessions.0001_initial... OK

(.venv) seannie@Seannies-Mac-Pro backend % python manage.py runserver
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
September 06, 2026 - 09:17:54
Django version 4.2.30, using settings 'core.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```