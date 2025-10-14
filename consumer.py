import pika

def main():
    # callback for processing messages
    def callback(ch, method, properties, body):
        print(f"[Consumer] Received: {body.decode()}")

    # connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    # ensure queue exists
    channel.queue_declare(queue='file_alerts')

    # subscribe to the queue
    channel.basic_consume(queue='file_alerts', on_message_callback=callback, auto_ack=True)

    print("[Consumer] Waiting for messages... press Ctrl+C to exit.")
    channel.start_consuming()

if __name__ == "__main__":
    main()