import statistics
from typing import Optional, Any
from dotenv import load_dotenv

from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult 

load_dotenv()

mcp = FastMCP("clinical-trial-recommendation-mcp")


def parse_conditions(cond: str) -> list[str]:
    """Parse comma-separated condition string into list."""
    if not cond:
        return []
    if isinstance(cond, str):
        parts = [c.strip() for c in cond.split(",") if c.strip()]
        return parts
    return []


@mcp.tool(
    name="search_trials",
    description="Search clinical trials using a query and optional filters.",
    annotations={"readOnlyHint": True}
)
def search_trials(
    query: str,
    top_k: int = 5,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    min_enrollment: Optional[int] = None
) -> dict[str, Any]:
    """
    Search for clinical trials using semantic search with optional filters.
    
    Args:
        query: Search query (e.g., "diabetes cardiovascular trial")
        top_k: Number of results to return (default: 5)
        phase: Filter by phase (e.g., "Phase 2", "Phase 3")
        status: Filter by status (e.g., "COMPLETED", "RECRUITING")
        min_enrollment: Minimum enrollment count
    
    Returns:
        Dictionary with query, filters, count, and list of trials
    """
    from .vectorstore import get_vector_store

    try:
        vs = get_vector_store()
        
        # Build filters dictionary only if filters provided
        filters = None
        if phase or status or min_enrollment:
            filters = {
                "phase": phase,
                "status": status,
                "min_enrollment": min_enrollment
            }
        
        trials = vs.search(
            query=query,
            top_k=top_k,
            filters=filters,
            enrich_from_db=True
        )
        
        return {
            "query": query,
            "filters": {
                "phase": phase,
                "status": status,
                "min_enrollment": min_enrollment
            },
            "count": len(trials),
            "trials": trials
        }
    
    except Exception as e:
        return {
            "error": f"Search failed: {str(e)}",
            "query": query,
            "count": 0,
            "trials": []
        }


