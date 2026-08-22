from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv
import json
import os
import subprocess
import sys
import tempfile


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


app = FastAPI(
    title="EnergyPlus HVAC Sizing API",
    version="1.0.0",
)


class Room(BaseModel):
    name: str = Field(min_length=1)
    area_m2: float = Field(gt=0)
    volume_m3: float = Field(gt=0)


class BuildingInput(BaseModel):
    rooms: list[Room] = Field(min_length=1)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "EnergyPlus HVAC Sizing API",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/calculate")
def calculate(building: BuildingInput):
    project_root = Path(__file__).resolve().parent.parent
    model_generator = project_root / "backend" / "model_generator.py"
    parser_script = project_root / "backend" / "parse_eplus.py"
    validator_script = project_root / "backend" / "validate_results.py"

    energyplus_env = os.getenv("ENERGYPLUS_EXECUTABLE")
    weather_env = os.getenv("ENERGYPLUS_WEATHER")

    if energyplus_env:
        energyplus = Path(energyplus_env).resolve()
    else:
        energyplus = next(
            project_root.glob(
                "EnergyPlus-23.2.0-*/energyplus-23.2.0"
            ),
            None,
        )

    if weather_env:
        weather = Path(weather_env).resolve()
    else:
        weather = (
            project_root
            / "EnergyPlus-23.2.0-7636e6b3e9-Linux-Ubuntu22.04-x86_64"
            / "WeatherData"
            / "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
        )

    if (
        not energyplus
        or not energyplus.is_file()
        or not weather
        or not weather.is_file()
    ):
        raise HTTPException(
            status_code=500,
            detail="EnergyPlus executable or weather file not found.",
        )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)

        input_json = temp / "building.json"
        idf_file = temp / "building.idf"
        eplus_dir = temp / "eplus_run"
        csv_file = eplus_dir / "epluszsz.csv"
        result_json = temp / "zone_sizing_results.json"

        input_json.write_text(
            json.dumps(building.model_dump(), indent=2)
        )

        subprocess.run(
            [
                sys.executable,
                str(model_generator),
                "--input",
                str(input_json),
                "--output",
                str(idf_file),
            ],
            check=True,
        )

        eplus_dir.mkdir(parents=True, exist_ok=True)

        try:
            subprocess.run(
                [
                    str(energyplus),
                    "-w",
                    str(weather),
                    "-d",
                    str(eplus_dir),
                    str(idf_file),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=500,
                detail="EnergyPlus simulation failed.",
            ) from exc

        if not csv_file.exists():
            raise HTTPException(
                status_code=500,
                detail="EnergyPlus did not produce zone sizing results.",
            )

        subprocess.run(
            [
                sys.executable,
                str(parser_script),
                "--input-csv",
                str(csv_file),
                "--output-json",
                str(result_json),
            ],
            check=True,
        )

        subprocess.run(
            [
                sys.executable,
                str(validator_script),
                "--input-csv",
                str(csv_file),
                "--input-json",
                str(result_json),
            ],
            check=True,
        )

        return json.loads(result_json.read_text())
