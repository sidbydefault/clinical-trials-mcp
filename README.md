# Clinical Trials MCP Server

An MCP server that helps researchers design clinical trials by analyzing historical trial patterns and matching against available patient populations.

## Overview

**What This Does:**
Input: "Design a Phase 2 diabetes trial with 80 patients"
Output: Trial design recommendations + eligibility criteria + list of 80 eligible patients to recruit

**Core Value:**
Combines historical clinical trial knowledge (45K trials from AACT database) with local patient databases to provide comprehensive trial feasibility analysis in seconds, not weeks.

## Architecture

### System Components

```
┌─────────────────────────────────────────┐
│         MCP Server (FastMCP)            │
│                                         │
│  Tool 1: search_trials                  │
│  → Lightweight browsing/exploration     │
│                                         │
│  Tool 2: analyze_trial_feasibility      │
│  → Complete design + patient matching   │
└─────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  ┌──────────┐        ┌──────────┐
  │ ChromaDB │        │Postgres  │
  │ (AACT)   │        │(Synthea) │
  │ ~45K     │        │Pluggable │
  └──────────┘        └──────────┘
```

### Two-Tool Design

1. **`search_trials`** - Lightweight browsing
   - Semantic search on clinical trials database
   - Filter by phase, condition, enrollment size
   - Quick exploration: "What trials exist for X?"

2. **`analyze_trial_feasibility`** - Comprehensive analysis
   - Find similar historical trials (RAG)
   - Generate eligibility criteria (LLM)
   - Match eligible patients (SQL)
   - Return complete feasibility report

## Key Features

- **Historical Trial Analysis**: Learn from 45K+ clinical trials (AACT database)
- **Patient Recruitment**: Identify eligible patients from your database
- **Synthetic Patient Cohorts**: Default Synthea database with realistic patient populations
- **Semantic Search**: Vector-based similarity matching using ChromaDB
- **LLM-Powered Design**: Generate appropriate eligibility criteria
- **Local Deployment**: Docker-based for data sovereignty (HIPAA-friendly)
- **Pluggable Database**: Use your own patient database or synthetic Synthea data
- **Complete Feasibility**: Get trial design + patient list in one query

## Project Structure

```
clinical-trial-mcp/
├── src/              # Core application code
├── docs/             # Documentation
├── examples/         # Sample data and setup examples
├── notebooks/        # Jupyter notebooks for experimentation
└── data/             # Data storage (gitignored)
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (recommended)
- API Keys:
  - Groq API key (for LLM analysis)
  - Google API key (for embeddings)

## Quick Start

### Option 1: Docker Deployment (Recommended)

```bash
# 1. Clone and setup
git clone <repository-url>
cd clinical-trials-mcp

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys:
# - GROQ_API_KEY=your_key_here
# - GOOGLE_API_KEY=your_key_here

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose logs -f mcp-server
```

The server will:
- Initialize PostgreSQL with Synthea synthetic patient cohorts
- Load 45K clinical trials from AACT database into ChromaDB
- Start MCP server on port 8000

### Option 2: Local Development

```bash
# 1. Install dependencies
poetry install
# or
pip install -r requirements.txt

# 2. Setup environment
cp .env.example .env
# Add your API keys

# 3. Initialize databases
python scripts/load_vector_db.py
python scripts/load_patients.py

# 4. Run server
python src/server.py
```

## Example Workflow

```
User Query:
"Design a Phase 2 cardiovascular trial for 80 patients
testing a new anti-hypertensive drug"

Server Response:
├─ Trial Design Recommendations
│  ├─ Recommended enrollment: 80-92 patients
│  ├─ Age range: 45-75 years (based on 8 similar trials)
│  └─ Estimated duration: 12-24 months
│
├─ Eligibility Criteria
│  ├─ Inclusion: 6 specific criteria
│  │  └─ Adults 45-75, Hypertension diagnosis (BP >140/90)...
│  └─ Exclusion: 10 specific criteria
│     └─ Recent MI, Severe renal impairment...
│
├─ Patient Recruitment Feasibility
│  ├─ Found: 134 eligible patients
│  ├─ Feasibility: HIGH (1.67x target ratio)
│  ├─ Demographics: 58% male, avg age 61
│  └─ Patient list with IDs and demographics
│
└─ Strategic Recommendations
   ├─ Recruitment timeline: 8-12 months
   ├─ Risk factors to consider
   └─ Next steps for protocol development
