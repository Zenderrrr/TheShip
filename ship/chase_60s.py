import json
import pika
import config
import nav

TARGET_NAME = "G-Station 3-4"

# 1. Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host=config.HOST, port=2014))
channel = connection.channel()

# 2. Subscribe to the radar scanner feed using a temporary private queue
channel.exchange_declare(exchange="scanner/detected_objects", exchange_type="fanout")
queue_name = channel.queue_declare(queue="", exclusive=True).method.queue
channel.queue_bind(exchange="scanner/detected_objects", queue=queue_name)

print(f"Following {TARGET_NAME}")

try:
    # 3. Continuously receive live radar scan messages
    for method_frame, properties, body in channel.consume(queue=queue_name, auto_ack=True):
        data = json.loads(body.decode("utf-8"))

        # Search for our target in the list of detected objects
        for obj in (data if isinstance(data, list) else [data]):
            if "3-4" in str(obj.get("name", "")):
                pos = obj.get("pos", {})
                tx, ty = pos.get("x"), pos.get("y")

                # Send new waypoint coordinates to the autopilot
                if tx is not None and ty is not None:
                    nav.set_target((tx, ty))
                    print(f"\rFollowing {TARGET_NAME} at ({tx:.0f}, {ty:.0f})", end="", flush=True)
                break

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    # 4. Clean up: close the RabbitMQ connection and stop the ship
    connection.close()
    nav.stop_ship()
