"""
title: Chemical Properties Lookup
version: 2.0.0
description: Query PubChem database for chemical properties, safety data, and molecular information.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic, requests

# SYSTEM PROMPT FOR AI
# ====================
# Access REAL chemical data from PubChem database.
# Use this instead of relying on training data for chemical properties!
#
# CAPABILITIES:
#   - Chemical properties lookup
#   - GHS safety information
#   - CAS numbers and identifiers
#   - Physical properties
#   - Chemical synonyms
"""

import json
import re
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"


def _get_cid_by_name(name: str) -> Optional[int]:
    if not REQUESTS_AVAILABLE:
        return None
    try:
        url = f"{PUBCHEM_BASE}/compound/name/{requests.utils.quote(name)}/cids/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
            return cids[0] if cids else None
    except:
        pass
    return None


def _get_cid_by_cas(cas: str) -> Optional[int]:
    if not REQUESTS_AVAILABLE:
        return None
    try:
        url = f"{PUBCHEM_BASE}/compound/name/{cas}/cids/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
            return cids[0] if cids else None
    except:
        pass
    return None


def _get_compound_properties(cid: int) -> Dict[str, Any]:
    if not REQUESTS_AVAILABLE:
        return {}
    properties = [
        "MolecularFormula", "MolecularWeight", "CanonicalSMILES", "IUPACName",
        "InChI", "InChIKey", "XLogP", "ExactMass", "MonoisotopicMass", "TPSA",
        "Complexity", "HBondDonorCount", "HBondAcceptorCount",
        "RotatableBondCount", "HeavyAtomCount",
    ]
    try:
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{','.join(properties)}/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            props = data.get("PropertyTable", {}).get("Properties", [])
            return props[0] if props else {}
    except:
        pass
    return {}


def _get_compound_synonyms(cid: int, max_count: int = 20) -> List[str]:
    if not REQUESTS_AVAILABLE:
        return []
    try:
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            info = data.get("InformationList", {}).get("Information", [])
            if info:
                synonyms = info[0].get("Synonym", [])
                return synonyms[:max_count]
    except:
        pass
    return []


def _get_compound_description(cid: int) -> str:
    if not REQUESTS_AVAILABLE:
        return ""
    try:
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/description/JSON"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            info = data.get("InformationList", {}).get("Information", [])
            for item in info:
                desc = item.get("Description", "")
                if desc and len(desc) > 50:
                    return desc
    except:
        pass
    return ""


def _get_ghs_info(cid: int) -> Dict[str, Any]:
    if not REQUESTS_AVAILABLE:
        return {}
    try:
        url = f"{PUBCHEM_VIEW}/data/compound/{cid}/JSON?heading=GHS+Classification"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            ghs_info = {
                "hazard_statements": [],
                "precautionary_statements": [],
                "pictograms": [],
                "signal_word": ""
            }
            record = data.get("Record", {})
            sections = record.get("Section", [])

            for section in sections:
                section_str = json.dumps(section)
                h_codes = re.findall(r'H\d{3}[a-zA-Z]?', section_str)
                ghs_info["hazard_statements"].extend(h_codes)
                p_codes = re.findall(r'P\d{3}(?:\+P\d{3})*', section_str)
                ghs_info["precautionary_statements"].extend(p_codes)
                if "Danger" in section_str:
                    ghs_info["signal_word"] = "Danger"
                elif "Warning" in section_str:
                    ghs_info["signal_word"] = "Warning"

                pictogram_names = [
                    "Flammable", "Oxidizer", "Compressed Gas", "Corrosive",
                    "Toxic", "Harmful", "Health Hazard", "Environmental Hazard",
                    "Explosive", "Irritant"
                ]
                for pic in pictogram_names:
                    if pic in section_str and pic not in ghs_info["pictograms"]:
                        ghs_info["pictograms"].append(pic)

            ghs_info["hazard_statements"] = list(set(ghs_info["hazard_statements"]))
            ghs_info["precautionary_statements"] = list(set(ghs_info["precautionary_statements"]))[:10]
            return ghs_info
    except:
        pass
    return {}


def _find_cas_number(cid: int) -> Optional[str]:
    synonyms = _get_compound_synonyms(cid, max_count=100)
    cas_pattern = re.compile(r'^\d{2,7}-\d{2}-\d$')
    for syn in synonyms:
        if cas_pattern.match(syn):
            return syn
    return None


