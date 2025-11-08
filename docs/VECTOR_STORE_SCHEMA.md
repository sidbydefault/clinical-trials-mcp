# Vector Store Schema

This document describes the vector store schema used for semantic search and trial matching.

## Overview

The vector store uses ChromaDB to enable semantic search of clinical trials based on:
- Trial descriptions and purposes
- Inclusion and exclusion criteria
- Medical conditions being studied

## Collections

### trial_embeddings

Primary collection for clinical trial semantic search.

#### Metadata Schema

Each vector embedding includes the following metadata:

| Field | Type | Description |
|-------|------|-------------|
| trial_id | string | NCT number or unique trial identifier |
| title | string | Trial title |
| phase | string | Trial phase (Phase I, II, III, IV) |
| status | string | Trial status (recruiting, active, etc.) |
| conditions | string[] | List of conditions studied |
| min_age | int | Minimum age requirement |
| max_age | int | Maximum age requirement |
| eligible_genders | string | Eligible genders |
| locations | string[] | Trial locations |
| embedding_type | string | Type of text embedded (description, criteria, combined) |

#### Document Types

Three types of documents are embedded per trial:

1. **Description Embedding**
   - Source: `title + description`
   - Purpose: General trial overview matching
   - embedding_type: "description"

2. **Criteria Embedding**
   - Source: `inclusion_criteria + exclusion_criteria`
   - Purpose: Detailed eligibility matching
   - embedding_type: "criteria"

3. **Combined Embedding**
   - Source: All text fields combined
   - Purpose: Comprehensive semantic search
   - embedding_type: "combined"

### condition_embeddings

Secondary collection for medical condition semantic search.

#### Metadata Schema

| Field | Type | Description |
|-------|------|-------------|
| condition_code | string | Medical condition code |
| condition_name | string | Human-readable condition name |
| synonyms | string[] | Alternative names/terms |
| category | string | Condition category |

## Embedding Model

**Default Model**: `all-MiniLM-L6-v2`
- Dimensions: 384
- Max sequence length: 256 tokens
- Optimized for: Speed and efficiency

**Alternative Models** (configurable):
- `all-mpnet-base-v2`: Higher quality, 768 dimensions
- `multi-qa-MiniLM-L6-cos-v1`: Optimized for Q&A tasks

## Query Strategies

### 1. Patient-to-Trial Matching

**Input**: Patient demographics + conditions
**Process**:
1. Construct patient profile text
2. Generate embedding
3. Search trial_embeddings collection
4. Filter by demographic criteria (age, gender, location)
5. Rank by semantic similarity

**Query Example**:
```python
query_text = f"""
Patient: {age} year old {gender}
Conditions: {', '.join(conditions)}
Location: {state}
"""
results = collection.query(
    query_texts=[query_text],
    n_results=10,
    where={
        "status": "recruiting",
        "min_age": {"$lte": age},
        "max_age": {"$gte": age}
    }
)
```

### 2. Condition-Based Search

**Input**: Condition name or description
**Process**:
1. Normalize condition text
2. Search condition_embeddings for matches
3. Use matched condition codes for trial search

### 3. Hybrid Search

Combines vector similarity with traditional filters:
- Vector similarity: Top-k candidates
- Metadata filters: Age, gender, status, location
- Re-ranking: Combined score

## Distance Metrics

**Primary**: Cosine similarity
- Range: [0, 1] (0 = identical, 1 = opposite)
- Threshold: 0.7 for high-confidence matches

**Secondary**: L2 (Euclidean) distance
- Used for clustering and analysis

## Indexing Strategy

1. **Initial Load**: Bulk insert all trials
2. **Updates**: Incremental adds/updates
3. **Refresh**: Full re-index weekly (optional)

## Performance Considerations

- **Collection size**: ~10,000 trials → ~30,000 embeddings
- **Query latency**: <100ms for top-10 results
- **Memory usage**: ~200MB for embeddings + index
- **Batch size**: 100 documents per indexing batch

## Data Flow

```
Clinical Trial Data (Database)
        ↓
Text Preprocessing
        ↓
Embedding Generation (Sentence Transformers)
        ↓
Vector Store (ChromaDB)
        ↓
Semantic Search
        ↓
Filtered & Ranked Results
```

## Maintenance

- **Rebuild index**: When changing embedding models
- **Update embeddings**: When trial data changes significantly
- **Monitor quality**: Track relevance scores and user feedback
