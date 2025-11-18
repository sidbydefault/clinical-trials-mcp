from sqlmodel import create_engine, Session, select
from models import Patient, PatientCondition, AACTTrial
from dotenv import load_dotenv
import os
import json
load_dotenv()

def get_engine():
    """Get database engine"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return create_engine(database_url)


engine = get_engine()


with Session(engine) as session:
    statement = select(Patient).where(Patient.age >50).limit(5).offset(10)
    results = session.exec(statement)
    for patient in results:
        print(patient)
        print("*****************************")
        print(patient.conditions)
   

filepath = '/home/sid/clinical-trials-mcp/data/raw/clinical_documents_with_metadata_final.json'
with open(filepath,'r',encoding='utf-8') as f:
        data = json.load(f)

for nct_id, content in data.items():

    text = content['document']
    metadata = content['metadata']
    conds_count = metadata.get('conditions_count',0)
    conditions=[]
    for i in range(conds_count):
        condition = metadata.get(f'condition_{i+1}','')
        conditions.append(condition)
     