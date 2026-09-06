# sivihack26



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