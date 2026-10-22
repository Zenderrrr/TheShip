#!/usr/bin/env python3

import argparse
import asyncio
import json
import time

import websockets

PORT = 5000

STATIONS = {
    "elyse": {
        "name": "Elyse Terminal",
        "url": "ws://127.0.0.1:2026/api",
        "incoming_field": "msg",
        "outgoing_field": "msg",
        "other_station": "Shangris Station",
    },
    "shangris": {
        "name": "Shangris Station",
        "url": "ws://127.0.0.1:2025/ws",
        "incoming_field": "data",
        "outgoing_field": "data",
        "other_station": "Elyse Terminal",
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
        self.start_time = time.time()

    # ==========================================
    # NACHRICHT AN ANDERE VM SENDEN
    # ==========================================

    async def send_to_peer(self, message):
        try:
            reader, writer = await asyncio.open_connection(
                self.peer,
                PORT,
            )

            writer.write((json.dumps(message) + "\n").encode("utf-8"))

            await writer.drain()

            writer.close()
            await writer.wait_closed()

            self.sent += 1

            print(f"[VM -> VM] Nachricht {self.sent}: {message}")

        except Exception as error:
            print("[VM SENDEFEHLER]", error)

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

                self.received += 1

                print(f"[VM EMPFANGEN] Nachricht {self.received}: {message}")

                await self.send_to_station(message)

        except Exception as error:
            print("[TCP FEHLER]", error)

        finally:
            writer.close()
            await writer.wait_closed()

    # ==========================================
    # NACHRICHT AN RAUMSTATION SENDEN
    # ==========================================

    async def send_to_station(self, message):

        if self.websocket is None:
            print("[WARNUNG] Station nicht verbunden")
            return

        field = self.config["outgoing_field"]

        outgoing = {
            "source": self.config["other_station"],
            field: message["payload"],
        }

        try:
            await self.websocket.send(json.dumps(outgoing))

            print(f"[AN {self.config['name']}] {outgoing}")

        except Exception as error:
            print("[STATION SENDEFEHLER]", error)

    # ==========================================
    # WEBSOCKET CLIENT
    # ==========================================

    async def station_client(self):

        while True:
            try:
                print(f"[{self.config['name']}] Verbinde ...")

                async with websockets.connect(self.config["url"]) as ws:
                    self.websocket = ws

                    print(f"[{self.config['name']}] Verbunden!")

                    async for raw in ws:
                        message = json.loads(raw)

                        print(f"[VON {self.config['name']}] {message}")

                        # Nur Nachrichten weiterleiten,
                        # die an die andere Station gehen.

                        if message.get("destination") != self.config["other_station"]:
                            continue

                        field = self.config["incoming_field"]

                        if field not in message:
                            continue

                        outgoing = {
                            "source": self.config["name"],
                            "destination": self.config["other_station"],
                            "payload": message[field],
                            "timestamp": time.time(),
                        }

                        await self.send_to_peer(outgoing)

            except Exception as error:
                print("[WEBSOCKET FEHLER]", error)

            finally:
                self.websocket = None

            await asyncio.sleep(2)

    # ==========================================
    # TCP SERVER
    # ==========================================

    async def start_server(self):

        server = await asyncio.start_server(
            self.handle_client,
            "0.0.0.0",
            PORT,
        )

        print(f"[SERVER] TCP Port {PORT} aktiv")

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
            print(f"LAUFZEIT: {duration} Sekunden")
            print(f"GESENDET: {self.sent}")
            print(f"EMPFANGEN: {self.received}")
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
        print("TCP Port:", PORT)
        print("WebSocket:", self.config["url"])
        print("=" * 45)

        await asyncio.gather(
            self.start_server(),
            self.station_client(),
            self.status(),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--station",
        choices=["elyse", "shangris"],
        required=True,
    )

    parser.add_argument(
        "--peer",
        required=True,
    )

    args = parser.parse_args()

    app = Communication(
        args.station,
        args.peer,
    )

    try:
        asyncio.run(app.run())

    except KeyboardInterrupt:
        print("\n[STOP] Kommunikation beendet")
