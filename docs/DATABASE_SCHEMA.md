# Database Schema

This document describes the PostgreSQL database schema for the Clinical Trials MCP system.

## Overview

The database uses PostgreSQL with SQLModel/SQLAlchemy for ORM. It stores patient demographics, medical conditions, and clinical trial information.

## Tables

### patients_demographics

Stores patient demographic information from Synthea synthetic data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| patient_id | VARCHAR | PRIMARY KEY, INDEX | Unique patient identifier |
| gender | VARCHAR | NOT NULL | Patient gender |
| age | INTEGER | NOT NULL, INDEX | Patient age in years |
| name | VARCHAR | NOT NULL | Patient full name |
| marital | VARCHAR | NOT NULL | Marital status |
| race | VARCHAR | NOT NULL | Patient race |
| ethnicity | VARCHAR | NOT NULL | Patient ethnicity |
| ssn | VARCHAR | NOT NULL | Social security number |
| address | VARCHAR | NOT NULL | Patient address |

**Indexes:**
- Primary key on `patient_id`
- Index on `age` for age-based queries

**Relationships:**
- One-to-many with `patients_conditions`

### patients_conditions

Stores patient medical conditions with a many-to-one relationship to patients.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing condition record ID |
| patient_id | VARCHAR | FOREIGN KEY, INDEX | References `patients_demographics(patient_id)` |
| conditions | VARCHAR | NOT NULL, INDEX | Medical condition description |

**Indexes:**
- Primary key on `id`
- Foreign key index on `patient_id`
- Index on `conditions` for condition lookups

**Relationships:**
- Many-to-one with `patients_demographics` via `patient_id`

### aact_clinical_trials

Stores AACT (Aggregate Analysis of ClinicalTrials.gov) clinical trial data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| nct_id | VARCHAR | PRIMARY KEY, INDEX | NCT identifier (e.g., NCT12345678) |
| text | TEXT | NOT NULL | Full clinical trial document text |
| conditions | VARCHAR | NOT NULL | Comma-separated list of conditions studied |

**Indexes:**
- Primary key on `nct_id`

**Notes:**
- The `text` field contains the complete trial documentation including eligibility criteria, study design, outcomes, etc.
- The `conditions` field is extracted from trial metadata and stored as a comma-separated string

## Data Loading Process

The database is initialized using `database_creation/create_db.py`:

1. **Drop existing tables** (if any)
2. **Create fresh tables** using SQLModel metadata
3. **Load patient demographics** from Parquet file
   - Batch size: 1000 records
   - Duplicate entries are skipped
4. **Load patient conditions** from Parquet file
   - Batch size: 1000 records
   - Validates patient existence via foreign key
   - Skips conditions for non-existent patients
5. **Load clinical trials** from JSON file
   - Batch size: 1000 records
   - Parses metadata to extract conditions
   - Stores full document text

## Configuration

Database connection is configured via environment variable:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

Set this in your `.env` file before running the database creation script.

## Usage

### Creating the Database

```bash
cd database_creation
python create_db.py demographics.parquet conditions.parquet clinical_trials.json
```

### Sample Queries

**Find patient by ID:**
```sql
SELECT * FROM patients_demographics WHERE patient_id = 'patient-123';
```

**Get all conditions for a patient:**
```sql
SELECT c.conditions
FROM patients_conditions c
WHERE c.patient_id = 'patient-123';
```

**Find trials by condition:**
```sql
SELECT nct_id, conditions
FROM aact_clinical_trials
WHERE conditions LIKE '%diabetes%';
```

**Patient demographics with conditions (JOIN):**
```sql
SELECT p.patient_id, p.name, p.age, c.conditions
FROM patients_demographics p
LEFT JOIN patients_conditions c ON p.patient_id = c.patient_id;
```

## Runtime Integration

The database is accessed at runtime through `src/database.py`, which provides:

- **Connection pooling** via SQLModel engine
- **Patient matching** using semantic similarity of conditions
- **Embedding cache** for condition embeddings (GTE-Multilingual model)
- **Cosine similarity scoring** with 0.75 threshold for matching

See `src/database.py` for the full database interface implementation.
