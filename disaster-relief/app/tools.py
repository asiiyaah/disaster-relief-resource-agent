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

        # Case-insensitive matching
        matched = [
            s
            for s in shelters
            if s["district"].strip().lower() == district.strip().lower()
        ]

        if matched:
            return {"status": "success", "shelters": matched}
        else:
            return {
                "status": "not_found",
                "message": (
                    f"No shelters found in district '{district}'. Please specify"
                    " another nearby district in Kerala (e.g. Wayanad, Alappuzha,"
                    " Ernakulam, Idukki)."
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

        matched = [
            h
            for h in hospitals
            if h["district"].strip().lower() == district.strip().lower()
        ]

        if matched:
            return {"status": "success", "hospitals": matched}
        else:
            return {
                "status": "not_found",
                "message": (
                    f"No hospitals found in district '{district}'. Please specify another Kerala district "
                    "(e.g. Wayanad, Alappuzha, Ernakulam, Idukki) or contact local state helpline at 1077."
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