class Tools:
    class Valves(BaseModel):
        timeout_seconds: int = Field(default=15, description="API request timeout")
        max_synonyms: int = Field(default=15, description="Maximum synonyms to show")

    def __init__(self):
        self.citation = True
        self.valves = self.Valves()

    def lookup_chemical(self, query: str) -> str:
        """
        Look up a chemical compound from PubChem.

        Args:
            query: Chemical name, CAS number, or formula

        Returns:
            Chemical properties and identifiers.
        """
        if not REQUESTS_AVAILABLE:
            return "Error: 'requests' library not installed. Run: pip install requests"

        cid = None
        if re.match(r'^\d{2,7}-\d{2}-\d$', query):
            cid = _get_cid_by_cas(query)
        if not cid:
            cid = _get_cid_by_name(query)

        if not cid:
            return f"Chemical not found: '{query}'"

        props = _get_compound_properties(cid)
        cas = _find_cas_number(cid)
        description = _get_compound_description(cid)

        result = [
            f"Chemical: {query}", "=" * 50,
            f"PubChem CID: {cid}",
            f"URL: https://pubchem.ncbi.nlm.nih.gov/compound/{cid}", "",
        ]

        if cas:
            result.append(f"CAS Number: {cas}")

        result.extend([
            "", "IDENTIFIERS:",
            f"  IUPAC Name: {props.get('IUPACName', 'N/A')}",
            f"  Formula: {props.get('MolecularFormula', 'N/A')}",
            f"  SMILES: {props.get('CanonicalSMILES', 'N/A')}",
            f"  InChIKey: {props.get('InChIKey', 'N/A')}",
            "", "MOLECULAR PROPERTIES:",
            f"  Molecular Weight: {props.get('MolecularWeight', 'N/A')} g/mol",
            f"  Exact Mass: {props.get('ExactMass', 'N/A')} g/mol",
            f"  XLogP: {props.get('XLogP', 'N/A')}",
            f"  TPSA: {props.get('TPSA', 'N/A')} Å²",
            f"  Complexity: {props.get('Complexity', 'N/A')}",
            "", "STRUCTURE:",
            f"  Heavy Atoms: {props.get('HeavyAtomCount', 'N/A')}",
            f"  H-Bond Donors: {props.get('HBondDonorCount', 'N/A')}",
            f"  H-Bond Acceptors: {props.get('HBondAcceptorCount', 'N/A')}",
            f"  Rotatable Bonds: {props.get('RotatableBondCount', 'N/A')}",
        ])

        if description:
            result.extend(["", "DESCRIPTION:", f"  {description[:500]}{'...' if len(description) > 500 else ''}"])

        return "\n".join(result)

    def get_safety_info(self, query: str) -> str:
        """
        Get GHS safety/hazard information for a chemical.

        Args:
            query: Chemical name or CAS number

        Returns:
            GHS classification with hazard statements and pictograms.
        """
        if not REQUESTS_AVAILABLE:
            return "Error: 'requests' library not installed"

        cid = None
        if re.match(r'^\d{2,7}-\d{2}-\d$', query):
            cid = _get_cid_by_cas(query)
        if not cid:
            cid = _get_cid_by_name(query)

        if not cid:
            return f"Chemical not found: '{query}'"

        ghs = _get_ghs_info(cid)
        props = _get_compound_properties(cid)

        result = [
            f"Safety Information: {query}", "=" * 50,
            f"PubChem CID: {cid}",
            f"Formula: {props.get('MolecularFormula', 'N/A')}", "",
        ]

        if ghs.get("signal_word"):
            result.append(f"⚠️  SIGNAL WORD: {ghs['signal_word'].upper()}")
            result.append("")

        if ghs.get("pictograms"):
            result.append("GHS PICTOGRAMS:")
            for pic in ghs["pictograms"]:
                result.append(f"  • {pic}")
            result.append("")

        h_descriptions = {
            "H200": "Unstable explosive", "H220": "Extremely flammable gas",
            "H224": "Extremely flammable liquid and vapor",
            "H225": "Highly flammable liquid and vapor",
            "H226": "Flammable liquid and vapor", "H228": "Flammable solid",
            "H270": "May cause or intensify fire; oxidizer",
            "H280": "Contains gas under pressure",
            "H300": "Fatal if swallowed", "H301": "Toxic if swallowed",
            "H302": "Harmful if swallowed", "H304": "May be fatal if swallowed and enters airways",
            "H310": "Fatal in contact with skin", "H311": "Toxic in contact with skin",
            "H312": "Harmful in contact with skin",
            "H314": "Causes severe skin burns and eye damage",
            "H315": "Causes skin irritation", "H317": "May cause allergic skin reaction",
            "H318": "Causes serious eye damage", "H319": "Causes serious eye irritation",
            "H330": "Fatal if inhaled", "H331": "Toxic if inhaled",
            "H332": "Harmful if inhaled", "H334": "May cause allergy or asthma symptoms",
            "H335": "May cause respiratory irritation",
            "H336": "May cause drowsiness or dizziness",
            "H340": "May cause genetic defects", "H350": "May cause cancer",
            "H360": "May damage fertility or the unborn child",
            "H370": "Causes damage to organs",
            "H400": "Very toxic to aquatic life",
            "H410": "Very toxic to aquatic life with long lasting effects",
        }

        if ghs.get("hazard_statements"):
            result.append("HAZARD STATEMENTS (H-codes):")
            for h_code in sorted(ghs["hazard_statements"]):
                desc = h_descriptions.get(h_code, "")
                if desc:
                    result.append(f"  {h_code}: {desc}")
                else:
                    result.append(f"  {h_code}")
            result.append("")

        if ghs.get("precautionary_statements"):
            result.append("PRECAUTIONARY STATEMENTS (P-codes):")
            for p_code in sorted(ghs["precautionary_statements"])[:10]:
                result.append(f"  {p_code}")
            result.append("")

        if not ghs.get("hazard_statements") and not ghs.get("pictograms"):
            result.append("No GHS classification data found in PubChem.")
            result.append("⚠️  Always consult official Safety Data Sheets (SDS)")

        result.extend([
            "", "Note: Always verify with official SDS from manufacturer.",
            f"Full data: https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=Safety-and-Hazards",
        ])

        return "\n".join(result)

    def get_synonyms(self, query: str) -> str:
        """
        Get alternative names and synonyms for a chemical.

        Args:
            query: Chemical name or CAS number

        Returns:
            List of synonyms and trade names.
        """
        if not REQUESTS_AVAILABLE:
            return "Error: 'requests' library not installed"

        cid = None
        if re.match(r'^\d{2,7}-\d{2}-\d$', query):
            cid = _get_cid_by_cas(query)
        if not cid:
            cid = _get_cid_by_name(query)

        if not cid:
            return f"Chemical not found: '{query}'"

        synonyms = _get_compound_synonyms(cid, max_count=self.valves.max_synonyms)
        props = _get_compound_properties(cid)
        cas = _find_cas_number(cid)

        result = [
            f"Synonyms for: {query}", "=" * 50,
            f"PubChem CID: {cid}",
            f"Formula: {props.get('MolecularFormula', 'N/A')}",
            f"IUPAC Name: {props.get('IUPACName', 'N/A')}",
        ]

        if cas:
            result.append(f"CAS Number: {cas}")

        result.extend(["", f"SYNONYMS ({len(synonyms)} shown):"])
        for i, syn in enumerate(synonyms, 1):
            result.append(f"  {i:2}. {syn}")

        result.extend(["", f"Full list: https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section=Synonyms"])

        return "\n".join(result)

    def compare_chemicals(self, chemical1: str, chemical2: str) -> str:
        """
        Compare properties of two chemicals.

        Args:
            chemical1: First chemical name or CAS
            chemical2: Second chemical name or CAS

        Returns:
            Side-by-side comparison.
        """
        if not REQUESTS_AVAILABLE:
            return "Error: 'requests' library not installed"

        cid1 = _get_cid_by_name(chemical1) or _get_cid_by_cas(chemical1)
        cid2 = _get_cid_by_name(chemical2) or _get_cid_by_cas(chemical2)

        if not cid1:
            return f"Chemical not found: '{chemical1}'"
        if not cid2:
            return f"Chemical not found: '{chemical2}'"

        props1 = _get_compound_properties(cid1)
        props2 = _get_compound_properties(cid2)

        result = [
            "Chemical Comparison", "=" * 60, "",
            f"{'Property':<25} {'Chemical 1':<17} {'Chemical 2':<17}",
            f"{'':_<25} {'':_<17} {'':_<17}", "",
            f"{'Name':<25} {chemical1:<17} {chemical2:<17}",
            f"{'PubChem CID':<25} {cid1:<17} {cid2:<17}",
            f"{'Formula':<25} {str(props1.get('MolecularFormula', 'N/A')):<17} {str(props2.get('MolecularFormula', 'N/A')):<17}",
            f"{'Mol. Weight (g/mol)':<25} {str(props1.get('MolecularWeight', 'N/A')):<17} {str(props2.get('MolecularWeight', 'N/A')):<17}",
            f"{'XLogP':<25} {str(props1.get('XLogP', 'N/A')):<17} {str(props2.get('XLogP', 'N/A')):<17}",
            f"{'TPSA (Å²)':<25} {str(props1.get('TPSA', 'N/A')):<17} {str(props2.get('TPSA', 'N/A')):<17}",
            f"{'H-Bond Donors':<25} {str(props1.get('HBondDonorCount', 'N/A')):<17} {str(props2.get('HBondDonorCount', 'N/A')):<17}",
            f"{'H-Bond Acceptors':<25} {str(props1.get('HBondAcceptorCount', 'N/A')):<17} {str(props2.get('HBondAcceptorCount', 'N/A')):<17}",
            "", "Links:",
            f"  Chemical 1: https://pubchem.ncbi.nlm.nih.gov/compound/{cid1}",
            f"  Chemical 2: https://pubchem.ncbi.nlm.nih.gov/compound/{cid2}",
        ]

        return "\n".join(result)

    def check_availability(self) -> str:
        """Check if PubChem API is accessible."""
        if not REQUESTS_AVAILABLE:
            return "❌ 'requests' library not installed."

        try:
            response = requests.get(
                f"{PUBCHEM_BASE}/compound/name/water/cids/JSON",
                timeout=10
            )
            if response.status_code == 200:
                return "✅ PubChem API is accessible and working."
            else:
                return f"⚠️ PubChem API returned status {response.status_code}"
        except requests.exceptions.Timeout:
            return "❌ PubChem API request timed out."
        except requests.exceptions.RequestException as e:
            return f"❌ Cannot connect to PubChem API: {str(e)}"
