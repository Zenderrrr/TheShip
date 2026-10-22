#!/usr/bin/env python3

import argparse
import asyncio
import json
import time
import uuid

import websockets

# ==========================================
# KONFIGURATION
# ==========================================

TCP_PORT = 5000
INTERVAL = 2

STATIONS = {
    "elyse": {
        "name": "Elyse Terminal",
        "url": "ws://127.0.0.1:2026/api",
        "field": "msg",
        "other": "Shangris Station",
    },
    "shangris": {
        "name": "Shangris Station",
        "url": "ws://127.0.0.1:2025/ws",
        "field": "data",
        "other": "Elyse Terminal",
    },
}


class Communication:
    def __init__(self, station, peer):
        self.station = station
        self.peer = peer
        self.config = STATIONS[station]

        self.websocket = None

        self.sent = 0
        self.received = 0
        self.forwarded = 0

        self.start_time = time.time()

        self.queue = asyncio.Queue()

    # ==========================================
    # NACHRICHT AN ANDERE VM SENDEN
    # ==========================================

    async def send_to_peer(self, message):

        try:
            reader, writer = await asyncio.open_connection(self.peer, TCP_PORT)

            writer.write((json.dumps(message) + "\n").encode("utf-8"))

            await writer.drain()

            writer.close()
            await writer.wait_closed()

            self.sent += 1

            print(f"[VM -> VM] Nachricht {self.sent} gesendet")

            return True

        except Exception as error:
            print("[VM SENDEFEHLER]", error)
            return False

    # ==========================================
    # NACHRICHT VON ANDERER VM EMPFANGEN
    # ==========================================

    async def handle_client(self, reader, writer):

        try:
            while True:
                raw = await reader.readline()

                if not raw:
                    break

                message = json.loads(raw.decode("utf-8"))

                if message.get("type") == "heartbeat":
                    print("[HEARTBEAT] Partner erreichbar")
                    continue

                if message.get("type") != "station_message":
                    print("[UNBEKANNT]", message)
                    continue

                self.received += 1

                print(f"[VM EMPFANGEN] Nachricht {self.received}")

                await self.queue.put(message)

        except Exception as error:
            print("[TCP FEHLER]", error)

        finally:
            writer.close()
            await writer.wait_closed()

    # ==========================================
    # NACHRICHT AN STATION SENDEN
    # ==========================================

    async def station_sender(self):

        while True:
            message = await self.queue.get()

            try:
                while self.websocket is None:
                    print("[WARTEN] WebSocket nicht verbunden")
                    await asyncio.sleep(1)

                # Nur Nachrichten für diese Station
                if message.get("destination") != self.config["name"]:
                    print("[IGNORIERT] Falsches Ziel")
                    continue

                outgoing = {
                    "source": message["source"],
                    self.config["field"]: message["payload"],
                }

                await self.websocket.send(json.dumps(outgoing))

                self.forwarded += 1

                print(f"[AN {self.config['name']}] Nachricht weitergeleitet")

            except Exception as error:
                print("[STATION SENDEFEHLER]", error)

                # Bei Verbindungsfehler erneut versuchen
                await self.queue.put(message)
                await asyncio.sleep(2)

            finally:
                self.queue.task_done()

    # ==========================================
    # WEBSOCKET STATION
    # ==========================================

    async def station_client(self):

        while True:
            try:
                print(f"[{self.config['name']}] Verbinde ...")

                async with websockets.connect(self.config["url"]) as ws:
                    self.websocket = ws

                    print(f"[{self.config['name']}] VERBUNDEN!")

                    async for raw in ws:
                        # print("[WEBSOCKET RAW]", raw)

                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        destination = message.get("destination")

                        if destination != self.config["other"]:
                            print("[INFO] Nachricht nicht für", self.config["other"])
                            continue

                        field = self.config["field"]

                        if field not in message:
                            print("[INFO] Nutzdaten fehlen")
                            continue

                        outgoing = {
                            "type": "station_message",
                            "id": str(uuid.uuid4()),
                            "source": self.config["name"],
                            "destination": destination,
                            "payload": message[field],
                            "timestamp": time.time(),
                        }

                        await self.send_to_peer(outgoing)

            except Exception as error:
                print("[WEBSOCKET FEHLER]", error)

            finally:
                self.websocket = None

            print("[WEBSOCKET] Neuer Versuch in 2 Sekunden")
            await asyncio.sleep(2)

    # ==========================================
    # HEARTBEAT ALLE 2 SEKUNDEN
    # ==========================================

    async def heartbeat(self):

        while True:
            message = {
                "type": "heartbeat",
                "station": self.config["name"],
                "timestamp": time.time(),
            }

            await self.send_to_peer(message)

            await asyncio.sleep(INTERVAL)

    # ==========================================
    # TCP SERVER
    # ==========================================

    async def start_server(self):

        server = await asyncio.start_server(self.handle_client, "0.0.0.0", TCP_PORT)

        print(f"[SERVER] TCP Port {TCP_PORT} aktiv")

        async with server:
            await server.serve_forever()

    # ==========================================
    # STATUS
    # ==========================================

    async def status(self):

        while True:
            await asyncio.sleep(5)

            duration = int(time.time() - self.start_time)

            print()
            print("=" * 45)
            print("SHIP COMMUNICATION STATUS")
            print("=" * 45)

            print("LAUFZEIT:", duration, "Sekunden")
            print("STATION:", self.config["name"])
            print("PARTNER:", self.peer)

            print("GESENDET:", self.sent)
            print("EMPFANGEN:", self.received)
            print("AN STATION WEITERGELEITET:", self.forwarded)

            print("WEBSOCKET:", "VERBUNDEN" if self.websocket else "GETRENNT")

            print("=" * 45)
            print()

    # ==========================================
    # HAUPTPROGRAMM
    # ==========================================

    async def run(self):

        print("=" * 45)
        print("SHIP COMMUNICATION MISSION")
        print("=" * 45)

        print("Station:", self.config["name"])
        print("Partner VM:", self.peer)
        print("TCP Port:", TCP_PORT)
        print("WebSocket:", self.config["url"])

        print("=" * 45)

        await asyncio.gather(
            self.start_server(),
            self.station_client(),
            self.station_sender(),
            self.heartbeat(),
            self.status(),
        )


# ==========================================
# START
# ==========================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--station", choices=["elyse", "shangris"], required=True)

    parser.add_argument("--peer", required=True)

    args = parser.parse_args()

    app = Communication(args.station, args.peer)

    try:
        asyncio.run(app.run())

    except KeyboardInterrupt:
        print("\n[STOP] Kommunikation beendet")
