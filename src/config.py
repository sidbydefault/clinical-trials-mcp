from dotenv import load_dotenv
import os 
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


load_dotenv()
@dataclass
class DatabaseConfig:
    """ PostreSQL database configuration parameters. """
    url : str
    @classmethod
    def from_env(cls):
        url = os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable not set")
        return cls(url=url)
    
@dataclass
class VectorStoreConfig:
    """ Configuration parameters for the vector store. """
    uri : str 
    collection_name : str = "clincaldocs"
    embedding_dim : int = 2560
    enable_sparse : bool = True
    hybrid_ranker : str = "RRFRanker"
    @classmethod
    def from_env(cls):
        uri = os.getenv("MILVUS_LOCALPATH")
        if not uri:
            raise ValueError("MILVUS_URI environment variable not set")
        return cls(
            uri=uri,
            collection_name=os.getenv("MILVUS_COLLECTION_NAME", "clincaldocs"),
            embedding_dim=int(os.getenv("EMBEDDING_DIM", "2560")),
            enable_sparse=bool(os.getenv("ENABLE_SPARSE", "True")),
            hybrid_ranker=os.getenv("HYBRID_RANKER", "RRFRanker"),
        )
@dataclass
class EmbeddingConfig:
    model_name : str ="Qwen/Qwen3-Embedding-4B"
    batch_size : int = 1
    device: str = "cuda:0"
    dimension: int = 2560
    @classmethod
    def from_env(cls):
        return cls(
            model_name=os.getenv("EMBEDDING_MODEL_NAME", "Qwen/Qwen3-Embedding-4B"),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "1")),
            device=os.getenv("EMBEDDING_DEVICE", "cuda:0"),
            dimension=int(os.getenv("EMBEDDING_DIMENSION", "2560")),
        )

@dataclass
class ServerConfig:
    """Complete server configuration"""
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    embedding: EmbeddingConfig
    
    @classmethod
    def from_env(cls):
        return cls(
            database=DatabaseConfig.from_env(),
            vector_store=VectorStoreConfig.from_env(),
            embedding=EmbeddingConfig.from_env(),
        )


# Global config instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get or initialize server configuration"""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
    return _config


    