"""
All objectives must output a single number. If several outputs are required
for a single input, multiple objectives must be specified.
"""

import numpy as np

import stl.robustness as STL
from stl.parser import parse

class Objective:

    def __init__(self):
        self.parameters = {}

    def setup(self, sut):
        self.sut = sut

    def __getattr__(self, name):
        if "parameters" in self.__dict__ and name in self.parameters:
            return self.parameters.get(name)

        raise AttributeError(name)

    def __call__(self, t, r):
        raise NotImplementedError

class Minimize(Objective):
    """Objective function which selects the minimum of the specified components
    for vector outputs and minimum value of the selected signals for signal
    outputs."""

    def __init__(self, selected=None, scale=False, invert=False, clip=True):
        super().__init__()
        if not (isinstance(selected, (list, tuple)) or selected is None):
            raise Exception("The parameter 'selected' must be None or a list or a tuple.")

        self.parameters["selected"] = selected
        self.parameters["scale"] = scale
        self.parameters["invert"] = invert
        self.parameters["clip"] = clip

    def __call__(self, t, r):
        idx = self.selected if self.selected is not None else list(range(len(r.outputs)))
        if r.output_timestamps is not None:
            # Find the minimum value of the selected signals and form a vector
            # from them.
            v = np.array([min(signal) for signal in r.outputs[idx,:]])
        else:
            # Just select the desired components.
            v = r.outputs[idx]

        if self.invert:
            v = v*(-1)
            ranges = np.asarray([[-self.sut.output_range[i][1], -self.sut.output_range[i][0]] for i in idx])
        else:
            ranges = [self.sut.output_range[i] for i in idx]

        if self.scale:
            output = self.sut.scale(v.reshape(1, -1), ranges, target_A=0, target_B=1).reshape(-1)
        else:
            output = v

        return max(0, min(1, min(output))) if self.clip else min(output)

