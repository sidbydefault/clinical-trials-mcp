import statistics
from typing import Optional,List,Dict
from dotenv import load_dotenv 

from fastmcp import FastMCP 
from fastmcp.tools.tool import ToolResult 

load_dotenv()

mcp = FastMCP("clinical-trial-recommedation-mcp")

def parse_conditions(cond):

    if not cond:
        return []
    if isinstance(cond,str):
        parts = [c.strip() for c in cond.split(",") if c.strip()]
        return parts
    else:
        return []

@mcp.tool(
        name = "search_trials",
        description="Search clinical trials using a query and optional filters.",
        annotations={"readOnlyHint": True}
)
def search_trials(
    query: str,
    top_k: int = 5,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    min_enrollment : Optional[int] = None
):
    from .vectorstore import get_vector_store

    vs = get_vector_store()
    trials = vs.search(
        query=query,
        top_k=top_k,
        filters={"phase": phase, "status": status, "min_enrollment": min_enrollment}
                if (phase or status or min_enrollment) else None,
        enrich_from_db=True
    )
    return {
        "query": query,
        "filters": {"phase": phase, "status": status, "min_enrollment": min_enrollment},
        "count": len(trials),
        "trials": trials
    }

@mcp.tool(
    name="find_eligible_patients",
    description="Find patients by age range, gender, and required clinical conditions.",
    annotations={"readOnlyHint": True}
)
def find_eligible_patients(
    age_min: int,
    age_max: int,
    required_conditions: Optional[List[str]] = None,
    limit: int = 100
):
    from .database import get_db 

    db = get_db()
    patients = db.find_eligible_patients(
        age_min=age_min,
        age_max=age_max,
        required_conditions=required_conditions,
        limit=limit
    )
    summary = {
        "total": len(patients),
        "age": {},
        "gender": {},
        "race": {},
        "ethnicity": {}
    }
    if patients:
        ages = [p["age"] for p in patients]
        summary["age"]["min"] = min(ages)
        summary["age"]["max"] = max(ages)
        summary["age"]["median"] = statistics.median(ages)
        summary["age"]["mean"] = round(statistics.mean(ages), 1)

        for p in patients:
            summary["gender"][p["gender"]] = summary["gender"].get(p["gender"], 0) + 1
            summary["race"][p["race"]] = summary["race"].get(p["race"], 0) + 1
            summary["ethnicity"][p["ethnicity"]] = summary["ethnicity"].get(p["ethnicity"], 0) + 1

    return {
        "criteria": {
            "age_min": age_min,
            "age_max": age_max,
            "required_conditions": required_conditions or []
        },
        "demographics_summary": summary,
        "patients": patients
    }
    
@mcp.tool(
    name="analyze_trials_and_match_patients",
    description="Infer eligibility criteria from top trials and find matching patients.",
    annotations={"readOnlyHint": True}
)
def analyze_trials_and_match_patients(
    query: str,
    top_k_trials: int = 5,
    max_patients: int = 200
) -> ToolResult:
    from src.vectorstore import get_vector_store
    from src.database import get_db

    vs = get_vector_store()
    trials = vs.search(
        query=query,
        top_k=top_k_trials,
        filters=None,
        enrich_from_db=True
    )

    # Extract conditions
    all_conditions = []
    for t in trials:
        conds = parse_conditions(t.get("conditions"))
        t["conditions"] = conds
        all_conditions.extend(conds)

    # Dedupe in order
    seen = set()
    unique_conditions = [c for c in all_conditions if not (c in seen or seen.add(c))]

    # Infer age
    min_ages= []
    max_ages= []
    enrollments =[]
    for t in trials:
        mn = t.get("minimum_age")
        mx = t.get("maximum_age")
        en = t.get("enrollment")
        try:
            if mn not in (None, "", "NA"):
                min_ages.append(int(float(mn)))
        except:
            pass
        try:
            if mx not in (None, "", "NA"):
                max_ages.append(int(float(mx)))
        except:
            pass
        try:
            if en not in (None, "", "NA"):
                enrollments.append(int(float(en)))
        except:
            pass

    inferred_min_age = statistics.median(min_ages) if min_ages else None
    inferred_max_age = statistics.median(max_ages) if max_ages else None
    inferred_enrollment = statistics.median(enrollments) if enrollments else 100

    # Fetch patients
    patients = []
    demographics = {}
    if inferred_min_age is not None and inferred_max_age is not None:
        db = get_db()
        patients = db.find_eligible_patients(
            age_min=int(inferred_min_age),
            age_max=int(inferred_max_age),
            required_conditions=unique_conditions,
            limit=inferred_enrollment 
        )

        # Build patient demographics summary
        demographics = {
            "total": len(patients),
            "age": {},
            "gender": {},
            "race": {},
            "ethnicity": {}
        }

        if patients:
            ages = [p["age"] for p in patients]
            demographics["age"]["min"] = min(ages)
            demographics["age"]["max"] = max(ages)
            demographics["age"]["median"] = statistics.median(ages)
            demographics["age"]["mean"] = round(statistics.mean(ages), 1)
            for p in patients:
                demographics["gender"][p["gender"]] = demographics["gender"].get(p["gender"], 0) + 1
                demographics["race"][p["race"]] = demographics["race"].get(p["race"], 0) + 1
                demographics["ethnicity"][p["ethnicity"]] = demographics["ethnicity"].get(p["ethnicity"], 0) + 1

        available_ratio = len(patients) / inferred_enrollment if inferred_enrollment > 0 else 0
        feasibility = {
            "target_enrollment": inferred_enrollment,
            "available_patients": len(patients),
            "availability_ratio": round(available_ratio, 2),
            "feasibility_level": "HIGH" if available_ratio >= 1.5 else "MEDIUM" if available_ratio >= 1.0 else "LOW",
            "recruitment_risk": "Minimal" if available_ratio >= 2.0 else "Moderate" if available_ratio >= 1.2 else "High"
        }

    # Build structured result
    result = {
        "query": query,
        "top_k_trials": top_k_trials,
        "inferred_criteria": {
            "conditions": unique_conditions,
            "median_min_age": inferred_min_age,
            "median_max_age": inferred_max_age,
            "median enrollment":inferred_enrollment
        },
        "similar_trials": trials,
        
        "patient_recruitment":{
            "demographics_summary":demographics,
            "matched_patients": patients,
            "feasibility": feasibility
            }
    }

    # Build human-readable content
    content = (
        f"Found {len(trials)} trials. Inferred {len(unique_conditions)} conditions: "
        f"{', '.join(unique_conditions)}. Age: {inferred_min_age}–{inferred_max_age}."
        f"(feasibility: {feasibility.get('feasibility_level', 'UNKNOWN')})."
        
    )

    return ToolResult(content=[content], structured_content=result)



