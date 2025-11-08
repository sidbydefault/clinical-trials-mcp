"""
Database management for clinical trials, patients, and conditions.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

Base = declarative_base()


class PatientDB(Base):
    """Patient table."""

    __tablename__ = "patients"

    patient_id = Column(String(50), primary_key=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    race = Column(String(50))
    state = Column(String(2))
    zip_code = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conditions = relationship("ConditionDB", back_populates="patient")


class ConditionDB(Base):
    """Condition table."""

    __tablename__ = "conditions"

    condition_id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=False)
    condition_code = Column(String(20), nullable=False)
    condition_name = Column(String(255), nullable=False)
    onset_date = Column(Date)
    status = Column(String(20), default="active")
    severity = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("PatientDB", back_populates="conditions")


class ClinicalTrialDB(Base):
    """Clinical trial table."""

    __tablename__ = "clinical_trials"

    trial_id = Column(String(50), primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    phase = Column(String(20))
    status = Column(String(50), nullable=False)
    sponsor = Column(String(255))
    conditions_studied = Column(Text)  # JSON string
    min_age = Column(Integer)
    max_age = Column(Integer)
    eligible_genders = Column(String(50), default="all")
    inclusion_criteria = Column(Text)
    exclusion_criteria = Column(Text)
    locations = Column(Text)  # JSON string
    start_date = Column(Date)
    completion_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseManager:
    """Manages database operations."""

    def __init__(self, database_url: str):
        """
        Initialize database manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def load_patients(self, df: pd.DataFrame) -> None:
        """
        Load patients from DataFrame.

        Args:
            df: DataFrame with patient data
        """
        with self.get_session() as session:
            for _, row in df.iterrows():
                patient = PatientDB(
                    patient_id=row["patient_id"],
                    age=row["age"],
                    gender=row["gender"],
                    race=row.get("race"),
                    state=row.get("state"),
                    zip_code=row.get("zip_code"),
                )
                session.merge(patient)
            session.commit()

    def load_conditions(self, df: pd.DataFrame) -> None:
        """
        Load conditions from DataFrame.

        Args:
            df: DataFrame with condition data
        """
        with self.get_session() as session:
            for _, row in df.iterrows():
                condition = ConditionDB(
                    condition_id=row["condition_id"],
                    patient_id=row["patient_id"],
                    condition_code=row["condition_code"],
                    condition_name=row["condition_name"],
                    onset_date=row.get("onset_date"),
                    status=row.get("status", "active"),
                    severity=row.get("severity"),
                )
                session.merge(condition)
            session.commit()

    def load_trials(self, df: pd.DataFrame) -> None:
        """
        Load clinical trials from DataFrame.

        Args:
            df: DataFrame with trial data
        """
        with self.get_session() as session:
            for _, row in df.iterrows():
                # Convert list fields to JSON strings
                conditions_studied = row.get("conditions_studied", [])
                if isinstance(conditions_studied, list):
                    conditions_studied = json.dumps(conditions_studied)

                locations = row.get("locations", [])
                if isinstance(locations, list):
                    locations = json.dumps(locations)

                trial = ClinicalTrialDB(
                    trial_id=row["trial_id"],
                    title=row["title"],
                    description=row["description"],
                    phase=row.get("phase"),
                    status=row["status"],
                    sponsor=row.get("sponsor"),
                    conditions_studied=conditions_studied,
                    min_age=row.get("min_age"),
                    max_age=row.get("max_age"),
                    eligible_genders=row.get("eligible_genders", "all"),
                    inclusion_criteria=row.get("inclusion_criteria"),
                    exclusion_criteria=row.get("exclusion_criteria"),
                    locations=locations,
                    start_date=row.get("start_date"),
                    completion_date=row.get("completion_date"),
                )
                session.merge(trial)
            session.commit()

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by ID.

        Args:
            patient_id: Patient identifier

        Returns:
            Patient data dictionary or None
        """
        with self.get_session() as session:
            patient = session.query(PatientDB).filter_by(patient_id=patient_id).first()
            if not patient:
                return None

            return {
                "patient_id": patient.patient_id,
                "age": patient.age,
                "gender": patient.gender,
                "race": patient.race,
                "state": patient.state,
                "zip_code": patient.zip_code,
            }

    def get_patient_conditions(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get all conditions for a patient.

        Args:
            patient_id: Patient identifier

        Returns:
            List of condition dictionaries
        """
        with self.get_session() as session:
            conditions = (
                session.query(ConditionDB).filter_by(patient_id=patient_id).all()
            )

            return [
                {
                    "condition_id": c.condition_id,
                    "condition_code": c.condition_code,
                    "condition_name": c.condition_name,
                    "status": c.status,
                    "severity": c.severity,
                }
                for c in conditions
            ]

    def get_trial(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trial by ID.

        Args:
            trial_id: Trial identifier

        Returns:
            Trial data dictionary or None
        """
        with self.get_session() as session:
            trial = (
                session.query(ClinicalTrialDB).filter_by(trial_id=trial_id).first()
            )
            if not trial:
                return None

            return {
                "trial_id": trial.trial_id,
                "title": trial.title,
                "description": trial.description,
                "phase": trial.phase,
                "status": trial.status,
                "sponsor": trial.sponsor,
                "conditions_studied": json.loads(trial.conditions_studied or "[]"),
                "min_age": trial.min_age,
                "max_age": trial.max_age,
                "eligible_genders": trial.eligible_genders,
                "inclusion_criteria": trial.inclusion_criteria,
                "exclusion_criteria": trial.exclusion_criteria,
                "locations": json.loads(trial.locations or "[]"),
            }

    def get_all_patients(self) -> pd.DataFrame:
        """Get all patients as DataFrame."""
        with self.get_session() as session:
            patients = session.query(PatientDB).all()
            return pd.DataFrame([vars(p) for p in patients])

    def get_all_conditions(self) -> pd.DataFrame:
        """Get all conditions as DataFrame."""
        with self.get_session() as session:
            conditions = session.query(ConditionDB).all()
            return pd.DataFrame([vars(c) for c in conditions])

    def get_all_trials(self) -> pd.DataFrame:
        """Get all trials as DataFrame."""
        with self.get_session() as session:
            trials = session.query(ClinicalTrialDB).all()
            data = []
            for t in trials:
                trial_dict = vars(t).copy()
                trial_dict["conditions_studied"] = json.loads(
                    t.conditions_studied or "[]"
                )
                trial_dict["locations"] = json.loads(t.locations or "[]")
                data.append(trial_dict)
            return pd.DataFrame(data)
