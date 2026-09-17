import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# Load SHIP_HOST from .env file if present
for env_path in [pathlib.Path.cwd() / ".env", pathlib.Path(__file__).parent.parent / ".env"]:
    if env_path.is_file():
        with open(env_path) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        break

# Spacecraft IP Address
HOST = os.getenv("HOST")

# Known Station Coordinates (X, Y)
STATIONS = {
    "Core Station": (0, 0),
    "Azura Station": (-1000, 1000),
    "Vesta Station": (7000, 7000),
    "Elyse Terminal": (-70565, 72811),
    "Shangris Station": (4446, 4340),
    "G-Station": (-19567, 16308),
}

# Thruster Port Numbers
THRUSTERS = {1: 2003, 2: 2004, 3: 2006, 4: 2007, 5: 2008}

def normalize_station(name):
    """Matches partial or lowercase names to full station names."""
    query = str(name).strip().lower()
    for full_name in STATIONS:
        if query in full_name.lower():
            return full_name
    return name
