import pika
import time
from shared_log import write_log
from logical_clock import LamportClock
import json

def main():
    clock = LamportClock()

    # connect to RabbitMQ server
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # declare queue (creates it if not existing)
    channel.queue_declare(queue='file_alerts')

    # simulate sending file alerts
    for i in range(5):
        ts = clock.send_event()

        payload = {
            "file_id": f"file_{i}.txt",
            "version": i + 1,
            "ts": ts
        }

        channel.basic_publish(
            exchange='',
            routing_key='file_alerts',
            body=json.dumps(payload)
        )

        print(f"[Producer] Sent: {payload}")
        write_log(f"[Producer] Sent {payload}")

        time.sleep(1)

    connection.close()

if __name__ == "__main__":
    main()
