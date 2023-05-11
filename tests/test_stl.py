import unittest, traceback

import numpy as np
import pandas as pd

from stgem.sut import SUT, SUTInput, SUTOutput
from stgem.objective.objective import FalsifySTL
import stl.robustness as STL
import stl.parser as Parser

class DummySUT(SUT):
    def __init__(self, odim, outputs):
        super().__init__()
        self.odim = odim
        self.outputs = outputs
        self.output_range = [None for _ in range(self.odim)]
        self.idim = 2
        self.inputs = ["i1", "i2"]
        self.input_range = [None, None]

class TestSTL(unittest.TestCase):

    def get_with_range(self, specification, timestamps, signals, ranges, time, nu=None):
        spec = Parser.parse(specification, ranges=ranges, nu=nu)

        formula_variables = []
        time_bounded = []
        for node in spec:
            if isinstance(node, STL.Signal) and node.name not in formula_variables:
                formula_variables.append(node.name)

            if isinstance(node, (STL.Global, STL.Until)):
                time_bounded.append(node)
            if isinstance(node, STL.Finally):
                time_bounded.extend((node, node.formula_robustness.formulas[0]))
        args = []
        for var in formula_variables:
            args.extend((var, timestamps, signals[var]))
        # Adjust time bounds to integers.
        sampling_period = 1/10
        for x in time_bounded:
            x.old_lower_time_bound = x.lower_time_bound
            x.old_upper_time_bound = x.upper_time_bound
            x.lower_time_bound = int(x.lower_time_bound / sampling_period)
            x.upper_time_bound = int(x.upper_time_bound / sampling_period)

        trajectories = STL.Traces.from_mixed_signals(*args, sampling_period=sampling_period)
        trajectories.timestamps = np.arange(len(trajectories.timestamps))
        robustness_signal, effective_range = spec.eval(trajectories)

        # Reset time bounds.
        for x in time_bounded:
            x.lower_time_bound = x.old_lower_time_bound
            x.upper_time_bound = x.old_upper_time_bound

        return robustness_signal[time], effective_range[time]

    def get(self, specification, variables, sut_input, sut_output, ranges=None, time=None, scale=False, strict_horizon_check=True, nu=None):
        sut = DummySUT(len(variables), variables)
        objective = FalsifySTL(specification, ranges=ranges, scale=scale, strict_horizon_check=strict_horizon_check, nu=nu)
        objective.setup(sut)
        return objective(sut_input, sut_output), objective

    def test_stl(self):
        # Test the moving window.
        # ---------------------------------------------------------------------
        sequence = [2, 1, 2, 3, 4, 5, 6, 7, 0, 9]
        window = STL.Window(sequence)
        assert window.update(10, 15) == -1
        assert window.update(-5, -2) == -1
        assert window.update(9, 15) == 9
        assert window.update(8, 14) == 8
        assert window.update(7, 10) == 8
        assert window.update(7, 8) == 7
        assert window.update(4, 6) == 4
        assert window.update(0, 5) == 1
        assert window.update(0, 4) == 1
        assert window.update(2, 4) == 2
        assert window.update(1, 6) == 1
        assert window.update(3, 8) == 3
        assert window.update(1, 9) == 8
        assert window.update(2, 8) == 2

        # Test vector-valued output.
        # ---------------------------------------------------------------------
        output = [3, 0.5]
        variables = ["foo", "bar"]
        specification = "foo > 0 and bar > 0"
        correct_robustness = 0.5

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(output, None, None, None))
        assert robustness == correct_robustness

        output = [3, -0.5]
        variables = ["foo", "bar"]
        specification = "always[0,1] (foo > 0 and bar > 0)"
        correct_robustness = -0.5

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(output, None, None, None))
        assert robustness == correct_robustness

        # Test signal outputs.
        # ---------------------------------------------------------------------
        t = [0.0, 0.5, 1.0, 1.5, 2.0]
        s1 = [4.0, 6.0, 2.0, 8.0, -1.0]
        s2 = [3.0, 6.0, 1.0, 0.5,  3.0]
        signals = [s1, s2]
        variables = ["s1", "s2"]
        specification = "always[0,1] (s1 >= 0 and s2 >= 0)"
        correct_robustness = 1.0

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None))
        assert robustness == correct_robustness

        data = pd.read_csv("data/stl_at.csv")
        t = data["time"].tolist()
        s1 = data["SPEED"].tolist()
        s2 = data["RPM"].tolist()
        # The following holds for the signals:
        # always[0,30](RPM < 3000) is true, maximum is 2995.4899293611793.
        # We have SPEED < 39.55047897841963 [0, 4].
        # We have SPEED < 45.06303990113543 in [0, 8].
        # We have SPEED < 45.063039901135426 in [0, 20]:
        signals = [s1, s2]
        variables = ["SPEED", "RPM"]
        scale = False
        specification = "(always[0,30] RPM <= 3000) -> (always[0,4] SPEED <= 35)"
        correct_robustness = -4.55048

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale)
        assert abs(robustness - correct_robustness) < 1e-5

        specification = "(always[0,30] RPM <= 3000) -> (always[0,8] SPEED < 50)"
        correct_robustness = 4.936960098864567

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale)
        assert abs(robustness - correct_robustness) < 1e-5

        specification = "(always[0,30] RPM <= 3000) -> (always[0,20] SPEED < 65)"
        correct_robustness = 19.936958

        robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale)
        assert abs(robustness - correct_robustness) < 1e-5

        # Test until operator.
        # ---------------------------------------------------------------------
        specification = "SPEED < 2.10 until[0.1,0.2] RPM > 2000"
        correct_robustness = 0.0033535970602489584

        robustness, objective = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale)
        assert abs(robustness - correct_robustness) < 1e-5

        s3 = 10000*np.ones_like(s1)
        signals = [s1, s2, s3]
        variables = ["SPEED", "RPM", "VERUM"]
        specification = "(not (VERUM until[0,30] RPM > 3000)) -> (not (VERUM until[0,4] SPEED > 35))"
        correct_robustness = -4.55048

        robustness, objective = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale)
        assert abs(robustness - correct_robustness) < 1e-5

        # Test time horizon.
        # ---------------------------------------------------------------------
        t = [0.5*i for i in range(21)]
        #     0  0.5 1.0 1.5 2.0 2.5 3.0 3.5 4.0 4.5 5.0 5.5 6.0 6.5 7.0 7.5 8.0 8.5 9.0 9.5 10
        s1 = [0, 0,  0,  6,  0,  0,  6,  0,  0,  6,  0,  0,  5,  0,  0,  0,  0,  0,  6,  0,  0]
        s2 = [0, 0,  0,  0,  0,  0,  4,  0,  0,  0,  4,  0,  4,  4,  4,  0,  0,  0,  4,  0,  0]
        variables = ["s1", "s2"]
        signals = [s1, s2]
        specification = "always[0,10] ( (s1 >= 5) -> (eventually[0,1] s2 <= 3) )"
        correct_robustness = 0

        # Check with strict horizon check.
        try:
            robustness, _ = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale, strict_horizon_check=True)
        except Exception as E:
            if not E.args[0].startswith("The horizon"):
                traceback.print_exc()
                raise
        # Check without strict horizon check.
        robustness, objective = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), scale=scale, strict_horizon_check=False)
        assert objective.horizon == 11
        assert robustness == correct_robustness

        # Test time series adjustment.
        # ---------------------------------------------------------------------
        t1 = [0, 1, 2, 3]
        i1 = [1, 3, 4, 1]
        t2 = [0, 0.5, 1, 2, 2.5, 3]
        s1 = [2, 2, 2, 2, 2, 2]
        variables = ["s1"]
        specification = "always[0,3] i1 >= s1"
        correct_robustness = -1.0

        robustness, objective = self.get(specification, variables, SUTInput(None, [i1], t1), SUTOutput([s1], t2, None, None), scale=scale)
        assert objective.horizon == 3
        assert robustness == correct_robustness

        # Test signal ranges.
        # ---------------------------------------------------------------------
        t = [0, 1, 2, 3, 4, 5]
        s1 = [100, 150, 70, 30, 190, 110]   # scale [0, 200]
        s2 = [4500, 100, 0, 2300, -100, -5] # scale [-200, 4500]
        variables = ["s1", "s2"]
        signals = [s1, s2]
        specification = "3*s1 <= s2"
        ranges = {"s1": [0, 200], "s2": [-200, 4500]}

        robustness, objective = self.get(specification, variables, SUTInput(None, None, None), SUTOutput(signals, t, None, None), ranges=ranges, scale=scale)
        assert objective.specification.range == [-800, 4500]

        # Test effective ranges.
        # ---------------------------------------------------------------------
        specification = "s1 and s2"
        signals = {"s1": s1, "s2": s2}

        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=0)
        assert (effective_range == np.array([0, 200])).all()
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=10)
        assert (effective_range == [-200, 4500]).all()

        specification = "3*s1 or (3*s1 <= s2)"
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=0)
        assert (effective_range == [-800, 4500]).all()
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=10)
        assert (effective_range == [0, 600]).all()

        specification = "always[3,4] (s1 and s2)"
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=0)
        assert (effective_range == [-200, 4500]).all()

        specification = "s1 until[0,4] (not s2)"
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=0)
        assert (effective_range == [0, 200]).all()

        specification = "s1 until[0,2] (not s2)"
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=1)
        assert (effective_range == [-4500, 200]).all()

        # Test alternative robustness.
        # ---------------------------------------------------------------------
        specification = "s1 and s2"
        variables = ["s1", "s2"]

        eps = 1e-4

        correct_robustness = 100.0
        correct_interval = [-1.55622645e-17, 2.00000000e+02]
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=0, nu=1)
        assert robustness == correct_robustness
        assert abs(effective_range[0] - correct_interval[0]) < eps and abs(effective_range[1] - correct_interval[1]) < eps
        correct_robustness = 118.87703343990728
        correct_interval = [-124.49186624, 2876.57512417]
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=10, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4
        assert abs(effective_range[0] - correct_interval[0]) < eps and abs(effective_range[1] - correct_interval[1]) < eps
        correct_robustness = 0
        correct_interval = [0, 0]
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=20, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4
        assert abs(effective_range[0] - correct_interval[0]) < eps and abs(effective_range[1] - correct_interval[1]) < eps
        correct_robustness = -95.07160938995717
        correct_interval = [-189.56928738, 4275.73967876]
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=40, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4
        assert abs(effective_range[0] - correct_interval[0]) < eps and abs(effective_range[1] - correct_interval[1]) < eps

        # Test alternative robustness nonassociativity.
        # ---------------------------------------------------------------------
        specification = "s1 and s2 and s1/3"
        ranges = {"s1": [0.5, 200], "s2": [-200, 4500]}

        correct_robustness = 71.23948086977792
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=10, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4
        correct_robustness = -4.998798729741061
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=50, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4

        specification = "s1 and (s2 and s1/3)"

        correct_robustness = 81.06600514116339
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=10, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4
        correct_robustness = -4.998798729743643
        robustness, effective_range = self.get_with_range(specification, t, signals, ranges, time=50, nu=1)
        assert abs(robustness - correct_robustness) < 1e-4

if __name__ == "__main__":
    unittest.main()

