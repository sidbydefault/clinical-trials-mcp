import json
import torch
import gc
import os
import numpy as np
import random
from multiprocessing import Pool, set_start_method
from llama_index.vector_stores.milvus.utils import BM25BuiltInFunction
from llama_index.core.schema import TextNode, MetadataMode
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from chunker import ClinicalTrialChunker

def create_nodes(file_path: str, max_length: int = 4096, RANDOM_SEED: int = 42,SAMPLE_SIZE: int = 10000):
    """Create text nodes from clinical trial document."""
    with open(file_path, 'r') as f:
        data = json.load(f)

    #sampling 10,000 documents for processing
    doc_ids = list(data.keys())
    random.seed(RANDOM_SEED)
    sampled_doc_ids = random.sample(doc_ids, k=SAMPLE_SIZE)
    sampled_data = {doc_id: data[doc_id] for doc_id in sampled_doc_ids}

    print(f"Total number of documents: {len(data)}")
    all_nodes = []
    chunk_count = 0
    # Process metadata
    for doc_id, content in sampled_data.items():
        nct_id = doc_id
        count = content['metadata'].get("conditions_count", 0)
        excluded_keys = [f"condition_{i+1}" for i in range(count)]
        excluded_keys.extend(['interventions_count', 'outcomes_count'])

        base_metadata = { k: v for k, v in content['metadata'].items() if k not in excluded_keys }

        parser = ClinicalTrialChunker(content["document"],max_length=4096)
        parser.parse()
        chunks = parser.create_chunks()

        for chunk_idx, chunk in enumerate(chunks):
            chunk_count += 1
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update({
                "chunk_index": chunk_idx
            })
            chunk["metadata"] = chunk_metadata

            node = TextNode(
                text=chunk["text"],
                metadata=chunk["metadata"],
                excluded_embed_metadata=excluded_keys,
                metadata_mode=MetadataMode.EMBED,
                id_=f"{nct_id}_chunk_{chunk_idx}"
            )
            all_nodes.append(node)


    print(f"\n{'='*60}")
    print(f"Chunking Summary")
    print('='*60)
    print(f"Original documents: {len(sampled_data)}")
    print(f"Total chunks created: {chunk_count}")
    print(f"Average chunks per document: {chunk_count/len(sampled_data):.1f}")

    return all_nodes


def embed_worker(args):
    """
    Embed chunks on GPU, then write to Milvus with lock synchronization.
    Each worker handles its own database writes.
    """
    shard, device_id, model_name, shard_id = args
    try:
        print(f"[GPU {device_id}] Worker started with {len(shard)} chunks")
        
        torch.cuda.set_device(device_id)
        torch.cuda.empty_cache()
        
        embed_model = HuggingFaceEmbedding(
            model_name=model_name,
            device=f"cuda:{device_id}",
            embed_batch_size=1,
        )
        
        embedded_nodes = []
        failed_count = 0
        
        for idx, node in enumerate(shard):
            if idx % 500 == 0 and idx > 0:
                print(f"[GPU {device_id}] Embedding progress: {idx}/{len(shard)} ({idx/len(shard)*100:.1f}%)")
            
            try:
                if idx % 10 == 0:
                    torch.cuda.empty_cache()
                
                with torch.no_grad():
                    embedding = embed_model.get_text_embedding(
                        node.get_content(metadata_mode=MetadataMode.EMBED)
                    )
                if isinstance(embedding, torch.Tensor):
                    embedding = embedding.cpu().numpy()
                elif hasattr(embedding, '__array__'):
                    embedding = np.array(embedding)

                node.embedding = embedding
                embedded_nodes.append(node)
                
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    print(f"[GPU {device_id}] OOM at index {idx}, length: {len(node.text)}")
                    failed_count += 1
                    torch.cuda.empty_cache()
                    gc.collect()
                else:
                    raise e
        
        # Cleanup model
        del embed_model
        torch.cuda.empty_cache()
        gc.collect()
        
        print(f"[GPU {device_id}] Embedding done: {len(embedded_nodes)}/{len(shard)} successful")

        return embedded_nodes
        
        
    except Exception as e:
        print(f"[GPU {device_id}] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return embedded_nodes


def main():
    MILVUS_DB_PATH = "/home/sid/vector_database/clincaldocs_milvus.db"
    MODEL_NAME = "Qwen/Qwen3-Embedding-4B"
    EMBEDDING_DIM = 2560
    DEVICE_IDS = [1, 2, 3, 4, 5, 6, 7]
    MAX_CHUNK_LENGTH = 4096
    SAMPLE_SIZE = 10000

    
    nodes = create_nodes(
        file_path="/home/sid/research_note_generation/sid/data_processing/notebooks/clinical_documents_with_metadata_final.json",
        max_length=MAX_CHUNK_LENGTH,
        RANDOM_SEED=42,
        SAMPLE_SIZE=SAMPLE_SIZE
    )
    print(f"Total nodes to process: {len(nodes)}")

    num_gpus = len(DEVICE_IDS)
    shards = [nodes[i::num_gpus] for i in range(num_gpus)]

    print("\n" + "="*60)
    print("Step 2: Embedding in parallel across GPUs")
    print("="*60)
    
    # Prepare arguments for workers
    worker_args = [
        (shard, device_id, MODEL_NAME, shard_id)
        for shard_id, (shard, device_id) in enumerate(zip(shards, DEVICE_IDS))
    ]
    
    # Run embedding in parallel
    with Pool(processes=num_gpus) as pool:
        results = pool.map(embed_worker, worker_args)
    
    # Collect all embedded nodes
    all_embedded_nodes = []
    failed_workers = []
    
    for idx, result in enumerate(results):
        if result is not None and len(result) > 0:
            all_embedded_nodes.extend(result)
            print(f"GPU {DEVICE_IDS[idx]}: {len(result)} nodes collected")
        else:
            failed_workers.append(DEVICE_IDS[idx])
            print(f"GPU {DEVICE_IDS[idx]}: Worker failed or returned empty!")
    
    print(f"\nCollected {len(all_embedded_nodes)} nodes from {len(results) - len(failed_workers)}/{len(results)} workers")
    
    print("\n" + "="*60)
    print("Step 3: Writing to Milvus (single process)")
    print("="*60)
    print(f"Total embedded nodes: {len(all_embedded_nodes)}")
    
    # Create vector store ONCE in main process
    vector_store = MilvusVectorStore(
        uri=MILVUS_DB_PATH,
        dim=EMBEDDING_DIM,
        collection_name='clincaldocs',
        overwrite=False,  
        enable_sparse=True,
        sparse_embedding_function=BM25BuiltInFunction(),
        hybrid_ranker='RRFRanker',
    )
    
    # Write in batches
    BATCH_SIZE = 1000
    for i in range(0, len(all_embedded_nodes), BATCH_SIZE):
        batch = all_embedded_nodes[i:i+BATCH_SIZE]
        vector_store.add(batch)
        print(f"Written: {min(i+BATCH_SIZE, len(all_embedded_nodes))}/{len(all_embedded_nodes)} chunks")
    
    print("\n" + "="*60)
    print("Pipeline Complete!")
    print("="*60)
    print(f"Total chunks indexed: {len(all_embedded_nodes)}")



if __name__ == "__main__":
    set_start_method('spawn', force=True)
    main()