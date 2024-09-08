class LamportClock:
    def __init__(self):
        self.clock = 0

    def increment(self):
        self.clock += 1

    def get_time(self):
        return self.clock

    def update(self, received_time):
        self.clock = max(self.clock, received_time) + 1
