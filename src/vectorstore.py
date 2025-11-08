"""
Vector store management for semantic search of clinical trials.
"""

import json
from typing import Any, Dict, List, Optional

import chromadb
import pandas as pd
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class VectorStoreManager:
    """Manages vector embeddings and semantic search."""

    def __init__(
        self,
        persist_directory: str = "data/vector_store",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize vector store manager.

        Args:
            persist_directory: Directory to persist vector store
            embedding_model: Sentence transformer model name
        """
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model

        # Initialize ChromaDB client
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
            )
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)

        # Get or create collections
        self.trial_collection = self.client.get_or_create_collection(
            name="trial_embeddings",
            metadata={"hnsw:space": "cosine"},
        )

    def _prepare_trial_text(
        self, trial: Dict[str, Any], embedding_type: str = "combined"
    ) -> str:
        """
        Prepare trial text for embedding.

        Args:
            trial: Trial data dictionary
            embedding_type: Type of embedding (description, criteria, combined)

        Returns:
            Prepared text string
        """
        if embedding_type == "description":
            return f"{trial['title']}\n\n{trial['description']}"

        elif embedding_type == "criteria":
            inclusion = trial.get("inclusion_criteria", "")
            exclusion = trial.get("exclusion_criteria", "")
            return f"Inclusion: {inclusion}\n\nExclusion: {exclusion}"

        else:  # combined
            parts = [
                trial["title"],
                trial["description"],
                f"Phase: {trial.get('phase', 'N/A')}",
            ]

            if trial.get("conditions_studied"):
                conditions = trial["conditions_studied"]
                if isinstance(conditions, list):
                    parts.append(f"Conditions: {', '.join(conditions)}")
                else:
                    parts.append(f"Conditions: {conditions}")

            if trial.get("inclusion_criteria"):
                parts.append(f"Inclusion: {trial['inclusion_criteria']}")

            if trial.get("exclusion_criteria"):
                parts.append(f"Exclusion: {trial['exclusion_criteria']}")

            return "\n\n".join(parts)

    def index_trials(self, trials_df: pd.DataFrame) -> None:
        """
        Index clinical trials in vector store.

        Args:
            trials_df: DataFrame with trial data
        """
        documents = []
        metadatas = []
        ids = []

        for _, trial in trials_df.iterrows():
            trial_dict = trial.to_dict()

            # Ensure list fields are properly formatted
            if isinstance(trial_dict.get("conditions_studied"), str):
                try:
                    trial_dict["conditions_studied"] = json.loads(
                        trial_dict["conditions_studied"]
                    )
                except (json.JSONDecodeError, TypeError):
                    trial_dict["conditions_studied"] = []

            if isinstance(trial_dict.get("locations"), str):
                try:
                    trial_dict["locations"] = json.loads(trial_dict["locations"])
                except (json.JSONDecodeError, TypeError):
                    trial_dict["locations"] = []

            # Create embeddings for different text types
            for embedding_type in ["description", "criteria", "combined"]:
                text = self._prepare_trial_text(trial_dict, embedding_type)
                doc_id = f"{trial_dict['trial_id']}_{embedding_type}"

                documents.append(text)
                ids.append(doc_id)

                # Prepare metadata
                metadata = {
                    "trial_id": trial_dict["trial_id"],
                    "title": trial_dict["title"],
                    "phase": trial_dict.get("phase", ""),
                    "status": trial_dict["status"],
                    "min_age": trial_dict.get("min_age", 0) or 0,
                    "max_age": trial_dict.get("max_age", 150) or 150,
                    "eligible_genders": trial_dict.get("eligible_genders", "all"),
                    "embedding_type": embedding_type,
                }

                # Add conditions as comma-separated string
                if trial_dict.get("conditions_studied"):
                    conditions = trial_dict["conditions_studied"]
                    if isinstance(conditions, list):
                        metadata["conditions"] = ",".join(conditions)
                    else:
                        metadata["conditions"] = str(conditions)

                # Add locations as comma-separated string
                if trial_dict.get("locations"):
                    locations = trial_dict["locations"]
                    if isinstance(locations, list):
                        metadata["locations"] = ",".join(locations)
                    else:
                        metadata["locations"] = str(locations)

                metadatas.append(metadata)

        # Batch add to collection
        if documents:
            self.trial_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

    def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search for trials using semantic similarity.

        Args:
            query: Search query text
            n_results: Number of results to return
            filters: Optional metadata filters

        Returns:
            Search results dictionary
        """
        where_filter = filters if filters else None

        results = self.trial_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        return results

    def search_for_patient(
        self,
        patient_data: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        n_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for trials matching a patient profile.

        Args:
            patient_data: Patient data dictionary
            conditions: List of patient conditions
            n_results: Number of results to return

        Returns:
            List of matching trials with scores
        """
        # Construct query from patient profile
        condition_names = [c["condition_name"] for c in conditions]
        query_parts = [
            f"Patient: {patient_data['age']} year old {patient_data['gender']}",
            f"Conditions: {', '.join(condition_names)}",
        ]

        if patient_data.get("state"):
            query_parts.append(f"Location: {patient_data['state']}")

        query = "\n".join(query_parts)

        # Build filters based on patient demographics
        filters = {
            "status": "recruiting",
            "min_age": {"$lte": patient_data["age"]},
            "max_age": {"$gte": patient_data["age"]},
        }

        # Add gender filter if not "all"
        gender = patient_data["gender"].lower()
        if gender in ["male", "female"]:
            # Trial must accept either "all" or the specific gender
            filters["$or"] = [
                {"eligible_genders": "all"},
                {"eligible_genders": gender},
            ]

        # Perform search
        results = self.search(query, n_results=n_results * 3, filters=None)

        # Process and deduplicate results
        trial_scores: Dict[str, float] = {}
        trial_metadata: Dict[str, Dict[str, Any]] = {}

        if results["ids"] and results["ids"][0]:
            for i, trial_id_full in enumerate(results["ids"][0]):
                # Extract base trial_id (remove embedding_type suffix)
                trial_id = trial_id_full.rsplit("_", 1)[0]
                distance = results["distances"][0][i]
                similarity = 1 - distance  # Convert distance to similarity

                # Keep best score for each trial
                if (
                    trial_id not in trial_scores
                    or similarity > trial_scores[trial_id]
                ):
                    trial_scores[trial_id] = similarity
                    trial_metadata[trial_id] = results["metadatas"][0][i]

        # Sort by score and return top n_results
        sorted_trials = sorted(
            trial_scores.items(), key=lambda x: x[1], reverse=True
        )[:n_results]

        return [
            {
                "trial_id": trial_id,
                "similarity_score": score,
                **trial_metadata[trial_id],
            }
            for trial_id, score in sorted_trials
        ]

    def clear_collection(self) -> None:
        """Clear all embeddings from the collection."""
        self.client.delete_collection("trial_embeddings")
        self.trial_collection = self.client.get_or_create_collection(
            name="trial_embeddings",
            metadata={"hnsw:space": "cosine"},
        )
