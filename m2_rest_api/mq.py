import os
import pika

class MqPublisher:
    def __init__(self):
        self.host = os.environ.get("RABBITMQ_HOST", "localhost")
        self.queue = os.environ.get("RABBITMQ_QUEUE", "file_alerts")
        self._connection = None
        self._channel = None
        self._enabled = True

        try:
            self._connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
            self._channel = self._connection.channel()
            self._channel.queue_declare(queue=self.queue, durable=False)
        except Exception:
            # RabbitMQ not reachable — keep API running, skip publishing
            self._enabled = False

    def publish(self, message: str):
        if not self._enabled or not self._channel:
            return False
        try:
            self._channel.basic_publish(exchange="", routing_key=self.queue, body=message)
            return True
        except Exception:
            return False

    def close(self):
        try:
            if self._connection:
                self._connection.close()
        except Exception:
            pass
