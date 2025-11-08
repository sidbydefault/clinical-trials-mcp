"""
Clinical trial matching logic.
"""

from typing import Any, Dict, List, Optional

from database import DatabaseManager
from database_creation.models import TrialMatch
from vectorstore import VectorStoreManager


class TrialMatcher:
    """Matches patients to clinical trials."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_manager: VectorStoreManager,
    ):
        """
        Initialize trial matcher.

        Args:
            db_manager: Database manager instance
            vector_manager: Vector store manager instance
        """
        self.db_manager = db_manager
        self.vector_manager = vector_manager

    def find_matching_trials(
        self,
        patient_id: str,
        top_k: int = 10,
        min_similarity: float = 0.5,
    ) -> List[TrialMatch]:
        """
        Find matching clinical trials for a patient.

        Args:
            patient_id: Patient identifier
            top_k: Number of top matches to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of trial matches
        """
        # Get patient data
        patient = self.db_manager.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        conditions = self.db_manager.get_patient_conditions(patient_id)

        # Search for matching trials
        search_results = self.vector_manager.search_for_patient(
            patient_data=patient,
            conditions=conditions,
            n_results=top_k * 2,  # Get more to filter
        )

        # Filter and enrich results
        matches = []
        for result in search_results:
            similarity = result["similarity_score"]

            # Skip low similarity matches
            if similarity < min_similarity:
                continue

            # Get full trial details
            trial = self.db_manager.get_trial(result["trial_id"])
            if not trial:
                continue

            # Determine eligibility and match reasons
            eligible, reasons = self._check_eligibility(patient, conditions, trial)

            match = TrialMatch(
                trial_id=trial["trial_id"],
                title=trial["title"],
                similarity_score=similarity,
                phase=trial.get("phase"),
                status=trial["status"],
                match_reasons=reasons,
                eligible=eligible,
            )
            matches.append(match)

            # Stop if we have enough matches
            if len(matches) >= top_k:
                break

        return matches

    def _check_eligibility(
        self,
        patient: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        trial: Dict[str, Any],
    ) -> tuple[bool, List[str]]:
        """
        Check patient eligibility for a trial.

        Args:
            patient: Patient data
            conditions: Patient conditions
            trial: Trial data

        Returns:
            Tuple of (eligible, reasons)
        """
        reasons = []
        eligible = True

        # Check age
        age = patient["age"]
        min_age = trial.get("min_age", 0)
        max_age = trial.get("max_age", 150)

        if min_age and age < min_age:
            eligible = False
            reasons.append(f"Age {age} below minimum {min_age}")
        elif max_age and age > max_age:
            eligible = False
            reasons.append(f"Age {age} above maximum {max_age}")
        else:
            reasons.append(f"Age {age} meets requirements")

        # Check gender
        gender = patient["gender"].lower()
        eligible_genders = trial.get("eligible_genders", "all").lower()

        if eligible_genders != "all" and gender != eligible_genders:
            eligible = False
            reasons.append(f"Gender {gender} not eligible (requires {eligible_genders})")
        else:
            reasons.append("Gender eligible")

        # Check conditions
        trial_conditions = trial.get("conditions_studied", [])
        patient_condition_names = {c["condition_name"].lower() for c in conditions}

        if trial_conditions:
            matching_conditions = []
            for tc in trial_conditions:
                tc_lower = tc.lower()
                for pc in patient_condition_names:
                    if tc_lower in pc or pc in tc_lower:
                        matching_conditions.append(tc)
                        break

            if matching_conditions:
                reasons.append(f"Matching conditions: {', '.join(matching_conditions)}")
            else:
                reasons.append("Related conditions based on semantic similarity")

        # Check location (if patient has state)
        if patient.get("state") and trial.get("locations"):
            locations = trial["locations"]
            patient_state = patient["state"].upper()

            # Check if any location matches patient state
            location_match = any(
                patient_state in loc.upper() for loc in locations
            )

            if location_match:
                reasons.append(f"Trial available in {patient_state}")
            else:
                reasons.append("Trial may require travel")

        return eligible, reasons

    def search_trials_by_condition(
        self,
        condition: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search trials by condition name or description.

        Args:
            condition: Condition name or description
            top_k: Number of results to return

        Returns:
            List of matching trials
        """
        query = f"Clinical trial for: {condition}"
        results = self.vector_manager.search(
            query=query,
            n_results=top_k,
            filters={"status": "recruiting"},
        )

        # Deduplicate and enrich results
        trials = []
        seen_trial_ids = set()

        if results["ids"] and results["ids"][0]:
            for i, trial_id_full in enumerate(results["ids"][0]):
                trial_id = trial_id_full.rsplit("_", 1)[0]

                if trial_id in seen_trial_ids:
                    continue
                seen_trial_ids.add(trial_id)

                trial = self.db_manager.get_trial(trial_id)
                if trial:
                    trial["similarity_score"] = 1 - results["distances"][0][i]
                    trials.append(trial)

        return trials[:top_k]
