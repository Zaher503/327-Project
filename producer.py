import pika
import time

def main():
    # connect to RabbitMQ server
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # declare queue (creates it if not existing)
    channel.queue_declare(queue='file_alerts')

    # simulate sending file alerts
    for i in range(5):
        message = f"File file_{i}.txt was updated"
        channel.basic_publish(exchange='', routing_key='file_alerts', body=message)
        print(f"[Producer] Sent: {message}")

        # resource protected write
        write_log(f"[Producer] Sent {message}")
        
        time.sleep(1)

    connection.close()

if __name__ == "__main__":

    main()
