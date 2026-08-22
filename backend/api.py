from fastapi import FastAPI

app = FastAPI(
    title="EnergyPlus HVAC Sizing API",
    version="1.0.0",
)


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
