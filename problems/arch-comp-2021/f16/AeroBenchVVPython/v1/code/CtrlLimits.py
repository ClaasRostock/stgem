'''
Stanley Bak
F-16 GCAS ctrl limits
'''

from util import Freezable

class CtrlLimits(Freezable):
    'Control Limits'

    def __init__(self):
        self.ThrottleMax = 1 # Afterburner on for throttle > 0.7
        self.ThrottleMin = 0
        self.ElevatorMaxDeg = 25
        self.ElevatorMinDeg = -25
        self.AileronMaxDeg = 21.5
        self.AileronMinDeg = -21.5
        self.RudderMaxDeg = 30
        self.RudderMinDeg = -30
        self.MaxBankDeg = 60 # For turning maneuvers
        self.NzMax = 6
        self.NzMin = -1

        self.check()

        self.freeze_attrs()

    def check(self):
        'check that limits are in bounds'

        ctrlLimits = self

        assert (
            ctrlLimits.ThrottleMin >= 0 and ctrlLimits.ThrottleMax <= 1
        ), 'ctrlLimits: Throttle Limits (0 to 1)'

        assert (
            ctrlLimits.ElevatorMaxDeg <= 25 and ctrlLimits.ElevatorMinDeg >= -25
        ), 'ctrlLimits: Elevator Limits (-25 deg to 25 deg)'

        assert (
            ctrlLimits.AileronMaxDeg <= 21.5 and ctrlLimits.AileronMinDeg >= -21.5
        ), 'ctrlLimits: Aileron Limits (-21.5 deg to 21.5 deg)'

        assert (
            ctrlLimits.RudderMaxDeg <= 30 and ctrlLimits.RudderMinDeg >= -30
        ), 'ctrlLimits: Rudder Limits (-30 deg to 30 deg)'
