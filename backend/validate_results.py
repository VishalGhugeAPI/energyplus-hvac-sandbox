import csv
import json
from pathlib import Path
import argparse


# ============================================================
# CONFIGURATION
# ============================================================

# Input paths are supplied through command-line arguments.
CSV_FILE = None
JSON_FILE = None


# ============================================================
# ENERGYPLUS FIELD MAPPING
# ============================================================

FIELDS = {
    "heating_load_w": "Des Heat Load [W]",
    "sensible_cooling_load_w": "Des Sens Cool Load [W]",
    "heating_mass_flow_kg_s": "Des Heat Mass Flow [kg/s]",
    "cooling_mass_flow_kg_s": "Des Cool Mass Flow [kg/s]",

    "latent_heating_load_w": "Des Latent Heat Load [W]",
    "latent_cooling_load_w": "Des Latent Cool Load [W]",

    "latent_heating_mass_flow_kg_s":
        "Des Latent Heat Mass Flow [kg/s]",

    "latent_cooling_mass_flow_kg_s":
        "Des Latent Cool Mass Flow [kg/s]",

    "heating_load_no_doas_w":
        "Des Heat Load No DOAS [W]",

    "sensible_cooling_load_no_doas_w":
        "Des Sens Cool Load No DOAS [W]",

    "latent_heating_load_no_doas_w":
        "Des Latent Heat Load No DOAS [W]",

    "latent_cooling_load_no_doas_w":
        "Des Latent Cool Load No DOAS [W]",

    "heating_temperature_c":
        "Heating Zone Temperature [C]",

    "heating_rh_percent":
        "Heating Zone Relative Humidity [%]",

    "cooling_temperature_c":
        "Cooling Zone Temperature [C]",

    "cooling_rh_percent":
        "Cooling Zone Relative Humidity [%]",
}


# ============================================================
# HELPERS
# ============================================================

