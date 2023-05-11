import json
import uuid


class BeamNGWaypoint:
    def __init__(self, name, position, persistentId=None):
        self.name = name
        self.position = position
        self.persistentId = persistentId if persistentId else str(uuid.uuid4())

    def to_json(self):
        obj = {
            'name': self.name,
            'class': 'BeamNGWaypoint',
            'persistentId': self.persistentId,
            '__parent': 'generated',
            'position': self.position,
            'scale': [4, 4, 4],
        }
        return json.dumps(obj)
