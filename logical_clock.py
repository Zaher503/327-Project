#logical clock

class LamportClock:
    def __init__(self):
        self.time = 0

    # local event
    def tick(self):
        self.time =+ 1
        return self.time

    # event before send a message
    def send_event(self):
        self.time += 1
        return self.time

    # merge incoming time stamp with local clock
    def recv_event(self, received_time: int):
        self.time = max(received_time, self.time) + 1
        return self.time

