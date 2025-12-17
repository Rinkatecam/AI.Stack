"""
title: Scientific Calculator
version: 2.0.0
description: Precise mathematical calculations, unit conversions, formula scaling, and statistical analysis.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic, numpy, scipy

# SYSTEM PROMPT FOR AI
# ====================
# LLMs are notoriously bad at math - USE THIS TOOL for any calculations!
#
# CAPABILITIES:
#   - Arithmetic and scientific functions
#   - Unit conversions
#   - Formula scaling
#   - Statistical analysis
#   - Molar mass calculations
#   - Dilution calculations
"""

import math
import re
import json
from typing import Optional, List, Dict, Union, Any
from pydantic import BaseModel, Field

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


PERIODIC_TABLE = {
    "H": 1.008, "He": 4.003, "Li": 6.941, "Be": 9.012, "B": 10.81,
    "C": 12.01, "N": 14.01, "O": 16.00, "F": 19.00, "Ne": 20.18,
    "Na": 22.99, "Mg": 24.31, "Al": 26.98, "Si": 28.09, "P": 30.97,
    "S": 32.07, "Cl": 35.45, "Ar": 39.95, "K": 39.10, "Ca": 40.08,
    "Sc": 44.96, "Ti": 47.87, "V": 50.94, "Cr": 52.00, "Mn": 54.94,
    "Fe": 55.85, "Co": 58.93, "Ni": 58.69, "Cu": 63.55, "Zn": 65.38,
    "Ga": 69.72, "Ge": 72.63, "As": 74.92, "Se": 78.97, "Br": 79.90,
    "Kr": 83.80, "Rb": 85.47, "Sr": 87.62, "Y": 88.91, "Zr": 91.22,
    "Nb": 92.91, "Mo": 95.95, "Tc": 98.00, "Ru": 101.1, "Rh": 102.9,
    "Pd": 106.4, "Ag": 107.9, "Cd": 112.4, "In": 114.8, "Sn": 118.7,
    "Sb": 121.8, "Te": 127.6, "I": 126.9, "Xe": 131.3, "Cs": 132.9,
    "Ba": 137.3, "La": 138.9, "Ce": 140.1, "Pr": 140.9, "Nd": 144.2,
    "Pm": 145.0, "Sm": 150.4, "Eu": 152.0, "Gd": 157.3, "Tb": 158.9,
    "Dy": 162.5, "Ho": 164.9, "Er": 167.3, "Tm": 168.9, "Yb": 173.0,
    "Lu": 175.0, "Hf": 178.5, "Ta": 180.9, "W": 183.8, "Re": 186.2,
    "Os": 190.2, "Ir": 192.2, "Pt": 195.1, "Au": 197.0, "Hg": 200.6,
    "Tl": 204.4, "Pb": 207.2, "Bi": 209.0, "Po": 209.0, "At": 210.0,
    "Rn": 222.0, "Fr": 223.0, "Ra": 226.0, "Ac": 227.0, "Th": 232.0,
    "Pa": 231.0, "U": 238.0, "Np": 237.0, "Pu": 244.0, "Am": 243.0,
}

UNIT_CONVERSIONS = {
    "kg": 1.0, "g": 0.001, "mg": 0.000001, "ug": 0.000000001,
    "ng": 0.000000000001, "lb": 0.453592, "oz": 0.0283495, "t": 1000.0,
    "L": 1.0, "l": 1.0, "mL": 0.001, "ml": 0.001, "uL": 0.000001,
    "ul": 0.000001, "m3": 1000.0, "cm3": 0.001, "mm3": 0.000001,
    "gal": 3.78541, "qt": 0.946353, "pt": 0.473176, "fl_oz": 0.0295735,
    "m": 1.0, "cm": 0.01, "mm": 0.001, "um": 0.000001, "nm": 0.000000001,
    "km": 1000.0, "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.34,
    "Pa": 1.0, "kPa": 1000.0, "MPa": 1000000.0, "bar": 100000.0,
    "mbar": 100.0, "atm": 101325.0, "psi": 6894.76, "mmHg": 133.322, "torr": 133.322,
    "M": 1.0, "mM": 0.001, "uM": 0.000001, "nM": 0.000000001,
    "mol/L": 1.0, "mmol/L": 0.001,
    "%": 0.01, "ppm": 0.000001, "ppb": 0.000000001,
}

UNIT_CATEGORIES = {
    "mass": ["kg", "g", "mg", "ug", "ng", "lb", "oz", "t"],
    "volume": ["L", "l", "mL", "ml", "uL", "ul", "m3", "cm3", "mm3", "gal", "qt", "pt", "fl_oz"],
    "length": ["m", "cm", "mm", "um", "nm", "km", "in", "ft", "yd", "mi"],
    "pressure": ["Pa", "kPa", "MPa", "bar", "mbar", "atm", "psi", "mmHg", "torr"],
    "concentration": ["M", "mM", "uM", "nM", "mol/L", "mmol/L"],
    "ratio": ["%", "ppm", "ppb"],
}


