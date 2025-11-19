# Clinical Trials MCP Server

A Model Context Protocol (MCP) server that accelerates clinical trial design by analyzing historical trial patterns and matching against available patient populations.

## What It Does

Transforms clinical trial feasibility analysis from **weeks to seconds**:

- **Input:** "Design a Phase 2 diabetes trial for 80 patients"
- **Output:** Trial design recommendations + eligibility criteria + list of eligible patients from your database

**Core Value:** Combines knowledge from 45,000+ historical clinical trials (AACT database) with local patient data to provide comprehensive feasibility analysis instantly.

---

## Key Features

- **Historical Trial Analysis** - Learn from 45K+ clinical trials from ClinicalTrials.gov
- **Patient Recruitment** - Identify eligible patients from your database using semantic matching
- **Synthetic Patient Data** - Includes realistic Synthea patient cohorts for testing
- **Semantic Search** - Vector-based similarity matching using Milvus
- **Local Deployment** - Docker-based for data sovereignty and HIPAA compliance
- **Pluggable Database** - Use your own patient database or synthetic data
- **Complete Feasibility** - Get trial design + patient list in one query

---

## Architecture

```
┌─────────────────────────────────────────┐
│        MCP Server (FastMCP)             │
│                                         │
│  Tool 1: search_trials                  │
│  → Browse and explore clinical trials   │
│                                         │
│  Tool 2: find_eligible_patients         │
│  → Match patients by criteria           │
│                                         │
│  Tool 3: analyze_trials_and_match       │
│  → Complete feasibility analysis        │
└─────────────────────────────────────────┘
            │                  │
            ▼                  ▼
    ┌──────────┐        ┌──────────┐
    │  Milvus  │        │Postgres  │
    │ (Trials) │        │(Patients)│
    │  ~45K    │        │ Synthea  │
    └──────────┘        └──────────┘
```

### Three-Tool Design

1. **`search_trials`** - Browse clinical trials database
   - Semantic search on 45K+ trials
   - Filter by phase, status, enrollment size

2. **`find_eligible_patients`** - Match patients by criteria
   - Filter by age range and conditions
   - Semantic matching using embeddings

3. **`analyze_trials_and_match_patients`** - Complete analysis
   - Find similar historical trials
   - Infer eligibility criteria
   - Match eligible patients
   - Assess feasibility (HIGH/MEDIUM/LOW)

---

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- NVIDIA GPU (optional, for faster embeddings)

---

## Quick Start with Docker

### 1. Clone and Configure

```bash
git clone https://github.com/sidbydefault/clinical-trials-mcp.git
cd clinical-trials-mcp

# Create environment file
cp .env.example .env
# Edit .env and configure as needed
```

### 2. Start Services

```bash
docker-compose up -d
```

This will:
- Initialize PostgreSQL with Synthea synthetic patient data
- Load clinical trials into Milvus vector database
- Start MCP server on port 8080

### 3. Check Status

```bash
docker-compose logs -f mcp-server
```

---

## Connecting to Claude Desktop

**Claude Desktop requires HTTPS.** We need to use **ngrok** to get a free HTTPS URL.

### Setup ngrok on GCP Server

**1. On your GCP server, install ngrok:**

```bash
# Download and install
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update
sudo apt install ngrok
```

**2. Sign up for free ngrok account (optional but recommended):**

Go to: https://dashboard.ngrok.com/signup

After signup, you'll get an authtoken. Run:
```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

**3. Start ngrok tunnel:**

```bash
ngrok http 8080
```

**You'll see output like:**
```
Forwarding   https://abc123-xy.ngrok-free.app -> http://localhost:8080
```

**4. Copy that HTTPS URL** (e.g., `https://abc123-xy.ngrok-free.app`)

**5. In Claude Desktop, configure the MCP server:**

Open Claude Desktop settings and add:
```json
{
  "mcpServers": {
    "clinical-trials": {
      "url": "https://abc123-xy.ngrok-free.app/sse"
    }
  }
}
```

**6. Restart Claude Desktop**

---

## Example Usage

### Query
```
Design a Phase 2 cardiovascular trial for 80 patients
testing a new anti-hypertensive drug
```

### Response
```
Trial Design Recommendations
├─ Recommended enrollment: 80-92 patients
├─ Age range: 45-75 years (based on 8 similar trials)
└─ Estimated duration: 12-24 months

Eligibility Criteria
├─ Inclusion: Adults 45-75, Hypertension (BP >140/90)...
└─ Exclusion: Recent MI, Severe renal impairment...

Patient Recruitment Feasibility
├─ Found: 134 eligible patients
├─ Feasibility: HIGH (1.67x target enrollment)
├─ Demographics: 58% male, avg age 61
└─ Patient list with IDs and contact info
```

---

## Data Sources

### Clinical Trials (AACT Database)
- **Source:** ClinicalTrials.gov via AACT database
- **Dataset:** 45,000+ clinical trial records
- **Storage:** Milvus vector database
- **Search:** Semantic + BM25 hybrid search

### Patient Database (Synthea)
- **Type:** 100% synthetic patient data (HIPAA-friendly)
- **Content:** Demographics, conditions, medications, encounters
- **Storage:** PostgreSQL
- **Privacy:** No real patient information - safe for demos and testing

---

## Using Your Own Patient Database

The system is designed to be **pluggable**. To use your institutional database:

1. **Ensure your database has these tables:**
   - `patients_demographics` (patient_id, age, gender, race, etc.)
   - `patients_conditions` (patient_id, condition)

2. **Update `DATABASE_URL` in `.env`:**
   ```bash
   DATABASE_URL=postgresql://user:pass@your-host:5432/your_db
   ```

3. **Restart services:**
   ```bash
   docker-compose restart mcp-server
   ```

See [docs/PLUGGING_YOUR_DB.md](docs/PLUGGING_YOUR_DB.md) for detailed instructions.

---

## Technology Stack

- **MCP Framework:** FastMCP (Anthropic)
- **Vector Database:** Milvus (hybrid search)
- **Relational Database:** PostgreSQL
- **Embeddings:** Qwen3-Embedding-4B, GTE-Multilingual
- **Container:** Docker with GPU support
- **Language:** Python 3.11+

---

## Project Structure

```
clinical-trials-mcp/
├── src/                  # Core application
│   ├── server.py         # MCP server with 3 tools
│   ├── database.py       # PostgreSQL interface
│   ├── vectorstore.py    # Milvus interface
│   └── config.py         # Configuration
├── database_creation/    # Database setup scripts
├── docs/                 # Documentation
├── docker-compose.yaml   # Container orchestration
└── pyproject.toml        # Python dependencies
```

---

## Development

```bash
# Install dependencies
poetry install
# or
pip install -r requirements.txt

# Initialize databases
python database_creation/create_db.py
python database_creation/create_vectordb.py

# Run server locally
python src/run_server.py
```

---

## Why Local Deployment?

- **Data Sovereignty** - Healthcare data stays on-premise
- **HIPAA Compliance** - No cloud data transmission
- **Zero Cloud Costs** - No recurring API fees
- **Institutional Control** - Use your own databases

---

## Limitations

- **Synthetic Default Data** - Uses Synthea (realistic but not real patients)
- **Historical Trials Only** - Based on public ClinicalTrials.gov data
- **Text-Based Matching** - Conditions matched by text similarity (not standardized codes)
- **Single Institution** - Designed for single-site deployment

---

## Roadmap

- [ ] Add Evaluations for Hybrid RAG
- [ ] Real-time AACT database updates


---

## Support

For questions and issues:
1. Check documentation in `docs/`
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
3. Open an issue on GitHub

---

## License

MIT

