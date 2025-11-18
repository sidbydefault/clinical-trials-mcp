from typing import List, Dict, Optional 
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.core import StorageContext, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus.utils import BM25BuiltInFunction
from .config import get_config
import torch
from .database import get_db


class VectorStore:

    def __init__(self):
        config = get_config()
        self.embed_model = HuggingFaceEmbedding(
            model_name = config.embedding.model_name,
            device = config.embedding.device,
            embed_batch_size = config.embedding.batch_size
        )

        Settings.embed_model = self.embed_model
        Settings.llm = None

        self.vector_store = MilvusVectorStore(
            uri=config.vector_store.uri,
            collection_name=config.vector_store.collection_name,
            dim=config.vector_store.embedding_dim,
            enable_sparse=config.vector_store.enable_sparse,
            sparse_embedding_function=BM25BuiltInFunction(),
            hybrid_ranker=config.vector_store.hybrid_ranker,
            overwrite=False,
        )
        storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        # Create index
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=storage_context,
            embed_model=self.embed_model,
            llm=None,
        )

    def search(
            self, query: str, 
            top_k: int = 5, 
            filters: Optional[Dict] = None,
            enrich_from_db: bool = True
            ):
        query_engine = self.index.as_query_engine(
            vector_store_query_mode="hybrid",
            similarity_top_k=top_k,
            llm=None,
        )
        response = query_engine.query(query)
        results =[]
        nct_ids_to_fetch =set()

        for node in response.source_nodes:
            metadata = node.metadata
            if filters:
                if filters.get("phase") and metadata.get("phase") != filters["phase"]:
                    continue
                if filters.get("status") and metadata.get("status") != filters["status"]:
                    continue
                if filters.get("min_enrollment"):
                    if metadata.get("enrollment", 0) < filters["min_enrollment"]:
                        continue
            
            nct_id = metadata.get("nct_id")
            if nct_id not in nct_ids_to_fetch:
                nct_ids_to_fetch.add(nct_id)

                record = {
                    "text": node.text,
                    "similarity_score": round(getattr(node, "score", 0.0), 3),
                    "metadata": metadata
                }
                results.append(record)

            if len(results)>= top_k:
                break
        
        
        if enrich_from_db and nct_ids_to_fetch:
            db = get_db()
            trial_data = db.get_trials_by_nct_ids(list(nct_ids_to_fetch))

        enhanced_results =[] 

        for r in results:
            metadata =r.get("metadata")
            nct_id = metadata.get("nct_id")
            full_text = trial_data[nct_id].get("text")
            conditions = trial_data[nct_id].get("conditions")
            enhanced_metadata = {**metadata, "conditions": conditions}
            enhanced_record = {
                "text": full_text,
                "chunk_similarity_score": r.get("similarity_score"),
                **enhanced_metadata
            }
            enhanced_results.append(enhanced_record)
        return enhanced_results
    
    def clean_up(self):
        if hasattr(self, "embed_model") and torch.cuda.is_available():
            torch.cuda.empty_cache()

_vector_store_instance: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    """Get or initialize vector store"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance

        
            