def _get_unit_category(unit: str) -> Optional[str]:
    for category, units in UNIT_CATEGORIES.items():
        if unit in units:
            return category
    return None


def _safe_eval(expression: str) -> float:
    """Safely evaluate a mathematical expression."""
    allowed_names = {
        "pi": math.pi, "e": math.e, "tau": math.tau, "inf": float("inf"),
        "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow,
        "sqrt": math.sqrt, "cbrt": lambda x: x ** (1/3), "exp": math.exp,
        "log": math.log, "log10": math.log10, "log2": math.log2, "ln": math.log,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan, "atan2": math.atan2,
        "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
        "ceil": math.ceil, "floor": math.floor, "factorial": math.factorial,
        "gcd": math.gcd, "degrees": math.degrees, "radians": math.radians,
    }

    expr = expression.strip()
    expr = expr.replace("^", "**").replace("×", "*").replace("÷", "/")

    if not re.match(r'^[\d\s\+\-\*\/\.\(\)\,\w]+$', expr):
        raise ValueError(f"Invalid characters in expression: {expression}")

    try:
        result = eval(expr, {"__builtins__": {}}, allowed_names)
        return float(result)
    except Exception as e:
        raise ValueError(f"Cannot evaluate expression: {expression} - {str(e)}")


def _parse_formula(formula: str) -> Dict[str, int]:
    """Parse a chemical formula into element counts."""
    elements = {}
    formula = formula.strip().replace(" ", "")
    pattern = r'([A-Z][a-z]?)(\d*)'

    paren_pattern = r'\(([^)]+)\)(\d+)'
    while re.search(paren_pattern, formula):
        match = re.search(paren_pattern, formula)
        group_formula = match.group(1)
        multiplier = int(match.group(2))
        group_elements = _parse_formula(group_formula)
        replacement = ""
        for elem, count in group_elements.items():
            replacement += f"{elem}{count * multiplier}"
        formula = formula[:match.start()] + replacement + formula[match.end():]

    for match in re.finditer(pattern, formula):
        element = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        if element:
            if element in PERIODIC_TABLE:
                elements[element] = elements.get(element, 0) + count
            elif element not in ["", " "]:
                raise ValueError(f"Unknown element: {element}")

    return elements


