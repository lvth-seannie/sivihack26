# [SiviHack26] Hackathon Tech Stack & Guide

---

## 1. The Final Stack

| Layer | Choice | Role |
|---|---|---|
| Frontend | React (Vite)  | UI, hosted as static build |
| Frontend Hosting | Vercel | Instant deploys, preview URLs per branch |
| Backend Framework | Django + Django Ninja | REST API, async-friendly, auto Swagger docs |
| Backend Hosting | Render (Web Service) | Runs the Django app |
| Database | Neon Postgres | Structured data — users, sessions, app data |
| File / Object Storage | Cloudflare R2 | Uploads, generated files, exports |
| Uptime / Keep-warm | UptimeRobot | Pings `/api/health` every 5 min |
| AI Provider | Anthropic or OpenAI API (your keys) | Swappable behind one wrapper module |

```mermaid
flowchart LR
    A[React + Vite] -->|Vercel| B((Browser / Judges))
    A -->|fetch /api| C[Django + Ninja]
    C -->|Render| D[(Neon Postgres)]
    C --> E[(Cloudflare R2)]
    C --> F[LLM API]
    G[UptimeRobot] -->|ping every 5 min| C
```

## 2. Repo structure

```
project-root/
├── frontend/ # React + Vite
│ ├── src/
│ ├── .env.example
│ └── vercel.json
├── backend/ # Django + Ninja
│ ├── config/ # settings, urls, wsgi/asgi
│ ├── core/ # health check, shared utils
│ ├── api/ # your feature endpoints (topic-specific)
│ ├── ai_client/ # LLM provider wrapper (topic-agnostic)
│ ├── storage_client/ # R2 upload/download helpers
│ ├── manage.py
│ ├── requirements.txt
│ ├── render.yaml
│ └── .env.example
└── README.md
```

