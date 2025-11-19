# Vector Store Schema

This document describes the Milvus vector store used for semantic search of clinical trials.

## Overview

The vector store uses **Milvus** (local persistent database) for hybrid semantic search combining:
- **Dense vector embeddings** for semantic similarity
- **Sparse BM25 embeddings** for keyword matching
- **RRF (Reciprocal Rank Fusion)** for hybrid ranking

## Vector Store Configuration

### Database Location
- **Type**: Milvus (local persistent file)
- **Default path**: Configured in `src/config.py` via `MILVUS_LOCALPATH`
- **Collection name**: `clincaldocs`

### Embedding Model

**Model**: `Qwen/Qwen3-Embedding-4B`
- **Dimensions**: 2560
- **Device**: CUDA (GPU-accelerated)
- **Batch size**: 1 (for stability during indexing)
- **Provider**: HuggingFace Transformers

This is a high-quality multilingual embedding model optimized for semantic understanding of clinical text.

### Hybrid Search Configuration

- **Dense embeddings**: Qwen3-Embedding-4B (2560-dim vectors)
- **Sparse embeddings**: BM25 built-in function (keyword matching)
- **Hybrid ranker**: RRFRanker (Reciprocal Rank Fusion)
- **Enable sparse**: True

## Data Structure

### Document Format

Each clinical trial document is chunked and embedded with the following structure:

**Text Nodes:**
```python
TextNode(
    text=chunk["text"],              # Chunked trial text
    metadata={                        # Trial metadata
        "nct_id": "NCT12345678",     # Trial identifier
        "chunk_index": 0,             # Chunk sequence number
        # ... additional metadata fields
    },
    id_="{nct_id}_chunk_{index}"     # Unique node ID
)
```

**Metadata Fields:**
- `nct_id`: NCT trial identifier
- `chunk_index`: Sequential chunk number within trial
- Condition metadata excluded from embeddings (configured via `excluded_embed_metadata`)
- Additional trial metadata from source JSON

### Chunking Strategy

**Parameters:**
- **Max chunk length**: 4096 characters
- **Chunker**: `ClinicalTrialChunker` (custom implementation)
- **Document sampling**: 10,000 trials from full dataset (~45,000 total)
- **Random seed**: 42 (for reproducible sampling)

**Process:**
1. Parse clinical trial document using custom chunker
2. Split into chunks of max 4096 characters
3. Preserve metadata across all chunks
4. Assign unique chunk IDs: `{nct_id}_chunk_{index}`

## Indexing Pipeline

The vector database is created using `database_creation/create_vectordb.py`:

### Step 1: Create Text Nodes
- Load clinical trials from JSON file
- Sample 10,000 documents
- Parse and chunk each document
- Extract and attach metadata
- Create TextNode objects

### Step 2: Parallel Embedding Generation
- **Multi-GPU processing** across available GPUs (e.g., GPUs 1-7)
- **Shard distribution**: Documents split across GPUs
- **Model per GPU**: Each GPU loads its own embedding model
- **Batch processing**: 1 embedding at a time for memory stability
- **Memory management**: Periodic CUDA cache clearing every 10 embeddings
- **Error handling**: Skip OOM chunks, continue processing

**Parallel Processing:**
```python
# Documents sharded across N GPUs
shards = [nodes[i::num_gpus] for i in range(num_gpus)]

# Each worker processes one shard on one GPU
for shard, gpu_id in zip(shards, device_ids):
    embed_on_gpu(shard, gpu_id)
```

### Step 3: Write to Milvus
- **Single-process writing** to avoid conflicts
- **Batch size**: 1000 vectors per write
- **Collection settings**:
  - Dimension: 2560
  - Enable sparse: True
  - Sparse function: BM25BuiltInFunction
  - Hybrid ranker: RRFRanker
  - Overwrite: False (append mode)

## Query Interface

### Runtime Configuration

At runtime (`src/vectorstore.py`), the vector store provides:

- **Connection**: Persistent Milvus database
- **Embedding model**: HuggingFaceEmbedding (Qwen3-Embedding-4B)
- **Index**: LlamaIndex VectorStoreIndex
- **Search mode**: Hybrid (dense + sparse)

### Query Process

1. **User query** → Embed using Qwen3-Embedding-4B
2. **Dense search** → Semantic similarity in 2560-dim space
3. **Sparse search** → BM25 keyword matching
4. **Hybrid ranking** → RRF combines both scores
5. **Return results** → Ranked trial chunks with metadata

### Similarity Metrics

**Dense vectors:**
- **Metric**: Cosine similarity
- **Range**: [-1, 1] (higher = more similar)

**Hybrid ranking:**
- **Method**: Reciprocal Rank Fusion (RRF)
- **Combines**: Dense vector similarity + BM25 keyword scores
- **Output**: Unified relevance ranking

## Performance Characteristics

### Indexing
- **Sample size**: 10,000 clinical trials
- **Total chunks**: ~10,000+ (varies by document length)
- **Embedding speed**: Dependent on GPU count and model
- **Memory per GPU**: ~2-4GB for model + embeddings

### Querying
- **Index type**: HNSW (approximate nearest neighbor)
- **Query latency**: <100ms typical for top-k results
- **Accuracy**: High (dense + sparse hybrid)

## Data Flow

```
Clinical Trial JSON
        ↓
Chunking (max 4096 chars)
        ↓
Text Nodes with Metadata
        ↓
Multi-GPU Parallel Embedding
        ↓
Milvus Vector Store
   (Dense + Sparse)
        ↓
Hybrid Search (RRF)
        ↓
Ranked Results
```

## Configuration Files

**Vector store config** (`src/config.py`):
```python
class VectorStoreConfig:
    MILVUS_LOCALPATH: str          # Path to Milvus database
    COLLECTION_NAME: str           # "clincaldocs"
    EMBEDDING_DIM: int            # 2560
    ENABLE_SPARSE: bool           # True
    HYBRID_RANKER: str            # "RRFRanker"
```

**Embedding config** (`src/config.py`):
```python
class EmbeddingConfig:
    MODEL_NAME: str               # "Qwen/Qwen3-Embedding-4B"
    DEVICE: str                   # "cuda:0"
    EMBED_BATCH_SIZE: int        # 1
```

## Maintenance

### Rebuilding the Index

To rebuild the vector store from scratch:

```bash
cd database_creation
python create_vectordb.py
```

**Note:** Update hardcoded paths in the script:
- `MILVUS_DB_PATH`: Output database location
- JSON input file path
- GPU device IDs

### Updating Embeddings

To add new trials without rebuilding:
- Set `overwrite=False` in MilvusVectorStore initialization
- Run embedding pipeline on new trials only
- Vectors will be appended to existing collection

## Integration

The vector store integrates with the MCP server through `src/vectorstore.py`:

- **Initialization**: Loads persistent Milvus database on startup
- **Query interface**: Exposes semantic search via LlamaIndex
- **Caching**: Singleton pattern for model/index reuse
- **Error handling**: Graceful fallback if vector store unavailable

See `src/vectorstore.py` for the complete runtime implementation.
