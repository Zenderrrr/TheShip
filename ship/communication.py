#!/usr/bin/env python3

import argparse
import asyncio
import json
import time

import websockets

PORT = 5000
SHANGRIS_WS = "ws://127.0.0.1:2025/ws"


class Communication:
    def __init__(self, station, peer):
        self.station = station
        self.peer = peer
        self.websocket = None
        self.clients = set()

    # ==========================================
    # NACHRICHTEN AN ANDERE VM SENDEN
    # ==========================================

    async def send_to_peer(self, message):
        try:
            reader, writer = await asyncio.open_connection(self.peer, PORT)

            writer.write((json.dumps(message) + "\n").encode())

            await writer.drain()

            writer.close()
            await writer.wait_closed()

            print("[VM -> VM]", message)

        except Exception as e:
            print("[VM FEHLER]", e)

    # ==========================================
    # NACHRICHTEN VON ANDERER VM EMPFANGEN
    # ==========================================

    async def handle_client(self, reader, writer):
        try:
            while True:
                data = await reader.readline()

                if not data:
                    break

                message = json.loads(data.decode())

                print("[VM EMPFANGEN]", message)

                await self.send_to_station(message)

        except Exception as e:
            print("[CLIENT FEHLER]", e)

        finally:
            writer.close()
            await writer.wait_closed()

    # ==========================================
    # NACHRICHT AN RAUMSTATION SENDEN
    # ==========================================

    async def send_to_station(self, message):

        if self.station == "shangris":
            if self.websocket is None:
                print("[SHANGRIS] Nicht verbunden")
                return

            outgoing = {"source": "Elyse Terminal", "data": message["data"]}

            await self.websocket.send(json.dumps(outgoing))

            print("[AN SHANGRIS]", outgoing)

        elif self.station == "elyse":
            # TODO:
            # Hier muss die REST-API von Elyse
            # eingebaut werden.
            print("[AN ELYSE] REST-API fehlt:", message)

    # ==========================================
    # SHANGRIS WEBSOCKET
    # ==========================================

    async def shangris_client(self):

        while True:
            try:
                print("[SHANGRIS] Verbinde ...")

                async with websockets.connect(SHANGRIS_WS) as ws:
                    self.websocket = ws

                    print("[SHANGRIS] Verbunden!")

                    async for raw in ws:
                        message = json.loads(raw)

                        print("[VON SHANGRIS]", message)

                        if message.get("destination") == "Elyse Terminal":
                            outgoing = {
                                "source": "Shangris Station",
                                "data": message["data"],
                            }

                            await self.send_to_peer(outgoing)

            except Exception as e:
                print("[SHANGRIS FEHLER]", e)

            finally:
                self.websocket = None

            await asyncio.sleep(2)

    # ==========================================
    # TCP SERVER
    # ==========================================

    async def start_server(self):

        server = await asyncio.start_server(self.handle_client, "0.0.0.0", PORT)

        print(f"[SERVER] Port {PORT} aktiv")

        async with server:
            await server.serve_forever()

    # ==========================================
    # HAUPTPROGRAMM
    # ==========================================

    async def run(self):

        print("=" * 45)
        print("SHIP COMMUNICATION")
        print("=" * 45)
        print("Station:", self.station)
        print("Partner:", self.peer)
        print("Port:", PORT)

        tasks = [asyncio.create_task(self.start_server())]

        if self.station == "shangris":
            tasks.append(asyncio.create_task(self.shangris_client()))

        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--station", choices=["shangris", "elyse"], required=True)

    parser.add_argument("--peer", required=True)

    args = parser.parse_args()

    app = Communication(args.station, args.peer)

    try:
        asyncio.run(app.run())

    except KeyboardInterrupt:
        print("\n[STOP] Kommunikation beendet")
