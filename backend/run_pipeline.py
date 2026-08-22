import argparse
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def run_command(command, description):
    print()
    print("=" * 70)
    print(description)
    print("=" * 70)
    print("Command:", " ".join(str(x) for x in command))
    print()

    result = subprocess.run(command)

    if result.returncode != 0:
        print()
        print(f"FAILED: {description}")
        print(f"Exit code: {result.returncode}")
        sys.exit(result.returncode)

    print()
    print(f"PASS: {description}")


def main():
    parser = argparse.ArgumentParser(
        description="Portable EnergyPlus HVAC sizing pipeline"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Building JSON input file",
    )

    parser.add_argument(
        "--weather",
        required=True,
        help="EnergyPlus EPW weather file",
    )

    parser.add_argument(
        "--energyplus",
        required=True,
        help="Path to EnergyPlus executable",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Pipeline output directory",
    )

    args = parser.parse_args()

    input_json = Path(args.input).resolve()
    weather_file = Path(args.weather).resolve()
    energyplus = Path(args.energyplus).resolve()
    output_dir = Path(args.output).resolve()

    backend_dir = Path(__file__).resolve().parent

    idf_file = output_dir / "building.idf"
    energyplus_dir = output_dir / "eplus_run"
    csv_file = energyplus_dir / "epluszsz.csv"
    json_file = output_dir / "zone_sizing_results.json"

    model_generator = BACKEND_DIR / "model_generator.py"
    parser_script = BACKEND_DIR / "parse_eplus.py"
    validator_script = BACKEND_DIR / "validate_results.py"

    print("=" * 70)
    print("PORTABLE ENERGYPLUS HVAC SIZING PIPELINE")
    print("=" * 70)

    print()
    print("Input JSON :", input_json)
    print("Weather    :", weather_file)
    print("EnergyPlus :", energyplus)
    print("Output     :", output_dir)

    # ------------------------------------------------------------
    # INPUT VALIDATION
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("1. INPUT VALIDATION")
    print("=" * 70)

    required_files = [
        (input_json, "Building JSON"),
        (weather_file, "Weather file"),
        (energyplus, "EnergyPlus executable"),
        (model_generator, "Model generator"),
        (parser_script, "Result parser"),
        (validator_script, "Result validator"),
    ]

    for path, label in required_files:
        if not path.exists():
            print(f"FAILED: {label} does not exist:")
            print(path)
            sys.exit(1)

        if not path.is_file():
            print(f"FAILED: {label} is not a file:")
            print(path)
            sys.exit(1)

        print(f"PASS: {label}")
        print(f"      {path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    # 2. MODEL GENERATION
    # ------------------------------------------------------------

    run_command(
        [
            sys.executable,
            str(model_generator),
            "--input",
            str(input_json),
            "--output",
            str(idf_file),
        ],
        "2. MODEL GENERATION",
    )

    if not idf_file.exists() or idf_file.stat().st_size == 0:
        print("FAILED: IDF was not created.")
        sys.exit(1)

    print("IDF :", idf_file)
    print("Size:", idf_file.stat().st_size, "bytes")

    # ------------------------------------------------------------
    # 3. ENERGYPLUS RUN
    # ------------------------------------------------------------

    energyplus_dir.mkdir(parents=True, exist_ok=True)

    run_command(
        [
            str(energyplus),
            "-w",
            str(weather_file),
            "-d",
            str(energyplus_dir),
            str(idf_file),
        ],
        "3. ENERGYPLUS SIMULATION",
    )

    # ------------------------------------------------------------
    # 4. ZONE SIZING OUTPUT
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("4. ZONE SIZING OUTPUT")
    print("=" * 70)

    if not csv_file.exists():
        print("FAILED: EnergyPlus zone sizing CSV was not created.")
        print("Expected:", csv_file)
        sys.exit(1)

    if csv_file.stat().st_size == 0:
        print("FAILED: Zone sizing CSV is empty.")
        sys.exit(1)

    print("PASS: Zone sizing CSV")
    print("File :", csv_file)
    print("Size :", csv_file.stat().st_size, "bytes")

    # ------------------------------------------------------------
    # 5. PARSE ENERGYPLUS RESULTS
    # ------------------------------------------------------------

    run_command(
        [
            sys.executable,
            str(parser_script),
            "--input-csv",
            str(csv_file),
            "--output-json",
            str(json_file),
        ],
        "5. PARSE ENERGYPLUS RESULTS",
    )

    if not json_file.exists() or json_file.stat().st_size == 0:
        print("FAILED: Parsed JSON was not created.")
        sys.exit(1)

    # ------------------------------------------------------------
    # 6. VALIDATE RESULTS
    # ------------------------------------------------------------

    run_command(
        [
            sys.executable,
            str(validator_script),
            "--input-csv",
            str(csv_file),
            "--input-json",
            str(json_file),
        ],
        "6. VALIDATE CSV → JSON RESULTS",
    )

    # ------------------------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------------------------

    print()
    print("=" * 70)
    print("PIPELINE RESULT: PASS")
    print("=" * 70)

    print()
    print("Generated files:")
    print("  IDF    :", idf_file)
    print("  CSV    :", csv_file)
    print("  JSON   :", json_file)

    print()
    print("EnergyPlus HVAC sizing pipeline completed successfully.")


if __name__ == "__main__":
    main()