class FalsifySTL(Objective):
    """Objective function to falsify an STL specification. By default the
    robustness is not scaled, but if scale is True and variable ranges have
    been specified for the signals, then the robustness is scaled to
    [0, 1].

    The parameter strict_horizon_check controls if an exception is raised if
    the signal is too short to determine the truth value of the specification.
    If False and the signal is too short, then the best estimate for the
    robustness is returned, but this value might be incorrect if the signal is
    augmented with appropriate values.

    The parameter epsilon is a value which is added to positive robustness
    values. A positive epsilon value thus makes falsification harder. This is
    sometimes useful if the observed values are very close to 0 but positive
    and the machine learning models consider such a value to be 0. Raising the
    bar a bit can encourage the models to work harder and eventually produce
    robustness which is nonpositive."""

    def __init__(self, specification, ranges=None, epsilon=0, scale=False, strict_horizon_check=True, nu=None):
        super().__init__()

        self.dim = 1

        if isinstance(specification, STL.STL):
            self.specification = specification
        else:
            self.specification = parse(specification, ranges=ranges, nu=nu)

        self.parameters["epsilon"] = epsilon
        self.parameters["scale"] = scale
        if self.scale and self.specification.range is None:
            raise Exception("The specification does not include a range for robustness. This is needed for scaling.")
        self.parameters["strict_horizon_check"] = strict_horizon_check

    def setup(self, sut):
        super().setup(sut)

        #if not isinstance(self.specification, STL.TLTK_MTL):
         #   raise Exception("Expected specification to be TLTK class not '{}'".format(type(self.specification)))

        self.horizon = self.specification.horizon

        # Find out variables of the formula and time bounded formulas.
        self.formula_variables = []
        self.time_bounded = []
        for node in self.specification:
            if isinstance(node, STL.Signal) and node.name not in self.formula_variables:
                self.formula_variables.append(node.name)

            if isinstance(node, (STL.Global, STL.Until)):
                self.time_bounded.append(node)
            if isinstance(node, STL.Finally):
                self.time_bounded.append(node)
                self.time_bounded.append(node.formula_robustness.formulas[0])

        """
        One problem with STL usage is that the differences between timestamps
        (input or output) from the used Simulink models can be very small and
        variable. We cannot simply take the minimum difference and use this as
        a sampling step because this can lead into very small time steps and
        thus to very long augmented signals. Very small time steps could be
        unnecessary too as the STL formula might only refer to relatively big
        time steps.

        Our solution to the above is to figure out the smallest timestep
        referred to in the STL formula and divide this into K equal pieces
        (currently K = 10). This determines a sampling period and we sample all
        signals according to this sampling period (if the SUT specifies even
        lower sampling period, we use this). This can mean discarding signal
        values or augmenting a signal. Currently we augment a signal by
        assuming a constant value.
        """

        K = 10
        smallest = 1
        for x in self.time_bounded:
            if x.lower_time_bound > 0 and x.lower_time_bound < smallest:
                smallest = x.lower_time_bound
            if x.upper_time_bound > 0 and x.upper_time_bound < smallest:
                smallest = x.upper_time_bound
        smallest /= K
        if hasattr(self.sut, "sampling_step"):
            self.sampling_period = min(smallest, self.sut.sampling_step)
        else:
            self.sampling_period = smallest

    def adjust_time_bounds(self):
        for x in self.time_bounded:
            x.old_lower_time_bound = x.lower_time_bound
            x.old_upper_time_bound = x.upper_time_bound
            x.lower_time_bound = int(x.lower_time_bound / self.sampling_period)
            x.upper_time_bound = int(x.upper_time_bound / self.sampling_period)

    def reset_time_bounds(self):
        for x in self.time_bounded:
            x.lower_time_bound = x.old_lower_time_bound
            x.upper_time_bound = x.old_upper_time_bound

    def _evaluate_vector(self, test, output):
        # We assume that the output is a single observation of a signal. It
        # follows that not all STL formulas have a clear interpretation (like
        # always[0,30](x1 > 0 and x2 > 0). It is up to the user to ensure a
        # reasonable interpretation.

        #self.specification.reset()

        timestamps = np.arange(1)
        trajectories = {}
        for var in self.formula_variables:
            try:
                idx = self.sut.outputs.index(var)
                trajectories[var] = np.array([output[idx]])
            except ValueError:
                try:
                    idx = self.sut.inputs.index[var]
                    trajectories[var] = np.array([test[idx]])
                except ValueError:
                    raise Exception(f"Variable '{var}' not in input or output variables.")

        # Notice that the return value is a Cython MemoryView.
        #robustness_signal = self.specification.eval_interval(trajectories, timestamps)

        #robustness = robustness_signal[0]

        traces = STL.Traces(timestamps, trajectories)
        robustness_signal, effective_range_signal = self.specification.eval(traces)

        return robustness_signal[0], effective_range_signal[0] if effective_range_signal is not None else None

    def _evaluate_signal(self, test, result):
        input_timestamps = test.input_timestamps
        output_timestamps = result.output_timestamps
        input_signals = test.input_denormalized
        output_signals = result.outputs

        """
        Here we find the robustness at time 0.

        We assume that the user guarantees that time is increasing. Floating
        point numbers and timestamp search do not go well together: we have 0.1
        != 0.1000000001 etc. This can lead to erroneous results. The solution
        is to use integer timestamps. Using integer timestamps then requires
        scaling the time intervals occurring in the specification formulas.
        This as already done in the setup method.
        """

        # Reset the specification for object reuse.
        #self.specification.reset()

        # Build trajectories in appropriate form.
        args = []
        for var in self.formula_variables:
            args.append(var)
            try:
                idx = self.sut.outputs.index(var)
                args.extend((output_timestamps, output_signals[idx]))
            except ValueError:
                try:
                    idx = self.sut.inputs.index(var)
                    args.extend((input_timestamps, input_signals[idx]))
                except ValueError:
                    raise Exception(f"Variable '{var}' not in input or output variables.")

        trajectories = STL.Traces.from_mixed_signals(*args, sampling_period=self.sampling_period)

        # Use integer timestamps.
        trajectories.timestamps = np.arange(len(trajectories.timestamps))

        # Allow slight inaccuracy in horizon check.
        if self.strict_horizon_check and self.horizon - 1e-2 > trajectories.timestamps[-1]:
            raise Exception(
                f"The horizon {self.horizon} of the formula is too long compared to signal length {trajectories.timestamps[-1]}. The robustness cannot be computed."
            )

        # Adjust time bounds.
        self.adjust_time_bounds()

        robustness_signal, effective_range_signal = self.specification.eval(trajectories)

        # Reset time bounds. This allows reusing the specifications.
        self.reset_time_bounds()

        return robustness_signal[0], effective_range_signal[0] if effective_range_signal is not None else None

    def __call__(self, t, r):
        if r.output_timestamps is None:
            robustness, range = self._evaluate_vector(t.inputs, r.outputs)
        else:
            robustness, range = self._evaluate_signal(t, r)

        # Scale the robustness to [0,1] if required.
        # TODO: Should epsilon be added even if no scaling is applied?
        if self.scale:
            if range is None:
                raise Exception("Scaling of robustness values requested but no scale available.")

            if robustness <= 0:
                robustness = 0
            else:
                robustness *= 1/range[1]
                robustness += self.epsilon
                robustness = min(1, robustness)

        return robustness

