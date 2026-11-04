# Trip Draft - System Architecture Diagram

Status: Proposed architecture. Only the `/chat` and `/health` endpoints and the Gemini client are implemented and verified (Week 5 backend demo). All other components are planned.

```mermaid
flowchart LR
  subgraph CLIENT[Browser]
    UI[React UI: chat, itinerary view, controls - PLANNED]
  end
  subgraph BACKEND[FastAPI backend]
    API[POST chat and GET health - IMPLEMENTED, VERIFIED]
    INTENT[Input validation and intent handling - PLANNED]
    FILTER[Rule-based filtering and recommendation - PLANNED]
    PROMPT[Prompt builder: filtered records only - PLANNED]
    LLMC[LLM client for Gemini - IMPLEMENTED, VERIFIED]
    VAL[Output validator: record IDs and prices - PLANNED]
    ERR[Error handler and rule-based fallback - PLANNED]
    subgraph UCA[User Control and Agency enforcement - PLANNED]
      G1[Gate 1: review proposed itinerary]
      G2[Gate 2: preview changes]
      G3[Gate 3: apply, or keep previous plan, and final confirmation]
      G4[Gate 4: Undo and Redo]
    end
    HIST[JSON event log for Undo and Redo - PLANNED]
  end
  DB[(SQLite dataset: source of truth - PENDING actual data)]
  ENV[Environment variables: API key, model name]
  LLM[Hosted LLM API: Google Gemini, external]
  HUMAN[Human handover - PLANNED, channel not configured]

  UI -->|request| API
  API --> INTENT
  INTENT --> FILTER
  FILTER -->|query| DB
  DB -->|matching records| FILTER
  FILTER --> PROMPT
  PROMPT --> LLMC
  ENV -.->|key read server-side only| LLMC
  LLMC -->|filtered records and user intent| LLM
  LLM -->|structured output| LLMC
  LLMC --> VAL
  VAL -->|check IDs and prices| DB
  VAL -->|valid| G1
  VAL -->|invalid| ERR
  LLMC -->|timeout or API error| ERR
  ERR -->|fallback options from dataset| G1
  ERR -.->|unresolved| HUMAN
  G1 --> G2
  G2 --> G3
  G3 -->|logged commit| HIST
  G4 <-->|restore or replay| HIST
  G1 -->|response| API
  G3 -->|response| API
  G4 -->|response| API
  API -->|response| UI

  classDef verified fill:#d4edda,stroke:#155724,color:#000;
  classDef planned fill:#eeeeee,stroke:#777,stroke-dasharray:5 5,color:#000;
  classDef ctrl fill:#d1ecf1,stroke:#0c5460,color:#000;
  classDef ext fill:#f8d7da,stroke:#842029,color:#000;
  class API,LLMC verified;
  class UI,INTENT,FILTER,PROMPT,VAL,ERR,HIST,HUMAN,DB planned;
  class G1,G2,G3,G4 ctrl;
  class LLM,ENV ext;
```

## Explanation

The React UI talks only to the FastAPI backend; there is no frontend-to-LLM connection, and the API key is read from environment variables on the server. The backend filters the SQLite dataset first and sends only those records to the model. Model output must be structured and is validated against the dataset; invalid IDs or prices are rejected and routed to error handling and the rule-based fallback. Valid results pass through the User Control and Agency gates (review, preview, apply or keep previous plan, final confirmation, and reversible Undo/Redo backed by the event log). Green nodes are implemented and verified, grey nodes are planned, and red nodes are external or configuration dependencies.
