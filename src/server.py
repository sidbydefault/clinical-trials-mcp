"""
MCP server implementation for clinical trial matching.
"""

import logging
from typing import Any, Dict, List

from config import ensure_directories, get_settings
from database import DatabaseManager
from matching import TrialMatcher
from vectorstore import VectorStoreManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ClinicalTrialsMCPServer:
    """MCP server for clinical trial matching."""

    def __init__(self):
        """Initialize the MCP server."""
        logger.info("Initializing Clinical Trials MCP Server...")

        # Load settings
        self.settings = get_settings()
        ensure_directories()

        # Initialize components
        self.db_manager = DatabaseManager(self.settings.database_url)
        self.vector_manager = VectorStoreManager(
            persist_directory=self.settings.vector_store_path,
            embedding_model=self.settings.embedding_model,
        )
        self.matcher = TrialMatcher(self.db_manager, self.vector_manager)

        logger.info("Server initialized successfully")

    def get_patient_matches(
        self,
        patient_id: str,
        top_k: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Get matching trials for a patient.

        Args:
            patient_id: Patient identifier
            top_k: Number of matches to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of trial matches
        """
        logger.info(f"Finding matches for patient {patient_id}")

        matches = self.matcher.find_matching_trials(
            patient_id=patient_id,
            top_k=top_k,
            min_similarity=min_similarity,
        )

        return [match.model_dump() for match in matches]

    def search_trials(
        self,
        condition: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search trials by condition.

        Args:
            condition: Condition name or description
            top_k: Number of results

        Returns:
            List of matching trials
        """
        logger.info(f"Searching trials for condition: {condition}")

        trials = self.matcher.search_trials_by_condition(
            condition=condition,
            top_k=top_k,
        )

        return trials

    def get_patient_info(self, patient_id: str) -> Dict[str, Any]:
        """
        Get patient information.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient data with conditions
        """
        patient = self.db_manager.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        conditions = self.db_manager.get_patient_conditions(patient_id)

        return {
            "patient": patient,
            "conditions": conditions,
        }

    def get_trial_details(self, trial_id: str) -> Dict[str, Any]:
        """
        Get trial details.

        Args:
            trial_id: Trial identifier

        Returns:
            Trial data
        """
        trial = self.db_manager.get_trial(trial_id)
        if not trial:
            raise ValueError(f"Trial {trial_id} not found")

        return trial


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Clinical Trials MCP Server...")

    server = ClinicalTrialsMCPServer()

    logger.info(
        f"Server running on {server.settings.host}:{server.settings.port}"
    )
    logger.info("Press Ctrl+C to stop")

    # TODO: Implement MCP protocol handler
    # For now, this is a basic setup
    # In production, integrate with actual MCP framework

    try:
        # Keep server running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