def to_float(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def get_zone_name(column):
    """
    EnergyPlus column format:

    SPACE1-1:DESIGN ENVIRONMENT:FIELD

    Return:

    SPACE1-1
    """

    if ":" not in column:
        return None

    zone = column.split(":", 1)[0].strip()

    if not zone or zone.lower() == "time":
        return None

    return zone


def get_field_name(column):
    """
    Return the final EnergyPlus field name.
    """

    if ":" not in column:
        return None

    return column.rsplit(":", 1)[-1].strip()


def find_column(fieldnames, zone_name, field_name):
    """
    Find the actual EnergyPlus CSV column for a zone/field.
    """

    for column in fieldnames:

        if get_zone_name(column) != zone_name:
            continue

        if get_field_name(column) != field_name:
            continue

        return column

    return None


def find_peak(rows, column):
    """
    Get maximum numeric value from the CSV column.
    """

    values = []

    for row in rows:

        value = to_float(row.get(column))

        if value is not None:
            values.append(value)

    if not values:
        return None

    return max(values)


# ============================================================
# LOAD RAW ENERGYPLUS CSV
# ============================================================

def load_csv():

    with open(
        CSV_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        fieldnames = reader.fieldnames

        rows = list(reader)

    return fieldnames, rows


# ============================================================
# EXTRACT RAW CSV RESULTS
# ============================================================

def extract_csv_results(fieldnames, rows):

    zones = {}

    for column in fieldnames:

        zone_name = get_zone_name(column)

        if zone_name is None:
            continue

        if zone_name not in zones:
            zones[zone_name] = {}

    for zone_name in zones:

        for internal_name, energyplus_field in FIELDS.items():

            column = find_column(
                fieldnames,
                zone_name,
                energyplus_field
            )

            if column is None:

                zones[zone_name][internal_name] = None

            else:

                zones[zone_name][internal_name] = find_peak(
                    rows,
                    column
                )

    return zones


# ============================================================
# LOAD PARSER JSON
# ============================================================

def load_json():

    with open(
        JSON_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# EXTRACT JSON RESULTS
# ============================================================

def extract_json_results(data):

    results = {}

    for zone in data["zones"]:

        zone_name = zone["zone_name"]

        results[zone_name] = {

            "heating_load_w":
                zone["heating"]["design_load_w"],

            "sensible_cooling_load_w":
                zone["cooling"]["sensible_load_w"],

            "heating_mass_flow_kg_s":
                zone["heating"]["mass_flow_kg_s"],

            "cooling_mass_flow_kg_s":
                zone["cooling"]["mass_flow_kg_s"],

            "latent_heating_load_w":
                zone["heating"]["latent_load_w"],

            "latent_cooling_load_w":
                zone["cooling"]["latent_load_w"],

            "latent_heating_mass_flow_kg_s":
                zone["heating"]["latent_mass_flow_kg_s"],

            "latent_cooling_mass_flow_kg_s":
                zone["cooling"]["latent_mass_flow_kg_s"],

            "heating_load_no_doas_w":
                zone["no_doas"]["heating_load_w"],

            "sensible_cooling_load_no_doas_w":
                zone["no_doas"]["sensible_cooling_load_w"],

            "latent_heating_load_no_doas_w":
                zone["no_doas"]["latent_heating_load_w"],

            "latent_cooling_load_no_doas_w":
                zone["no_doas"]["latent_cooling_load_w"],

            "heating_temperature_c":
                zone["heating"]["temperature_c"],

            "heating_rh_percent":
                zone["heating"]["relative_humidity_percent"],

            "cooling_temperature_c":
                zone["cooling"]["temperature_c"],

            "cooling_rh_percent":
                zone["cooling"]["relative_humidity_percent"],
        }

    return results


# ============================================================
# COMPARE VALUES
# ============================================================

def values_match(csv_value, json_value, tolerance=0.000001):

    if csv_value is None and json_value is None:
        return True

    if csv_value is None or json_value is None:
        return False

    return abs(csv_value - json_value) <= tolerance


# ============================================================
# VALIDATION
# ============================================================

def validate():

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--input-json", required=True)
    args = parser.parse_args()

    global CSV_FILE
    global JSON_FILE

    CSV_FILE = Path(args.input_csv)
    JSON_FILE = Path(args.input_json)

    print()
    print("=" * 75)
    print("ENERGYPLUS 23.2 CSV → JSON VALIDATION")
    print("=" * 75)

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"CSV file not found:\n{CSV_FILE}"
        )

    if not JSON_FILE.exists():
        raise FileNotFoundError(
            f"JSON file not found:\n{JSON_FILE}"
        )

    print(f"CSV : {CSV_FILE}")
    print(f"JSON: {JSON_FILE}")
    print()

    # --------------------------------------------------------
    # Load both sources
    # --------------------------------------------------------

    fieldnames, rows = load_csv()

    json_data = load_json()

    csv_results = extract_csv_results(
        fieldnames,
        rows
    )

    json_results = extract_json_results(
        json_data
    )

    # --------------------------------------------------------
    # Compare zone counts
    # --------------------------------------------------------

    csv_zones = set(csv_results.keys())
    json_zones = set(json_results.keys())

    print(
        f"CSV zones : {len(csv_zones)}"
    )

    print(
        f"JSON zones: {len(json_zones)}"
    )

    print()

    if csv_zones != json_zones:

        print("❌ ZONE MISMATCH")

        print(
            "Only in CSV :",
            sorted(csv_zones - json_zones)
        )

        print(
            "Only in JSON:",
            sorted(json_zones - csv_zones)
        )

        return False

    # --------------------------------------------------------
    # Compare every field
    # --------------------------------------------------------

    total_checks = 0
    passed_checks = 0
    failed_checks = []

    for zone_name in sorted(csv_zones):

        print("-" * 75)
        print(f"ZONE: {zone_name}")
        print("-" * 75)

        for field_name in FIELDS:

            total_checks += 1

            csv_value = csv_results[
                zone_name
            ][field_name]

            json_value = json_results[
                zone_name
            ][field_name]

            if values_match(
                csv_value,
                json_value
            ):

                passed_checks += 1

                print(
                    f"  ✓ {field_name}"
                )

            else:

                failed_checks.append(
                    (
                        zone_name,
                        field_name,
                        csv_value,
                        json_value
                    )
                )

                print(
                    f"  ❌ {field_name}"
                )

                print(
                    f"       CSV : {csv_value}"
                )

                print(
                    f"       JSON: {json_value}"
                )

    # --------------------------------------------------------
    # Final result
    # --------------------------------------------------------

    print()
    print("=" * 75)
    print("VALIDATION SUMMARY")
    print("=" * 75)

    print(
        f"Total checks : {total_checks}"
    )

    print(
        f"Passed       : {passed_checks}"
    )

    print(
        f"Failed       : {len(failed_checks)}"
    )

    print()

    if not failed_checks:

        print(
            "✅ VALIDATION PASSED"
        )

        print(
            "The JSON results match the "
            "EnergyPlus CSV results."
        )

        return True

    print(
        "❌ VALIDATION FAILED"
    )

    print(
        "The parser output does not completely "
        "match the EnergyPlus CSV."
    )

    return False


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    success = validate()

    if not success:
        raise SystemExit(1)