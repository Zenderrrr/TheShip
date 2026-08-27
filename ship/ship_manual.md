# 🚀 THE SHIP — Commander's Operations Manual & Control Reference

Comprehensive guide and system specification for piloting, trading, telemetry, dashboard widgets, and cluster infrastructure.

---

## 📌 1. Subsystems Overview

| Subsystem | Port / Protocol | Primary Purpose | Key Endpoints |
| :--- | :--- | :--- | :--- |
| **Telemetry & Sensors** | `HTTP :2011`, `:2010` | Position, heading angle, velocity vector | `GET /pos`, `GET /stations_in_reach` |
| **Autopilot / Navigation** | `HTTP :2009` | Course plotting, station targeting, stop/idle | `POST /set_target` |
| **Thruster Propulsion** | `HTTP :2003..2008` | Direct thruster percentage control (0-100%) | `PUT /thruster`, `GET /thruster` |
| **Cargo Hold & Bank** | `HTTP :2012` | Inventory counts, credit balance, capacity | `GET /hold` |
| **Commerce & Market** | `HTTP :2011` | Buying and selling resources | `POST /buy`, `POST /sell` |
| **Web UI & Widgets** | `TCP :2002` | Live dashboard widgets & markdown docs push | Socket messages: `update_widget`, `update_doc` |
| **Kubernetes Vendor** | `HTTPS :6443` | Underlying cluster workload management | `kubectl -n theship-vendor` |

---

## 🧭 2. Flight & Navigation (Port 2009)

The autopilot allows rapid waypoint setting to named stations, precise coordinates, or safety states.

### Fly to a Station
```bash
# Target named stations
curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": "Core Station"}'
curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": "Azura Station"}'
curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": "Vesta Station"}'
```

### Coordinate Waypoint
```bash
# Fly directly to target coordinates
curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": {"x": 7000, "y": 7000}}'
```

### Flight Control Modes
- **Emergency Stop:** `curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": "stop"}'`
- **Drift / Idle:** `curl -s -X POST http://192.168.103.40:2009/set_target -d '{"target": "idle"}'`

---

## 🔥 3. Direct Thruster Controls (Ports 2003–2008)

Manual thruster override allows custom maneuvers by setting thrust levels from `0%` to `100%`.

| Thruster ID | Port | Component |
| :--- | :--- | :--- |
| **Thruster 1** | `2003` | Main Forward Propulsion |
| **Thruster 2** | `2004` | Port Lateral Thruster |
| **Thruster 3** | `2006` | Starboard Lateral Thruster |
| **Thruster 4** | `2007` | Yaw / Attitude Thruster |
| **Thruster 5** | `2008` | Retro / Braking Thruster |

### Example Commands
```bash
# Set Thruster 1 to full forward burn
curl -s -X PUT http://192.168.103.40:2003/thruster -d '{"thrust_percent": 100}'

# Cut all thrust
curl -s -X PUT http://192.168.103.40:2003/thruster -d '{"thrust_percent": 0}'
```

---

## 📦 4. Cargo, Trading & Economy

### Cargo Hold Status (Port 2012)
```bash
curl -s http://192.168.103.40:2012/hold
# Output: {"kind": "success", "hold": {"resources": {"IRON": 10}, "credits": 550, "hold_size": 40, "hold_free": 30}}
```

### Stations in Reach (Port 2011)
```bash
curl -s http://192.168.103.40:2011/stations_in_reach
```

### Buying & Selling (Port 2011)
```bash
# Buy 5 Iron from Azura Station
curl -s -X POST http://192.168.103.40:2011/buy -d '{"station": "Azura Station", "what": "IRON", "amount": 5}'

# Sell 5 Iron to Core Station
curl -s -X POST http://192.168.103.40:2011/sell -d '{"station": "Core Station", "what": "IRON", "amount": 5}'
```

---

## 📊 5. Live Dashboard Widgets (Port 2002)

Your personal web dashboard connects to the game orchestrator over a raw TCP socket on Port `2002`.

### Protocol Specification
- Messages are UTF-8 JSON payloads terminated with a null byte `\0`.
- Keepalive is sustained by echoing `{"kind": "keepalive"}\0` when the server sends a null delimiter.

### Available Widget Groups & Formats
```json
{
  "kind": "update_widget",
  "widget": {
    "title": "Ship Navigation & Target",
    "group": "navigation",
    "width": 2,
    "height": 2,
    "content": {
      "kind": "text",
      "text": "Target: Vesta Station (7000, 7000)\nSpeed: 14.2 m/s\nHeading: 45°"
    }
  }
}
```

```json
{
  "kind": "update_doc",
  "doc": "# Live Ship Documentation\nAll systems nominal."
}
```

---

## 🎯 6. Mission Objectives
- **Objective:** Fully load the ship cargo hold with **IRON** (40 units) and dock at **Vesta Station (7000, 7000)**.
- **Trading Route Tip:** Buy low at **Azura Station (-1000, 1000)** and sell or trade near **Core Station (0, 0)**.
