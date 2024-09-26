class BoardSpotClass:
    def __init__(self):
        self.disk_user = None
        self.ring_user = None

    def set_ring(self, user_id):
        self.ring_user = user_id

    def set_disk(self, user_id):
        self.disk_user = user_id

    def __str__(self):
        return self.disk_user.__str__()

    def to_json(self):
        return {"disk_user": self.disk_user, "ring_user": self.ring_user}
