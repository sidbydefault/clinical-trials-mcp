"""
Simple Database Models - Matches Synthea CSV Structure Exactly
"""

from typing import List, Optional
from datetime import date
from sqlmodel import SQLModel, Field, Relationship


class Patient(SQLModel, table=True):
    """Patient demographics table"""
    __tablename__ = "patients_demographics"
    
    patient_id: str = Field(primary_key=True, index=True)
    gender: str
    age: int = Field(index=True)
    name: str
    marital: str
    race: str
    ethnicity: str
    ssn: str
    address: str
    
    conditions: List["PatientCondition"] = Relationship(back_populates="patient")


class PatientCondition(SQLModel, table=True):
    """Patient conditions table"""
    __tablename__ = "patients_conditions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: str = Field(foreign_key="patients_demographics.patient_id", index=True)
    conditions: str = Field(index=True)
    
    patient: Optional[Patient] = Relationship(back_populates="conditions")


class AACTTrial(SQLModel, table=True):
    """AACT Clinical Trials table"""
    __tablename__ = "aact_clinical_trials"
    nct_id: str = Field(primary_key=True, index=True)
    text: str
    conditions: str