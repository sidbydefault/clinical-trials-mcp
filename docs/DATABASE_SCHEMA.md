# Database Schema

This document describes the database schema for the Clinical Trials MCP system.

## Tables

### patients

Stores patient demographic information.

| Column | Type | Description |
|--------|------|-------------|
| patient_id | VARCHAR(50) PRIMARY KEY | Unique patient identifier |
| age | INTEGER | Patient age in years |
| gender | VARCHAR(20) | Patient gender |
| race | VARCHAR(50) | Patient race/ethnicity |
| state | VARCHAR(2) | Two-letter state code |
| zip_code | VARCHAR(10) | ZIP/postal code |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### conditions

Stores patient medical conditions.

| Column | Type | Description |
|--------|------|-------------|
| condition_id | VARCHAR(50) PRIMARY KEY | Unique condition record identifier |
| patient_id | VARCHAR(50) FOREIGN KEY | References patients(patient_id) |
| condition_code | VARCHAR(20) | Medical condition code (ICD-10, SNOMED, etc.) |
| condition_name | VARCHAR(255) | Human-readable condition name |
| onset_date | DATE | Date condition was diagnosed/onset |
| status | VARCHAR(20) | Current status (active, resolved, etc.) |
| severity | VARCHAR(20) | Condition severity (mild, moderate, severe) |
| created_at | TIMESTAMP | Record creation timestamp |

### clinical_trials

Stores clinical trial information and eligibility criteria.

| Column | Type | Description |
|--------|------|-------------|
| trial_id | VARCHAR(50) PRIMARY KEY | Unique trial identifier (NCT number) |
| title | TEXT | Trial title |
| description | TEXT | Brief trial description |
| phase | VARCHAR(20) | Trial phase (Phase I, II, III, IV) |
| status | VARCHAR(50) | Trial status (recruiting, active, completed) |
| sponsor | VARCHAR(255) | Trial sponsor organization |
| conditions_studied | TEXT | Conditions being studied (JSON array) |
| min_age | INTEGER | Minimum age requirement (years) |
| max_age | INTEGER | Maximum age requirement (years) |
| eligible_genders | VARCHAR(50) | Eligible genders (all, male, female) |
| inclusion_criteria | TEXT | Inclusion criteria (full text) |
| exclusion_criteria | TEXT | Exclusion criteria (full text) |
| locations | TEXT | Trial locations (JSON array) |
| start_date | DATE | Trial start date |
| completion_date | DATE | Expected/actual completion date |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

## Indexes

### patients
- `idx_patients_age` on `age`
- `idx_patients_state` on `state`
- `idx_patients_gender` on `gender`

### conditions
- `idx_conditions_patient` on `patient_id`
- `idx_conditions_code` on `condition_code`
- `idx_conditions_status` on `status`

### clinical_trials
- `idx_trials_status` on `status`
- `idx_trials_phase` on `phase`
- `idx_trials_conditions` on `conditions_studied` (GIN/JSONB for PostgreSQL)

## Relationships

```
patients (1) ----< (many) conditions
```

Clinical trials are matched to patients based on:
- Demographics (age, gender, location)
- Medical conditions
- Eligibility criteria (via vector similarity search)

## Notes

- All timestamps use UTC
- JSON fields are stored as TEXT in SQLite, JSONB in PostgreSQL
- Patient data is synthetic and for demonstration purposes only
- Trial data should be sourced from ClinicalTrials.gov or similar registries
