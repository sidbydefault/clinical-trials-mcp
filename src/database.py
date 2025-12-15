from database_creation.models import Patient, PatientCondition, AACTTrial
from sqlmodel import Session, select, create_engine
from collections import defaultdict
from contextlib import contextmanager
from .config import get_config
from typing import List, Dict, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


class Database:
    def __init__(self, embedding_model_name: str = "Qwen/Qwen3-Embedding-4B"):
        config = get_config()
        self.engine = create_engine(config.database.url)

        self.embedding_model = SentenceTransformer(
            embedding_model_name,
            trust_remote_code=True
        )

        self._embedding_cache = {}

    @contextmanager
    def get_session(self):
        with Session(self.engine) as session:
            yield session

    def _get_embedding(self, text: str):
        key = text.lower().strip()
        if key in self._embedding_cache:
            return self._embedding_cache[key]

        emb = self.embedding_model.encode(key, normalize_embeddings=True)
        self._embedding_cache[key] = emb
        return emb

    def _semantic_score(self, a: str, b: str):
        """Cosine similarity of normalized embeddings."""
        emb_a = self._get_embedding(a)
        emb_b = self._get_embedding(b)
        return float(np.dot(emb_a, emb_b)) 

    def _match_conditions(
        self,
        patient_conditions: List[str],
        required_conditions: List[str],
        threshold: float = 0.75
    ):

        if not required_conditions:
            return True

        patient_conditions = [pc.strip() for pc in patient_conditions if pc.strip()]
        required_conditions = [rc.strip() for rc in required_conditions if rc.strip()]

        for req in required_conditions:
            matched = any(
                self._semantic_score(req, pc) >= threshold
                for pc in patient_conditions
            )
            if not matched:
                return False

        return True

    def find_eligible_patients(
        self,
        age_min: int,
        age_max: int,
        required_conditions: Optional[List[str]] = None,
        limit: int = 100,
    ):

        with self.get_session() as session:
            # Primary filter: age + gender
            query = select(Patient).where(
                (Patient.age >= age_min) & (Patient.age <= age_max)
            )


            patients = session.exec(query).all()

            if not patients:
                return []

            # Fetch all their conditions in one query
            patient_ids = [p.patient_id for p in patients]

            condition_rows = session.exec(
                select(PatientCondition).where(
                    PatientCondition.patient_id.in_(patient_ids)
                )
            ).all()

        # Group conditions
        cond_map = defaultdict(list)
        for row in condition_rows:
            cond_map[row.patient_id].append(row.conditions)

        # Match using embeddings
        eligible = []
        for p in patients:
            p_conditions = cond_map.get(p.patient_id, [])

            if self._match_conditions(p_conditions, required_conditions or []):
                eligible.append(
                    {
                        "patient_id": p.patient_id,
                        "age": p.age,
                        "gender": p.gender,
                        "race": p.race,
                        "ethnicity": p.ethnicity,
                        "name": p.name,
                        "conditions": p_conditions,
                    }
                )

            if len(eligible) >= limit:
                break

        return eligible


    def get_trials_by_nct_ids(self, nct_ids: List[str]):
        with self.get_session() as session:
            trials = session.exec(
                select(AACTTrial).where(AACTTrial.nct_id.in_(nct_ids))
            ).all()

        trial_map = {
            t.nct_id: {"text": t.text, "conditions": t.conditions}
            for t in trials
        }

        return trial_map

_db_instance: Optional[Database] = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