```

## Data Sources

### Clinical Trials Database (AACT)
- **Source**: AACT Database (Aggregate Analysis of ClinicalTrials.gov)
- **Dataset**: 45,000 clinical trial records
- **Content**: Trial protocols, eligibility criteria, outcomes, enrollment data
- **Storage**: ChromaDB (vector embeddings for semantic search)
- **Search**: Semantic similarity using Google Gemini embeddings (gemini-embedding-001)
- **Coverage**: Multi-phase trials across various therapeutic areas

### Patient Database (Synthea)
- **Source**: Synthea - Synthetic Patient Population Simulator
- **Dataset**: Sample of synthetic patient cohorts with realistic medical histories
- **Content**: Patient demographics, conditions, medications, observations, encounters
- **Storage**: PostgreSQL (relational database)
- **Schema**: Demographics + Conditions tables (see docs/DATABASE_SCHEMA.md)
- **Privacy**: 100% synthetic data - no real patient information
- **Pluggable**: Easily replace with your institution's actual patient database
- **Use Cases**: Testing, demos, development, and training without PHI concerns

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - Complete system architecture
- [Database Schema](docs/DATABASE_SCHEMA.md) - PostgreSQL schema details
- [Vector Store Schema](docs/VECTOR_STORE_SCHEMA.md) - ChromaDB structure
- [API Reference](docs/API_REFERENCE.md) - Tool API documentation
- [Using Custom Databases](docs/PLUGGING_YOUR_DB.md) - Connect your own patient DB

## Technology Stack

- **MCP Framework**: FastMCP
- **Vector Database**: ChromaDB (persistent local storage)
- **Relational Database**: PostgreSQL
- **LLM**: Groq (llama-3.1-70b-versatile)
- **Embeddings**: Google Gemini (gemini-embedding-001)
- **Deployment**: Docker Compose
- **Language**: Python 3.11+

## Using Your Own Patient Database

The system is designed to be **pluggable** with your institution's patient database:

1. Ensure your database has tables matching our schema:
   - `patient_demographics` (patient_id, age, gender, race, etc.)
   - `patient_conditions` (patient_id, condition, start_date, stop_date)

2. Update `DATABASE_URL` in `.env`:
   ```bash
   DATABASE_URL=postgresql://user:pass@your-host:5432/your_db
   ```

3. Restart the MCP server:
   ```bash
   docker-compose restart mcp-server
   ```

See [docs/PLUGGING_YOUR_DB.md](docs/PLUGGING_YOUR_DB.md) for detailed instructions.

## Key Design Decisions

### Why 2 Tools?
- **Tool 1 (search_trials)**: Quick browsing and exploration
- **Tool 2 (analyze_trial_feasibility)**: Complete integrated analysis

Users typically want a complete answer in one query, not decomposed into 7+ micro-tools.

### Why Local Deployment?
- **Data Sovereignty**: Healthcare data stays on-premise
- **HIPAA Compliance**: No cloud data transmission
- **Zero Cloud Costs**: No recurring API fees for vector storage
- **Institutional Flexibility**: Use your own databases

### Why Synthea Default?
- **Realistic Synthetic Data**: Safe for demos and testing
- **No PHI Risk**: No real patient data exposure
- **Easy Onboarding**: Works out-of-the-box
- **Replaceable**: Swap with real data when ready

## Development

```bash
# Install dependencies
make install

# Run tests
make test

# Lint code
make lint

# Format code
make format

# Run local development server
make run
```

## Limitations & Assumptions

- **Synthetic Data**: Default uses Synthea (realistic but not real patients)
- **Historical Trials**: Based on public trials from ClinicalTrials.gov
- **Text Matching**: Conditions matched by text (not standardized codes)
- **Active Conditions**: Assumes `stop_date IS NULL` means condition is active
- **Single Institution**: Designed for single-site (can extend to multi-site)

## Roadmap

- [ ] Multi-site feasibility analysis
- [ ] Advanced ML-based patient prioritization
- [ ] Real-time AACT database updates
- [ ] Geographic analysis (patient locations vs trial sites)
- [ ] Cost estimation and budget analysis
- [ ] Regulatory submission template generation

## Support

For questions and issues:
1. Check documentation in `docs/`
2. Review architecture decisions in `docs/ARCHITECTURE.md`
3. Open an issue on GitHub

## License

MIT