@mcp.tool(
    name="find_eligible_patients",
    description="Find patients by age range, gender, and required clinical conditions.",
    annotations={"readOnlyHint": True}
)
def find_eligible_patients(
    age_min: int,
    age_max: int,
    required_conditions: Optional[list[str]] = None,
    limit: int = 100
) -> dict[str, Any]:
    """
    Find patients matching eligibility criteria.
    
    Args:
        age_min: Minimum age (inclusive)
        age_max: Maximum age (inclusive)
        required_conditions: List of required conditions (uses semantic matching)
        limit: Maximum number of patients to return (default: 100)
    
    Returns:
        Dictionary with criteria, demographics summary, and list of patients
    """
    from .database import get_db 

    try:
        db = get_db()
        patients = db.find_eligible_patients(
            age_min=age_min,
            age_max=age_max,
            required_conditions=required_conditions,
            limit=limit
        )
        
        # Build demographics summary
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
    
    except Exception as e:
        return {
            "error": f"Patient search failed: {str(e)}",
            "criteria": {
                "age_min": age_min,
                "age_max": age_max,
                "required_conditions": required_conditions or []
            },
            "demographics_summary": {"total": 0},
            "patients": []
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
    """
    Complete workflow: search trials, infer criteria, match patients, assess feasibility.
    
    Args:
        query: Search query (e.g., "Phase 2 diabetes HbA1c trial")
        top_k_trials: Number of similar trials to analyze (default: 5)
        max_patients: Maximum patients to return (default: 200, but limited by median_enrollment)
    
    Returns:
        ToolResult with content summary and structured data including:
        - Similar trials
        - Inferred criteria (age, conditions, enrollment)
        - Matched patients with demographics
        - Feasibility analysis
    """
    from .vectorstore import get_vector_store
    from .database import get_db

    try:
        #Search for similar trials
        vs = get_vector_store()
        trials = vs.search(
            query=query,
            top_k=top_k_trials,
            filters=None,
            enrich_from_db=True
        )

        # Extract and parse conditions
        all_conditions = []
        trials_with_parsed_conditions = []
        
        for t in trials:
            conditions_str = t.get("conditions", "")
            parsed_conditions = parse_conditions(conditions_str)
            
            # Create new trial dict with parsed conditions
            trial_copy = t.copy()
            trial_copy["conditions_parsed"] = parsed_conditions
            trials_with_parsed_conditions.append(trial_copy)
            
            all_conditions.extend(parsed_conditions)

        #Deduplicate conditions (preserve order)
        seen = set()
        unique_conditions = [c for c in all_conditions if not (c in seen or seen.add(c))]

        # Infer age ranges from trial metadata
        min_ages = []
        max_ages = []
        enrollments = []
        
        for t in trials_with_parsed_conditions:
            # Extract minimum age
            mn = t.get("minimum_age")
            try:
                if mn not in (None, "", "NA"):
                    min_ages.append(int(float(mn)))
            except (ValueError, TypeError):
                pass
            
            # Extract maximum age
            mx = t.get("maximum_age")
            try:
                if mx not in (None, "", "NA"):
                    max_ages.append(int(float(mx)))
            except (ValueError, TypeError):
                pass
            
            # Extract enrollment
            en = t.get("enrollment")
            try:
                if en not in (None, "", "NA"):
                    enrollments.append(int(float(en)))
            except (ValueError, TypeError):
                pass

        # Calculate inferred criteria
        inferred_min_age = statistics.median(min_ages) if min_ages else None
        inferred_max_age = statistics.median(max_ages) if max_ages else None
        inferred_enrollment = statistics.median(enrollments) if enrollments else None

        # Determine patient limit
        # Use median_enrollment if available, otherwise default to 100
        patient_limit = int(inferred_enrollment) if inferred_enrollment is not None else 100
        
        # Cap at max_patients to respect user's limit
        patient_limit = min(patient_limit, max_patients)

        # Fetch patients if we have valid age criteria
        patients = []
        demographics = {}
        feasibility = {}
        
        if inferred_min_age is not None and inferred_max_age is not None:
            db = get_db()
            patients = db.find_eligible_patients(
                age_min=int(inferred_min_age),
                age_max=int(inferred_max_age),
                required_conditions=unique_conditions if unique_conditions else None,
                limit=patient_limit
            )

            # Build demographics summary
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

            # Calculate feasibility metrics
            target_enrollment = inferred_enrollment if inferred_enrollment else patient_limit
            available_ratio = len(patients) / target_enrollment if target_enrollment > 0 else 0
            
            feasibility = {
                "target_enrollment": target_enrollment,
                "available_patients": len(patients),
                "availability_ratio": round(available_ratio, 2),
                "feasibility_level": (
                    "HIGH" if available_ratio >= 1.5 else
                    "MEDIUM" if available_ratio >= 1.0 else
                    "LOW"
                ),
                "recruitment_risk": (
                    "Minimal" if available_ratio >= 2.0 else
                    "Moderate" if available_ratio >= 1.2 else
                    "High"
                )
            }

        # Build structured result
        result = {
            "query": query,
            "top_k_trials": top_k_trials,
            "inferred_criteria": {
                "conditions": unique_conditions,
                "median_min_age": inferred_min_age,
                "median_max_age": inferred_max_age,
                "median_enrollment": inferred_enrollment,
                "patient_limit_used": patient_limit
            },
            "similar_trials": trials_with_parsed_conditions,
            "patient_recruitment": {
                "demographics_summary": demographics,
                "matched_patients": patients,
                "feasibility": feasibility
            }
        }

        # Build human-readable content
        content = (
            f"Found {len(trials_with_parsed_conditions)} similar trials. "
            f"Inferred {len(unique_conditions)} unique conditions: {', '.join(unique_conditions[:5])}{'...' if len(unique_conditions) > 5 else ''}. "
            f"Age range: {inferred_min_age}–{inferred_max_age}. "
            f"Target enrollment: {inferred_enrollment if inferred_enrollment else 'N/A'}. "
            f"Matched {len(patients)} patients (feasibility: {feasibility.get('feasibility_level', 'UNKNOWN')})."
        )

        return ToolResult(content=content, structured_content=result)
    
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        return ToolResult(
            content=error_msg,
            structured_content={
                "error": error_msg,
                "query": query
            }
        )