class Tools:
    class Valves(BaseModel):
        decimal_places: int = Field(
            default=6,
            description="Decimal places for results (1-15)"
        )
        scientific_notation_threshold: float = Field(
            default=1000000.0,
            description="Use scientific notation above this value"
        )

    def __init__(self):
        self.citation = False
        self.valves = self.Valves()

    def _format_result(self, value: float, unit: str = "") -> str:
        decimals = max(1, min(15, self.valves.decimal_places))
        threshold = self.valves.scientific_notation_threshold

        if abs(value) >= threshold or (abs(value) < 0.0001 and value != 0):
            formatted = f"{value:.{decimals}e}"
        else:
            formatted = f"{value:.{decimals}f}".rstrip('0').rstrip('.')

        if unit:
            return f"{formatted} {unit}"
        return formatted

    def calculate(self, expression: str) -> str:
        """
        Evaluate a mathematical expression.

        Args:
            expression: Math expression (supports sqrt, log, sin, cos, etc.)

        Returns:
            Calculated result.
        """
        try:
            result = _safe_eval(expression)
            return f"{expression} = {self._format_result(result)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def convert_units(self, value: float, from_unit: str, to_unit: str) -> str:
        """
        Convert between units.

        Args:
            value: Numeric value
            from_unit: Source unit (e.g., "g", "mL", "psi")
            to_unit: Target unit (e.g., "kg", "L", "bar")

        Returns:
            Converted value.
        """
        if from_unit in ["C", "°C", "F", "°F", "K"]:
            return self._convert_temperature(value, from_unit, to_unit)

        from_unit_clean = from_unit.strip()
        to_unit_clean = to_unit.strip()

        if from_unit_clean not in UNIT_CONVERSIONS:
            return f"Error: Unknown unit '{from_unit}'"

        if to_unit_clean not in UNIT_CONVERSIONS:
            return f"Error: Unknown unit '{to_unit}'"

        from_category = _get_unit_category(from_unit_clean)
        to_category = _get_unit_category(to_unit_clean)

        if from_category != to_category:
            return f"Error: Cannot convert {from_unit} ({from_category}) to {to_unit} ({to_category})"

        base_value = value * UNIT_CONVERSIONS[from_unit_clean]
        result = base_value / UNIT_CONVERSIONS[to_unit_clean]

        return f"{self._format_result(value)} {from_unit} = {self._format_result(result)} {to_unit}"

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> str:
        from_u = from_unit.replace("°", "").upper()
        to_u = to_unit.replace("°", "").upper()

        if from_u == "C":
            kelvin = value + 273.15
        elif from_u == "F":
            kelvin = (value - 32) * 5/9 + 273.15
        elif from_u == "K":
            kelvin = value
        else:
            return f"Error: Unknown temperature unit '{from_unit}'"

        if to_u == "C":
            result = kelvin - 273.15
        elif to_u == "F":
            result = (kelvin - 273.15) * 9/5 + 32
        elif to_u == "K":
            result = kelvin
        else:
            return f"Error: Unknown temperature unit '{to_unit}'"

        return f"{self._format_result(value)} {from_unit} = {self._format_result(result)} {to_unit}"

    def molar_mass(self, formula: str) -> str:
        """
        Calculate molar mass of a chemical compound.

        Args:
            formula: Chemical formula (e.g., "H2O", "NaCl", "Ca(OH)2")

        Returns:
            Molar mass in g/mol with breakdown.
        """
        try:
            elements = _parse_formula(formula)

            if not elements:
                return f"Error: Could not parse formula '{formula}'"

            total_mass = 0.0
            breakdown = []

            for element, count in sorted(elements.items()):
                if element not in PERIODIC_TABLE:
                    return f"Error: Unknown element '{element}'"

                atomic_mass = PERIODIC_TABLE[element]
                element_mass = atomic_mass * count
                total_mass += element_mass
                breakdown.append(f"  {element}: {count} × {atomic_mass:.3f} = {element_mass:.3f} g/mol")

            result = [f"Molar Mass of {formula}", "=" * 30, "", "Breakdown:"]
            result.extend(breakdown)
            result.append("")
            result.append(f"Total: {self._format_result(total_mass)} g/mol")

            return "\n".join(result)

        except Exception as e:
            return f"Error parsing formula: {str(e)}"

    def moles_grams(self, value: float, molar_mass: float, direction: str = "moles_to_grams") -> str:
        """
        Convert between moles and grams.

        Args:
            value: Amount to convert
            molar_mass: Molar mass in g/mol
            direction: "moles_to_grams" or "grams_to_moles"

        Returns:
            Converted value.
        """
        if direction == "moles_to_grams":
            result = value * molar_mass
            return f"{self._format_result(value)} mol × {molar_mass} g/mol = {self._format_result(result)} g"
        elif direction == "grams_to_moles":
            result = value / molar_mass
            return f"{self._format_result(value)} g ÷ {molar_mass} g/mol = {self._format_result(result)} mol"
        else:
            return "Error: direction must be 'moles_to_grams' or 'grams_to_moles'"

    def scale_formula(self, ingredients: str, scale_factor: float) -> str:
        """
        Scale a formula/recipe by a factor.

        Args:
            ingredients: JSON object of ingredient:amount pairs
            scale_factor: Factor to multiply (e.g., 2.0 for double)

        Returns:
            Scaled formula.
        """
        try:
            if isinstance(ingredients, str):
                ing_dict = json.loads(ingredients)
            else:
                ing_dict = ingredients

            result = [f"Formula Scaling (×{scale_factor})", "=" * 40, "",
                      f"{'Ingredient':<25} {'Original':>12} {'Scaled':>12}", "-" * 50]

            original_total = 0
            scaled_total = 0

            for ingredient, amount in ing_dict.items():
                scaled = amount * scale_factor
                original_total += amount
                scaled_total += scaled
                result.append(f"{ingredient:<25} {amount:>12.3f} {scaled:>12.3f}")

            result.append("-" * 50)
            result.append(f"{'TOTAL':<25} {original_total:>12.3f} {scaled_total:>12.3f}")

            return "\n".join(result)

        except json.JSONDecodeError:
            return 'Error: Invalid JSON format. Use: \'{"ingredient": amount, ...}\''
        except Exception as e:
            return f"Error: {str(e)}"

    def percentage(self, part: float, whole: float, calc_type: str = "of_whole") -> str:
        """
        Calculate percentages.

        Args:
            part: Partial amount or percentage
            whole: Whole amount or reference
            calc_type: "of_whole", "of_percent", or "find_whole"

        Returns:
            Calculated percentage or value.
        """
        if calc_type == "of_whole":
            if whole == 0:
                return "Error: Cannot calculate percentage of zero"
            result = (part / whole) * 100
            return f"{self._format_result(part)} is {self._format_result(result)}% of {self._format_result(whole)}"
        elif calc_type == "of_percent":
            result = (part / 100) * whole
            return f"{self._format_result(part)}% of {self._format_result(whole)} = {self._format_result(result)}"
        elif calc_type == "find_whole":
            if whole == 0:
                return "Error: Cannot find whole from 0%"
            result = (part / whole) * 100
            return f"If {self._format_result(part)} is {self._format_result(whole)}%, then 100% = {self._format_result(result)}"
        else:
            return "Error: calc_type must be 'of_whole', 'of_percent', or 'find_whole'"

    def statistics(self, data: str) -> str:
        """
        Calculate statistics for a dataset.

        Args:
            data: JSON array of numbers, e.g.: "[1.2, 1.5, 1.3]"

        Returns:
            Statistical summary.
        """
        try:
            if isinstance(data, str):
                values = json.loads(data)
            else:
                values = list(data)

            if not values:
                return "Error: Empty dataset"

            values = [float(v) for v in values]
            n = len(values)

            mean = sum(values) / n
            sorted_vals = sorted(values)

            if n % 2 == 0:
                median = (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
            else:
                median = sorted_vals[n//2]

            variance = sum((x - mean) ** 2 for x in values) / n
            std_dev = math.sqrt(variance)

            sample_variance = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0
            sample_std_dev = math.sqrt(sample_variance)

            min_val = min(values)
            max_val = max(values)
            range_val = max_val - min_val

            cv = (std_dev / mean * 100) if mean != 0 else 0

            result = [
                "Statistical Analysis", "=" * 40,
                f"Sample size (n):     {n}", "",
                "Central Tendency:",
                f"  Mean:              {self._format_result(mean)}",
                f"  Median:            {self._format_result(median)}", "",
                "Dispersion:",
                f"  Std Dev (pop):     {self._format_result(std_dev)}",
                f"  Std Dev (sample):  {self._format_result(sample_std_dev)}",
                f"  Variance:          {self._format_result(variance)}",
                f"  CV:                {self._format_result(cv)}%", "",
                "Range:",
                f"  Minimum:           {self._format_result(min_val)}",
                f"  Maximum:           {self._format_result(max_val)}",
                f"  Range:             {self._format_result(range_val)}",
            ]

            if NUMPY_AVAILABLE:
                p25 = float(np.percentile(values, 25))
                p75 = float(np.percentile(values, 75))
                iqr = p75 - p25
                result.extend([
                    "", "Percentiles:",
                    f"  25th (Q1):         {self._format_result(p25)}",
                    f"  75th (Q3):         {self._format_result(p75)}",
                    f"  IQR:               {self._format_result(iqr)}",
                ])

            return "\n".join(result)

        except json.JSONDecodeError:
            return "Error: Invalid JSON format. Use: [value1, value2, ...]"
        except Exception as e:
            return f"Error: {str(e)}"

    def dilution(self, c1: float, v1: float, c2: float, v2: float, solve_for: str) -> str:
        """
        Calculate dilution using C1V1 = C2V2.

        Args:
            c1: Initial concentration
            v1: Initial volume (use 0 if solving)
            c2: Final concentration (use 0 if solving)
            v2: Final volume (use 0 if solving)
            solve_for: "c1", "v1", "c2", or "v2"

        Returns:
            Calculated value.
        """
        try:
            if solve_for == "c1":
                if v1 == 0:
                    return "Error: V1 cannot be zero when solving for C1"
                result = (c2 * v2) / v1
                return f"C1 = (C2 × V2) / V1 = ({c2} × {v2}) / {v1} = {self._format_result(result)}"
            elif solve_for == "v1":
                if c1 == 0:
                    return "Error: C1 cannot be zero when solving for V1"
                result = (c2 * v2) / c1
                return f"V1 = (C2 × V2) / C1 = ({c2} × {v2}) / {c1} = {self._format_result(result)}"
            elif solve_for == "c2":
                if v2 == 0:
                    return "Error: V2 cannot be zero when solving for C2"
                result = (c1 * v1) / v2
                return f"C2 = (C1 × V1) / V2 = ({c1} × {v1}) / {v2} = {self._format_result(result)}"
            elif solve_for == "v2":
                if c2 == 0:
                    return "Error: C2 cannot be zero when solving for V2"
                result = (c1 * v1) / c2
                return f"V2 = (C1 × V1) / C2 = ({c1} × {v1}) / {c2} = {self._format_result(result)}"
            else:
                return "Error: solve_for must be 'c1', 'v1', 'c2', or 'v2'"
        except Exception as e:
            return f"Error: {str(e)}"

    def available_units(self) -> str:
        """List all available units for conversion."""
        result = ["Available Units for Conversion", "=" * 40, ""]
        for category, units in UNIT_CATEGORIES.items():
            result.append(f"{category.upper()}:")
            result.append(f"  {', '.join(units)}")
            result.append("")

        result.extend([
            "TEMPERATURE:", "  C (°C), F (°F), K", "",
            "CONCENTRATION:", "  %, g/L, mol/L (M), ppm, mg/mL",
        ])
        return "\n".join(result)
