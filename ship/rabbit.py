import json
import pika
import config

# 1. Connect to RabbitMQ message broker on port 2014
connection = pika.BlockingConnection(pika.ConnectionParameters(host=config.HOST, port=2014))
channel = connection.channel()

# 2. Subscribe to the scanner fanout exchange with a private queue
channel.exchange_declare(exchange="scanner/detected_objects", exchange_type="fanout")
queue_name = channel.queue_declare(queue="", exclusive=True).method.queue
channel.queue_bind(exchange="scanner/detected_objects", queue=queue_name)

print("Listening to scanner feed (press Ctrl+C to stop)...")

# 3. Print incoming scanner detections
try:
    for method_frame, properties, body in channel.consume(queue=queue_name, auto_ack=True):
        print(json.loads(body.decode("utf-8")))
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    connection.close()