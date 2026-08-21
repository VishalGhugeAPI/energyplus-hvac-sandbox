import json
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    INPUT_JSON = Path(args.input)
    OUTPUT_IDF = Path(args.output)

    print("=" * 70)
    print("HVAC SANDBOX - ENERGYPLUS 23.2 MODEL GENERATOR")
    print("=" * 70)

    print(f"\nInput JSON : {INPUT_JSON}")
    print(f"Output IDF : {OUTPUT_IDF}\n")

    with open(INPUT_JSON, "r") as f:
        data = json.load(f)

    rooms = data.get("rooms", [])

    if not rooms:
        raise ValueError("No rooms found in building.json")

    OUTPUT_IDF.parent.mkdir(parents=True, exist_ok=True)

    idf = []

    # ============================================================
    # VERSION
    # ============================================================

    idf.append("""Version,
    23.2;""")

    # ============================================================
    # SIMULATION CONTROL
    # ============================================================

    idf.append("""SimulationControl,
    Yes,
    Yes,
    No,
    Yes,
    Yes;""")

    # ============================================================
    # BUILDING
    # ============================================================

    idf.append("""Building,
    HVAC Sandbox Building,
    0.0,
    Suburbs,
    0.04,
    0.4,
    FullExterior,
    25,
    1;""")

    # ============================================================
    # LOCATION
    # ============================================================

    idf.append("""Site:Location,
    Chicago_IL_USA,
    41.78,
    -87.75,
    -6.0,
    190.0;""")

    # ============================================================
    # TIMESTEP
    # ============================================================

    idf.append("""Timestep,
    4;""")

    # ============================================================
    # RUN PERIOD
    # ============================================================

    idf.append("""RunPeriod,
    Annual Simulation,
    1,
    1,
    ,
    12,
    31,
    ,
    Monday,
    Yes,
    Yes,
    No,
    Yes,
    Yes;""")

    # ============================================================
    # GEOMETRY RULES
    # ============================================================

    idf.append("""GlobalGeometryRules,
    UpperLeftCorner,
    CounterClockwise,
    World;""")

    # ============================================================
    # SCHEDULE TYPE LIMITS
    # ============================================================

    idf.append("""ScheduleTypeLimits,
    Fraction,
    0.0,
    1.0,
    CONTINUOUS;""")

    idf.append("""ScheduleTypeLimits,
    Temperature,
    -60.0,
    100.0,
    CONTINUOUS;""")

    idf.append("""ScheduleTypeLimits,
    ActivityLevel,
    0.0,
    1000.0,
    CONTINUOUS;""")

    idf.append("""ScheduleTypeLimits,
    Control Type,
    0.0,
    4.0,
    DISCRETE;""")

    # ============================================================
    # SCHEDULES
    # ============================================================

    idf.append("""Schedule:Constant,
    Always On,
    Fraction,
    1.0;""")

    idf.append("""Schedule:Constant,
    Occupancy Schedule,
    Fraction,
    1.0;""")

    idf.append("""Schedule:Constant,
    Lighting Schedule,
    Fraction,
    1.0;""")

    idf.append("""Schedule:Constant,
    Equipment Schedule,
    Fraction,
    1.0;""")

    idf.append("""Schedule:Constant,
    Activity Schedule,
    ActivityLevel,
    120.0;""")

    # ============================================================
    # MATERIALS
    # ============================================================

    idf.append("""Material,
    Exterior Wall Material,
    MediumSmooth,
    0.200,
    0.500,
    800.0,
    900.0,
    0.90,
    0.70,
    0.70;""")

    idf.append("""Material,
    Floor Material,
    MediumSmooth,
    0.150,
    0.500,
    800.0,
    900.0,
    0.90,
    0.70,
    0.70;""")

    idf.append("""Material,
    Roof Material,
    MediumSmooth,
    0.200,
    0.500,
    800.0,
    900.0,
    0.90,
    0.70,
    0.70;""")

    # ============================================================
    # CONSTRUCTIONS
    # ============================================================

    idf.append("""Construction,
    Exterior Wall Construction,
    Exterior Wall Material;""")

    idf.append("""Construction,
    Floor Construction,
    Floor Material;""")

    idf.append("""Construction,
    Roof Construction,
    Roof Material;""")

    # ============================================================
    # GROUND TEMPERATURES
    # ============================================================

    idf.append("""Site:GroundTemperature:BuildingSurface,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0,
    18.0;""")

    # ============================================================
    # DESIGN DAY
    # ============================================================

    idf.append("""SizingPeriod:DesignDay,
    Chicago Summer Design Day,
    7,
    21,
    SummerDesignDay,
    31.0,
    10.0,
    DefaultMultipliers,
    ,
    WetBulb,
    21.0,
    ,
    ,
    ,
    ,
    99000.0,
    3.0,
    180.0,
    No,
    No,
    No,
    ASHRAEClearSky,
    ,
    ,
    ,
    ,
    1.0;""")

    # ============================================================
    # WINTER DESIGN DAY
    # ============================================================

    idf.append("""SizingPeriod:DesignDay,
    Chicago Winter Design Day,
    1,
    15,
    WinterDesignDay,
    -17.0,
    0.0,
    DefaultMultipliers,
    ,
    WetBulb,
    -17.0,
    ,
    ,
    ,
    ,
    99000.0,
    4.5,
    0.0,
    No,
    No,
    No,
    ASHRAEClearSky,
    ,
    ,
    ,
    ,
    0.0;""")

    # ============================================================
    # SIZING PARAMETERS
    # ============================================================

    idf.append("""Sizing:Parameters,
    1.15,
    1.15,
    4;""")

    # ============================================================
    # ZONES
    # ============================================================

    for room in rooms:
        name = room["name"]
        area = float(room.get("area", 20.0))
        volume = float(room.get("volume", area * 3.0))

        # Calculate simple rectangular dimensions
        width = area ** 0.5
        depth = area / width
        height = volume / area

        idf.append(f"""Zone,
    {name},
    0.0,
    0.0,
    0.0,
    0.0,
    1,
    1,
    {area:.3f},
    {volume:.3f};""")

        # Store dimensions for surfaces
        room["_width"] = width
        room["_depth"] = depth
        room["_height"] = height

    # ============================================================
    # SURFACES
    # ============================================================

    for room in rooms:
        name = room["name"]

        w = room["_width"]
        d = room["_depth"]
        h = room["_height"]

        x0 = float(room.get("x", 0.0))
        y0 = float(room.get("y", 0.0))

        x1 = x0 + w
        y1 = y0 + d

        # --------------------------------------------------------
        # FLOOR
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} Floor,
    Floor,
    Floor Construction,
    {name},
    ,
    Ground,
    ,
    NoSun,
    NoWind,
    1.0,
    4,
    {x0:.3f},
    {y1:.3f},
    0.000,
    {x1:.3f},
    {y1:.3f},
    0.000,
    {x1:.3f},
    {y0:.3f},
    0.000,
    {x0:.3f},
    {y0:.3f},
    0.000;""")

        # --------------------------------------------------------
        # ROOF
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} Roof,
    Roof,
    Roof Construction,
    {name},
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    1.0,
    4,
    {x0:.3f},
    {y0:.3f},
    {h:.3f},
    {x1:.3f},
    {y0:.3f},
    {h:.3f},
    {x1:.3f},
    {y1:.3f},
    {h:.3f},
    {x0:.3f},
    {y1:.3f},
    {h:.3f};""")

        # --------------------------------------------------------
        # SOUTH WALL
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} South Wall,
    Wall,
    Exterior Wall Construction,
    {name},
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    0.5,
    4,
    {x0:.3f},
    {y0:.3f},
    {h:.3f},
    {x1:.3f},
    {y0:.3f},
    {h:.3f},
    {x1:.3f},
    {y0:.3f},
    0.000,
    {x0:.3f},
    {y0:.3f},
    0.000;""")

        # --------------------------------------------------------
        # EAST WALL
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} East Wall,
    Wall,
    Exterior Wall Construction,
    {name},
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    0.5,
    4,
    {x1:.3f},
    {y0:.3f},
    {h:.3f},
    {x1:.3f},
    {y1:.3f},
    {h:.3f},
    {x1:.3f},
    {y1:.3f},
    0.000,
    {x1:.3f},
    {y0:.3f},
    0.000;""")

        # --------------------------------------------------------
        # NORTH WALL
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} North Wall,
    Wall,
    Exterior Wall Construction,
    {name},
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    0.5,
    4,
    {x1:.3f},
    {y1:.3f},
    {h:.3f},
    {x0:.3f},
    {y1:.3f},
    {h:.3f},
    {x0:.3f},
    {y1:.3f},
    0.000,
    {x1:.3f},
    {y1:.3f},
    0.000;""")

        # --------------------------------------------------------
        # WEST WALL
        # --------------------------------------------------------

        idf.append(f"""BuildingSurface:Detailed,
    {name} West Wall,
    Wall,
    Exterior Wall Construction,
    {name},
    ,
    Outdoors,
    ,
    SunExposed,
    WindExposed,
    0.5,
    4,
    {x0:.3f},
    {y1:.3f},
    {h:.3f},
    {x0:.3f},
    {y0:.3f},
    {h:.3f},
    {x0:.3f},
    {y0:.3f},
    0.000,
    {x0:.3f},
    {y1:.3f},
    0.000;""")

    # ============================================================
    # PEOPLE
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""People,
    {name} People,
    {name},
    Occupancy Schedule,
    People,
    1.000,
    ,
    ,
    0.30,
    ,
    Activity Schedule;""")

    # ============================================================
    # LIGHTING
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""Lights,
    {name} Lighting,
    {name},
    Lighting Schedule,
    Watts/Area,
    ,
    10.000,
    ,
    0.0,
    0.7,
    0.2,
    0.0,
    General,
    No;""")

    # ============================================================
    # ELECTRIC EQUIPMENT
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""ElectricEquipment,
    {name} Equipment,
    {name},
    Equipment Schedule,
    Watts/Area,
    ,
    8.000,
    ,
    0.0,
    0.3,
    0.0;""")

    # ============================================================
    # INFILTRATION
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""ZoneInfiltration:DesignFlowRate,
    {name} Infiltration,
    {name},
    Always On,
    AirChanges/Hour,
    ,
    ,
    ,
    0.5,
    1.0,
    0.0,
    0.0;""")

    # ============================================================
    # ZONE HVAC EQUIPMENT LIST + IDEAL LOADS
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""ZoneHVAC:EquipmentList,
    {name} Equipment List,
    SequentialLoad,
    ZoneHVAC:IdealLoadsAirSystem,
    {name} Ideal Loads,
    1,
    1;""")

        idf.append(f"""ZoneHVAC:IdealLoadsAirSystem,
    {name} Ideal Loads,
    ,
    {name} Zone Supply Inlet Node,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ,
    ;""")

    # ============================================================
    # ZONE HVAC EQUIPMENT CONNECTIONS
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""ZoneHVAC:EquipmentConnections,
    {name},
    {name} Equipment List,
    {name} Zone Supply Inlet Node,
    ,
    {name} Zone Air Node,
    {name} Zone Return Node;""")

        # ============================================================
    # THERMOSTAT
    # ============================================================

    idf.append("""Schedule:Constant,
    Thermostat Control Type,
    Control Type,
    4;""")

    idf.append("""Schedule:Constant,
    Heating Setpoint,
    Temperature,
    20.0;""")

    idf.append("""Schedule:Constant,
    Cooling Setpoint,
    Temperature,
    24.0;""")

    for room in rooms:
        name = room["name"]

        idf.append(f"""ThermostatSetpoint:DualSetpoint,
    {name} Dual Setpoint,
    Heating Setpoint,
    Cooling Setpoint;""")

        idf.append(f"""ZoneControl:Thermostat,
    {name} Thermostat,
    {name},
    Thermostat Control Type,
    ThermostatSetpoint:DualSetpoint,
    {name} Dual Setpoint;""")

        # ============================================================
    # ZONE SIZING
    # ============================================================

    for room in rooms:
        name = room["name"]

        idf.append(f"""Sizing:Zone,
    {name},
    SupplyAirTemperature,
    13.0,
    ,
    SupplyAirTemperature,
    32.0,
    ,
    0.009,
    0.004,
    ,
    1.0,
    1.0,
    DesignDay,
    ,
    0.000762,
    0.0,
    0.2,
    DesignDay,
    ,
    0.002032,
    0.0,
    0.3,
    ,
    No,
    NeutralSupplyAir,
    ,
    ,
    Sensible Load Only No Latent Load,
    ;""")

    # ============================================================
    # OUTPUT
    # ============================================================

    idf.append("""Output:SQLite,
    SimpleAndTabular;""")

    idf.append("""OutputControl:Table:Style,
    CommaAndHTML;""")

    idf.append("""Output:Table:SummaryReports,
    AllSummary;""")

    # ============================================================
    # WRITE IDF
    # ============================================================

    OUTPUT_IDF.write_text("\n\n".join(idf) + "\n")

    # ============================================================
    # CLEAN DISPLAY
    # ============================================================

    print(f"Rooms generated: {len(rooms)}")

    for room in rooms:
        name = room["name"]
        area = float(room.get("area", 20.0))
        volume = float(room.get("volume", area * 3.0))

        print(f"  {name}: {area:.2f} m² / {volume:.2f} m³")

    print("\nModel contains:")
    print("  ✓ Site:Location")
    print("  ✓ Building")
    print("  ✓ Thermal zones")
    print("  ✓ Floors")
    print("  ✓ Roofs")
    print("  ✓ Exterior walls")
    print("  ✓ People")
    print("  ✓ Lighting")
    print("  ✓ Equipment")
    print("  ✓ Infiltration")
    print("  ✓ Thermostats")
    print("  ✓ Design day")
    print("  ✓ Zone sizing")
    print("  ✓ Zone HVAC Equipment Connections")
    print("  ✓ Ideal Loads HVAC")
    print("  ✓ Weather-file RunPeriod")
    print("  ✓ EnergyPlus 23.2 field ordering")

    print("\n" + "=" * 70)
    print("MODEL GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()