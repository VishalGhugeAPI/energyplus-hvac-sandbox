import csv
import json
import re
from pathlib import Path
import argparse


# ============================================================
# ENERGYPLUS 23.2 ZONE SIZING RESULT PARSER
# ============================================================

# Input/output paths are supplied through command-line arguments.


# ============================================================
# REQUIRED ENERGYPLUS OUTPUT FIELDS
# ============================================================

REQUIRED_FIELDS = {
    "heating_load": "Des Heat Load [W]",
    "sensible_cooling_load": "Des Sens Cool Load [W]",
    "heating_mass_flow": "Des Heat Mass Flow [kg/s]",
    "cooling_mass_flow": "Des Cool Mass Flow [kg/s]",

    "latent_heating_load": "Des Latent Heat Load [W]",
    "latent_cooling_load": "Des Latent Cool Load [W]",

    "latent_heating_mass_flow":
        "Des Latent Heat Mass Flow [kg/s]",

    "latent_cooling_mass_flow":
        "Des Latent Cool Mass Flow [kg/s]",

    "heating_load_no_doas":
        "Des Heat Load No DOAS [W]",

    "sensible_cooling_load_no_doas":
        "Des Sens Cool Load No DOAS [W]",

    "latent_heating_load_no_doas":
        "Des Latent Heat Load No DOAS [W]",

    "latent_cooling_load_no_doas":
        "Des Latent Cool Load No DOAS [W]",

    "heating_temperature":
        "Heating Zone Temperature [C]",

    "heating_relative_humidity":
        "Heating Zone Relative Humidity [%]",

    "cooling_temperature":
        "Cooling Zone Temperature [C]",

    "cooling_relative_humidity":
        "Cooling Zone Relative Humidity [%]",
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def to_float(value):
    """
    Convert EnergyPlus scientific notation / numeric text
    into a Python float.
    """

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def extract_zone_name(column_name):
    """
    Extract the EnergyPlus zone/space name from a column.

    Example:

    SPACE1-1:CHICAGO_IL_USA ANNUAL HEATING 99%
    DESIGN CONDITIONS DB:Des Heat Load [W]

    becomes:

    SPACE1-1
    """

    if not column_name:
        return None

    # Everything before the first colon is the zone name.
    if ":" not in column_name:
        return None

    zone_name = column_name.split(":", 1)[0].strip()

    if not zone_name:
        return None

    # Ignore Time or other non-zone columns.
    if zone_name.lower() == "time":
        return None

    return zone_name


def extract_environment_name(column_name):
    """
    Extract the EnergyPlus design environment name.

    Example:

    SPACE1-1:CHICAGO_IL_USA ANNUAL HEATING 99%
    DESIGN CONDITIONS DB:Des Heat Load [W]

    returns:

    CHICAGO_IL_USA ANNUAL HEATING 99% DESIGN CONDITIONS DB
    """

    if ":" not in column_name:
        return None

    parts = column_name.split(":")

    if len(parts) < 2:
        return None

    environment = ":".join(parts[1:-1]).strip()

    return environment if environment else None


def extract_output_field(column_name):
    """
    Extract the final EnergyPlus output field.

    Example:

    SPACE1-1:CHICAGO_IL_USA ANNUAL HEATING 99%
    DESIGN CONDITIONS DB:Des Heat Load [W]

    returns:

    Des Heat Load [W]
    """

    if ":" not in column_name:
        return None

    return column_name.rsplit(":", 1)[-1].strip()


# ============================================================
# DISCOVER ZONES AND COLUMNS
# ============================================================

def discover_columns(fieldnames):
    """
    Analyze the EnergyPlus wide-format CSV header.

    Returns:

        {
            "SPACE1-1": {
                "Des Heat Load [W]": {
                    "column": "...",
                    "environment": "..."
                }
            }
        }
    """

    zones = {}

    for column in fieldnames:

        if not column:
            continue

        column = column.strip()

        zone_name = extract_zone_name(column)

        if zone_name is None:
            continue

        output_field = extract_output_field(column)

        if output_field is None:
            continue

        environment = extract_environment_name(column)

        if zone_name not in zones:
            zones[zone_name] = {}

        zones[zone_name][output_field] = {
            "column": column,
            "environment": environment,
        }

    return zones


# ============================================================
# VALIDATE REQUIRED FIELDS
# ============================================================

def validate_required_fields(zone_columns):
    """
    Verify that all required EnergyPlus fields exist
    for every discovered zone.
    """

    errors = []

    for zone_name, columns in zone_columns.items():

        for internal_name, energyplus_field in REQUIRED_FIELDS.items():

            if energyplus_field not in columns:

                errors.append(
                    f"{zone_name}: missing "
                    f"'{energyplus_field}'"
                )

    return errors


# ============================================================
# FIND PEAK / DESIGN VALUE
# ============================================================

def find_peak_value(rows, column_name, mode="max"):
    """
    Find the peak value for a specific EnergyPlus sizing
    column across all sizing timestep rows.

    For loads and mass flows we normally want the maximum.

    mode:
        max -> maximum numeric value
        min -> minimum numeric value
    """

    values = []

    for row in rows:

        value = to_float(
            row.get(column_name)
        )

        if value is not None:
            values.append(value)

    if not values:
        return None

    if mode == "min":
        return min(values)

    return max(values)


# ============================================================
# PARSE ONE ZONE
# ============================================================

def parse_zone(zone_name, columns, rows):
    """
    Convert one EnergyPlus zone into structured JSON.
    """

    def value(field_key):
        energyplus_field = REQUIRED_FIELDS[field_key]

        column_info = columns.get(energyplus_field)

        if column_info is None:
            return None

        return find_peak_value(
            rows,
            column_info["column"]
        )

    # --------------------------------------------------------
    # Determine design environments
    # --------------------------------------------------------

    heating_environment = None
    cooling_environment = None

    heating_field = REQUIRED_FIELDS["heating_load"]
    cooling_field = REQUIRED_FIELDS["sensible_cooling_load"]

    if heating_field in columns:
        heating_environment = columns[
            heating_field
        ].get("environment")

    if cooling_field in columns:
        cooling_environment = columns[
            cooling_field
        ].get("environment")

    # --------------------------------------------------------
    # Build structured result
    # --------------------------------------------------------

    result = {

        "zone_name": zone_name,

        "design_conditions": {

            "heating": heating_environment,

            "cooling": cooling_environment,
        },

        "heating": {

            "design_load_w":
                value("heating_load"),

            "latent_load_w":
                value("latent_heating_load"),

            "mass_flow_kg_s":
                value("heating_mass_flow"),

            "latent_mass_flow_kg_s":
                value("latent_heating_mass_flow"),

            "temperature_c":
                value("heating_temperature"),

            "relative_humidity_percent":
                value("heating_relative_humidity"),
        },

        "cooling": {

            "sensible_load_w":
                value("sensible_cooling_load"),

            "latent_load_w":
                value("latent_cooling_load"),

            "mass_flow_kg_s":
                value("cooling_mass_flow"),

            "latent_mass_flow_kg_s":
                value("latent_cooling_mass_flow"),

            "temperature_c":
                value("cooling_temperature"),

            "relative_humidity_percent":
                value("cooling_relative_humidity"),
        },

        "no_doas": {

            "heating_load_w":
                value("heating_load_no_doas"),

            "sensible_cooling_load_w":
                value("sensible_cooling_load_no_doas"),

            "latent_heating_load_w":
                value("latent_heating_load_no_doas"),

            "latent_cooling_load_w":
                value("latent_cooling_load_no_doas"),
        },
    }

    return result


# ============================================================
# MAIN CSV PARSER
# ============================================================

def parse_epluszsz(csv_file):
    """
    Parse the actual EnergyPlus epluszsz.csv file.
    """

    with open(
        csv_file,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                "EnergyPlus CSV does not contain a header."
            )

        # Remove whitespace from header names.
        reader.fieldnames = [
            field.strip()
            if field
            else field
            for field in reader.fieldnames
        ]

        fieldnames = reader.fieldnames

        # Read all timestep rows.
        rows = list(reader)

    # --------------------------------------------------------
    # Discover EnergyPlus zones
    # --------------------------------------------------------

    zone_columns = discover_columns(
        fieldnames
    )

    if not zone_columns:

        raise ValueError(
            "No EnergyPlus zones were discovered "
            "from epluszsz.csv."
        )

    # --------------------------------------------------------
    # Validate required fields
    # --------------------------------------------------------

    validation_errors = validate_required_fields(
        zone_columns
    )

    if validation_errors:

        error_message = (
            "Missing required EnergyPlus fields:\n\n"
            + "\n".join(
                f"  - {error}"
                for error in validation_errors
            )
        )

        raise ValueError(error_message)

    # --------------------------------------------------------
    # Parse every zone
    # --------------------------------------------------------

    parsed_zones = []

    for zone_name in sorted(zone_columns.keys()):

        zone_result = parse_zone(
            zone_name,
            zone_columns[zone_name],
            rows
        )

        parsed_zones.append(
            zone_result
        )

    # --------------------------------------------------------
    # Build final result
    # --------------------------------------------------------

    result = {

        "engine": "EnergyPlus",

        "version": "23.2.0",

        "source": "epluszsz.csv",

        "zone_count": len(parsed_zones),

        "timestep_row_count": len(rows),

        "zones": parsed_zones,
    }

    return result


# ============================================================
# WRITE JSON
# ============================================================

def save_json(data, output_file):

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


# ============================================================
# CONSOLE SUMMARY
# ============================================================

def print_summary(data):

    print()
    print("=" * 70)
    print("ENERGYPLUS 23.2 ZONE SIZING RESULTS")
    print("=" * 70)

    print(
        f"Engine             : {data['engine']}"
    )

    print(
        f"Version            : {data['version']}"
    )

    print(
        f"Zones              : {data['zone_count']}"
    )

    print(
        f"Sizing rows        : "
        f"{data['timestep_row_count']}"
    )

    print("-" * 70)

    for zone in data["zones"]:

        print(
            f"\nZONE: {zone['zone_name']}"
        )

        print(
            "  Heating Load       : "
            f"{zone['heating']['design_load_w']:.3f} W"
            if zone["heating"]["design_load_w"] is not None
            else "  Heating Load       : N/A"
        )

        print(
            "  Sensible Cooling   : "
            f"{zone['cooling']['sensible_load_w']:.3f} W"
            if zone["cooling"]["sensible_load_w"] is not None
            else "  Sensible Cooling   : N/A"
        )

        print(
            "  Latent Cooling     : "
            f"{zone['cooling']['latent_load_w']:.3f} W"
            if zone["cooling"]["latent_load_w"] is not None
            else "  Latent Cooling     : N/A"
        )

        print(
            "  Heating Airflow    : "
            f"{zone['heating']['mass_flow_kg_s']:.6f} kg/s"
            if zone["heating"]["mass_flow_kg_s"] is not None
            else "  Heating Airflow    : N/A"
        )

        print(
            "  Cooling Airflow    : "
            f"{zone['cooling']['mass_flow_kg_s']:.6f} kg/s"
            if zone["cooling"]["mass_flow_kg_s"] is not None
            else "  Cooling Airflow    : N/A"
        )

        print(
            "  Heating Temp       : "
            f"{zone['heating']['temperature_c']:.3f} °C"
            if zone["heating"]["temperature_c"] is not None
            else "  Heating Temp       : N/A"
        )

        print(
            "  Heating RH         : "
            f"{zone['heating']['relative_humidity_percent']:.3f} %"
            if zone["heating"]["relative_humidity_percent"] is not None
            else "  Heating RH         : N/A"
        )

        print(
            "  Cooling Temp       : "
            f"{zone['cooling']['temperature_c']:.3f} °C"
            if zone["cooling"]["temperature_c"] is not None
            else "  Cooling Temp       : N/A"
        )

        print(
            "  Cooling RH         : "
            f"{zone['cooling']['relative_humidity_percent']:.3f} %"
            if zone["cooling"]["relative_humidity_percent"] is not None
            else "  Cooling RH         : N/A"
        )

        print(
            "  No-DOAS Heat       : "
            f"{zone['no_doas']['heating_load_w']:.3f} W"
            if zone["no_doas"]["heating_load_w"] is not None
            else "  No-DOAS Heat       : N/A"
        )

        print(
            "  No-DOAS Sens Cool  : "
            f"{zone['no_doas']['sensible_cooling_load_w']:.3f} W"
            if zone["no_doas"]["sensible_cooling_load_w"] is not None
            else "  No-DOAS Sens Cool  : N/A"
        )

        print(
            "  No-DOAS Latent Heat: "
            f"{zone['no_doas']['latent_heating_load_w']:.3f} W"
            if zone["no_doas"]["latent_heating_load_w"] is not None
            else "  No-DOAS Latent Heat: N/A"
        )

        print(
            "  No-DOAS Latent Cool: "
            f"{zone['no_doas']['latent_cooling_load_w']:.3f} W"
            if zone["no_doas"]["latent_cooling_load_w"] is not None
            else "  No-DOAS Latent Cool: N/A"
        )

        print(
            "  Heating Design Day : "
            f"{zone['design_conditions']['heating']}"
        )

        print(
            "  Cooling Design Day : "
            f"{zone['design_conditions']['cooling']}"
        )

    print()
    print("=" * 70)


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    INPUT_FILE = Path(args.input_csv)
    OUTPUT_FILE = Path(args.output_json)

    print(
        "Starting EnergyPlus 23.2 result parser..."
    )

    print(
        f"Input file : {INPUT_FILE}"
    )

    print(
        f"Output file: {OUTPUT_FILE}"
    )

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"\nEnergyPlus output file does not exist:\n"
            f"{INPUT_FILE}"
        )

    try:

        data = parse_epluszsz(
            INPUT_FILE
        )

        save_json(
            data,
            OUTPUT_FILE
        )

        print_summary(
            data
        )

        print(
            f"\nJSON successfully created:"
        )

        print(
            OUTPUT_FILE
        )

    except Exception as error:

        print()
        print("=" * 70)
        print("PARSER ERROR")
        print("=" * 70)
        print(str(error))
        print("=" * 70)

        raise


if __name__ == "__main__":
    main()