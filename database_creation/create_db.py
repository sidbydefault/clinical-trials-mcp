from sqlmodel import Session,create_engine, SQLModel
import pandas as pd 
import os
from dotenv import load_dotenv
import sys
import json
from pathlib import Path
from models import Patient, PatientCondition, AACTTrial

load_dotenv()
DATA_DIR=Path(r'D:\clinical-trials-mcp\data\raw')

def get_engine():
    """Get database engine"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(database_url)


def create_tables():
    """Create database tables"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    print("Tables created")

def drop_tables():
    """Drop all existing tables"""
    engine = get_engine()
    database_url = os.getenv("DATABASE_URL")
    
    print(f"Database location: {database_url}")
    
    try:
        SQLModel.metadata.drop_all(engine)
        print("Dropped existing tables")
    except Exception as e:
        print(f" No existing tables to drop (or error: {e})")


def load_demographics(filepath: str, batch_size: int = 1000):
    df= pd.read_parquet(filepath)
    required_columns = ['patient_id', 'name', 'age', 'gender', 'marital', 
                    'race', 'ethnicity', 'ssn', 'address']
    missing_columns = [col for col in required_columns if col not in df.columns]
    df.drop_duplicates(inplace=True)
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    engine = get_engine()
    with Session(engine) as session:
        added =0
        skipped =0
        # use enumerate to get an integer counter instead of relying on the dataframe index
        for i,row in df.iterrows():
            patient = Patient(
                patient_id=row['patient_id'],
                name=row['name'],
                age=row['age'],
                gender = row['gender'],
                marital = row['marital'],
                race = row['race'],
                ethnicity=row['ethnicity'],
                ssn=row['ssn'],
                address=row['address']

             )
            session.add(patient)
            try:
                session.commit()
                added +=1
            except Exception as e:
                session.rollback()
                skipped +=1

            if (i + 1) % batch_size == 0:
                print(f"  Processed {i + 1}/{len(df)} patients...")
                session.commit()

        session.commit()

    print(f"Added {added} patients. Skipped {skipped} duplicate entries.")
    return

def load_conditions(filepath: str, batch_size: int = 1000):
    df= pd.read_parquet(filepath)
    required_columns = ['patient_id', 'conditions']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    engine = get_engine()
    with Session(engine) as session:
        added =0
        skipped =0
        patients_not_found =0
        for idx, row in df.iterrows():
            patient_id = row['patient_id']
            patient = session.get(Patient, patient_id)
            if not patient:
                print(f"Patient {patient_id} not found in database, skipping condition...")
                patients_not_found += 1
                continue
            condition = PatientCondition(
                patient_id=patient_id,
                conditions=row['conditions']
             )
            
            session.add(condition)
            try:
                session.commit()
                added +=1
            except Exception as e:
                session.rollback()
                skipped +=1

            if (idx + 1) % batch_size == 0:
                print(f"  Processed {idx + 1}/{len(df)} patient conditions...")
                session.commit()

        session.commit()

    print(f"Added {added} patient conditions. Skipped {skipped} duplicate entries.{patients_not_found} patients not found.")
    return

def load_trials(filepath: str, batch_size: int = 1000):
    """Load clinical trials from JSON file"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Clinical trials file not found: {filepath}")
    
    # Read JSON file
    with open(filepath, 'r',encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total trials to load: {len(data)}")
    
    engine = get_engine()
    with Session(engine) as session:
        added = 0
        skipped = 0
        
        for i, (nct_id, content) in enumerate(data.items()):
            # Extract text from document field
            text = content.get('document', '')
            
            # Extract conditions from metadata
            metadata = content.get('metadata', {})
            conds_count = metadata.get('conditions_count', 0)
            conditions = []
            
            for j in range(conds_count):
                condition = metadata.get(f'condition_{j+1}', '')
                if condition:
                    conditions.append(condition)
            
            # Convert conditions list to comma-separated string
            conditions_str = ', '.join(conditions)
            
            trial = AACTTrial(
                nct_id=nct_id,
                text=text,
                conditions=conditions_str
            )
            session.add(trial)
            
            try:
                session.commit()
                added += 1
            except Exception as e:
                session.rollback()
                skipped += 1
                if added == 0 and skipped == 1:
                    print(f"   Error on first record: {e}")

            if (i + 1) % batch_size == 0:
                print(f"  Processed {i + 1}/{len(data)} trials...")
                session.commit()

        session.commit()

    print(f"Added {added} trials. Skipped {skipped} duplicate entries.")
    return added, skipped

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python database_init_simple.py <demographics.parquet> <conditions.parquet>")
        sys.exit(1)
    
    demographics_filename = sys.argv[1]
    conditions_filename = sys.argv[2]
    clincal_trails_filename = sys.argv[3]
    demographics = os.path.join(DATA_DIR,demographics_filename)
    conditions = os.path.join(DATA_DIR,conditions_filename)
    clinical_trails = os.path.join(DATA_DIR,clincal_trails_filename)

    print("Dropping existing tables if any...")
    drop_tables()

    print("Creating tables...")
    create_tables()
    
    print(f"Loading patients from {demographics}...")
    load_demographics(demographics,batch_size=1000)
    
    print(f"Loading conditions from {conditions}...")
    load_conditions(conditions,batch_size=1000)

    print(f"Loading clinical trials from {clinical_trails}...")
    load_trials(clinical_trails,batch_size=1000)
    
    print("\nDone!")






