from .database import get_db
from database_creation.models import Patient, PatientCondition, AACTTrial
from sqlmodel import select
from .vectorstore import get_vector_store

# db = get_db()

# with db.get_session() as s:
#     print(s.exec(select(Patient).limit(1)).all())


# eligible = db.find_eligible_patients(
#     age_min=40,
#     age_max=70,
#     required_conditions=["diabetes mellitus"],
# )
# print("eligible patients")
# print(eligible)
# print("*********************************************\n")

vs = get_vector_store()

# A harmless test query—change if needed
query = "Search for immunotherapy trials for metastatic melanoma"


results_search = vs.search(query, top_k=2)

print("basic search")
print(results_search)
