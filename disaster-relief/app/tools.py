import difflib
import json
import os
from google.adk.tools import ToolContext

# Resolve the path to the mock data folder
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def lookup_shelters(district: str) -> dict:
    """Searches for disaster relief shelters/camps in a given district in Kerala.

    Args:
        district: The name of the district in Kerala (e.g. Wayanad, Alappuzha,
          Ernakulam, Idukki).

    Returns:
        A dictionary containing the status of the lookup and a list of shelters
        found.
    """
    try:
        shelters_file = os.path.join(DATA_DIR, "shelters.json")
        if not os.path.exists(shelters_file):
            return {"status": "error", "message": "Shelters database not found."}

        with open(shelters_file, "r", encoding="utf-8") as f:
            shelters = json.load(f)

        # Unique districts list
        all_districts = list({s["district"] for s in shelters})
        search_term = district.strip().lower()
        matched_district = None

        # 1. Direct substring match (supports partials like "way" -> "Wayanad")
        for d in all_districts:
            if search_term in d.strip().lower() or d.strip().lower() in search_term:
                matched_district = d
                break

        # 2. Fuzzy match close spellings (cutoff=0.5 for tolerance)
        if not matched_district:
            close_matches = difflib.get_close_matches(district.strip(), all_districts, n=1, cutoff=0.5)
            if close_matches:
                matched_district = close_matches[0]

        if matched_district:
            matched = [s for s in shelters if s["district"] == matched_district]
            return {"status": "success", "shelters": matched}
        else:
            available = ", ".join(all_districts)
            return {
                "status": "not_found",
                "message": (
                    f"Sorry, I couldn't find shelter information for district '{district}' in our records. "
                    f"Currently available districts are: {available}. "
                    "Please check the spelling or specify another nearby district in Kerala."
                ),
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def lookup_hospitals(district: str) -> dict:
    """Searches for hospitals with active emergency support/ICU in a given district in Kerala.

    Args:
        district: The name of the district in Kerala (e.g. Wayanad, Alappuzha, Ernakulam, Idukki).

    Returns:
        A dictionary containing the status of the lookup and a list of hospitals found.
    """
    try:
        hospitals_file = os.path.join(DATA_DIR, "hospitals.json")
        if not os.path.exists(hospitals_file):
            return {"status": "error", "message": "Hospitals database not found."}

        with open(hospitals_file, "r", encoding="utf-8") as f:
            hospitals = json.load(f)

        # Unique districts list
        all_districts = list({h["district"] for h in hospitals})
        search_term = district.strip().lower()
        matched_district = None

        # 1. Direct substring match
        for d in all_districts:
            if search_term in d.strip().lower() or d.strip().lower() in search_term:
                matched_district = d
                break

        # 2. Fuzzy match close spellings
        if not matched_district:
            close_matches = difflib.get_close_matches(district.strip(), all_districts, n=1, cutoff=0.5)
            if close_matches:
                matched_district = close_matches[0]

        if matched_district:
            matched = [h for h in hospitals if h["district"] == matched_district]
            return {"status": "success", "hospitals": matched}
        else:
            available = ", ".join(all_districts)
            return {
                "status": "not_found",
                "message": (
                    f"Sorry, no active hospitals found in district '{district}' in our records. "
                    f"Currently available districts are: {available}. "
                    "Please check the spelling or contact the local state medical helpline at 108."
                ),
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def lookup_helplines() -> dict:
    """Returns the list of state and community emergency helplines for disaster relief.

    Returns:
        A dictionary containing emergency helpline numbers for police, fire, disaster management, and NGOs.
    """
    try:
        helplines_file = os.path.join(DATA_DIR, "helplines.json")
        if not os.path.exists(helplines_file):
            return {"status": "error", "message": "Helplines database not found."}

        with open(helplines_file, "r", encoding="utf-8") as f:
            helplines = json.load(f)
        return {"status": "success", "helplines": helplines}
    except Exception as e:
        return {"status": "error", "message": str(e)}

