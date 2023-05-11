import numpy as np

# TODO: Save computed robustness values for efficiency and implement reset for reuse.

class Window:
    """A class for sliding a varying-length window along a signal and for
    finding the minimum or maximum over the window."""

    def __init__(self, sequence, find_min=True):
        self.sequence = sequence
        self.find_min = find_min

        self.argminmax = np.argmin if find_min else np.argmax
        self.better = lambda x, y: x < y if find_min else lambda x, y: x > y

        self.prev_best_idx = len(self.sequence)
        self.prev_best = float("inf") if self.find_min else float("-inf")

        self.prev_start_pos = len(self.sequence)
        self.prev_end_pos = len(self.sequence)

    def update(self, start_pos, end_pos):
        """Update the window location, and return the best value (minimum or
        maximum) in the updated window."""

        start = start_pos
        end = end_pos

        # If the window is outside of the sequence, return -1.
        if start >= len(self.sequence) or end < 0:
            return -1

        # Adjust the beginning and end if out of scope.
        end = min(end, len(self.sequence))
        start = max(start, 0)

        if start >= end:
            raise Exception(
                f"Window start position {start} before its end position {end}."
            )

        # We have three areas we need to care about: an overlap, for which we
        # hopefully know the answer, and two areas to the left and right of the
        # overlap. Each of these three areas can be empty.
        if start < self.prev_start_pos:
            # Disjoint and to the left.
            l_s = start
            if end <= self.prev_start_pos:
                l_e = end
                o_s = -1
                o_e = -1
                r_s = -1
                r_e = -1
            else:
                l_e = self.prev_start_pos
                if end <= self.prev_end_pos:
                    o_e = end
                    r_s = -1
                    r_e = -1
                else:
                    o_e = self.prev_end_pos
                    r_s = self.prev_end_pos
                    r_e = end
                o_s = self.prev_start_pos
        else:
            if start >= self.prev_end_pos:
                o_s = -1
                o_e = -1
                r_s = start
                r_e = end
            else:
                o_s = start
                if end <= self.prev_end_pos:
                    o_e = end
                    r_s = -1
                    r_e = -1
                else:
                    o_e = self.prev_end_pos
                    r_s = self.prev_end_pos
                    r_e = end

            l_e = -1
            # Disjoint and to the right.
            l_s = -1
        # Find the minimums from each area. If the previous best value is not
        # in the overlap, we need to search the whole overlap.
        best_idx = -1
        if o_s < o_e:
            if o_s <= self.prev_best_idx < o_e:
                best_idx = self.prev_best_idx
            else:
                best_idx = o_s + self.argminmax(self.sequence[o_s:o_e])
                self.prev_best = self.sequence[best_idx]
        if l_s < l_e:
            left_idx = l_s + self.argminmax(self.sequence[l_s:l_e])
            if best_idx == -1 or self.better(self.sequence[left_idx], self.prev_best):
                best_idx = left_idx
                self.prev_best = self.sequence[best_idx]
        if r_s < r_e:
            right_idx = r_s + self.argminmax(self.sequence[r_s:r_e])
            if best_idx == -1 or self.better(self.sequence[right_idx], self.prev_best):
                best_idx = right_idx
                self.prev_best = self.sequence[best_idx]

        self.prev_best_idx = best_idx
        self.prev_start_pos = start_pos
        self.prev_end_pos = end_pos

        return self.prev_best_idx

class Traces:

    def __init__(self, timestamps, signals):
        self.timestamps = timestamps
        self.signals = signals

        # Check that all signals have correct length.
        for s in signals.values():
            if len(s) != len(timestamps):
                raise ValueError("All signals must have exactly as many samples as there are timestamps.")

    @classmethod
    def from_mixed_signals(cls, *args, sampling_period=None):
        """Instantiate the class from signals that have different timestamps
        (with 0 as a first timestamp) and different lengths. This is done by
        finding the maximum signal length and using that as a signal length,
        dividing this length into pieces according to the sampling period
        (smallest observed difference between timestamps if None), and filling
        values by assuming constant value.

        The input is expected to be of the form
        name1, timestamps1, signal1, name2, timestamps2, signal2, ..."""

        """
        Currently the code does not work reliably with time steps lower than
        1e-4, but this should be enough.
        """

        if sampling_period is None:
            raise NotImplementedError()

        # Check that all timestamps begin with 0. Otherwise the code below is
        # not valid.
        for i in range(0, len(args), 3):
            if args[i+1][0] != 0:
                raise Exception("The first timestamp should be 0 in all signals.")

        # Maximum signal length.
        T = max(args[i+1][-1] for i in range(0, len(args), 3))

        # New timestamps.
        timestamps = [i*sampling_period for i in range(0, int(T/sampling_period) + 1)]

        # Check that all signals begin from time 0. Otherwise this does not work.

        # Fill the signals by assuming constant value.
        signals = {}
        eps = 1e-5
        for i in range(0, len(args), 3):
            name = args[i]
            signal_timestamps = args[i+1]
            signal_values = args[i+2]

            signals[name] = np.empty(shape=(len(timestamps)))
            pos = 0
            for n, t in enumerate(timestamps):
                while pos < len(signal_timestamps) and signal_timestamps[pos] <= t + eps:
                    pos += 1

                value = signal_values[pos - 1]
                signals[name][n] = value

        return cls(timestamps, signals)

    def search_time_index(self, t, start=0):
        """Finds the index of the time t in the timestamps using binary
        search."""

        lower_idx = start
        upper_idx = len(self.timestamps) - 1
        middle = (lower_idx + upper_idx)//2
        while lower_idx <= upper_idx:
            if self.timestamps[middle] < t:
                lower_idx = middle + 1
            elif self.timestamps[middle] > t:
                upper_idx = middle - 1
            else:
                break

            middle = (lower_idx + upper_idx)//2

        return middle if self.timestamps[middle] == t else -1

class TreeIterator:

    def __init__(self, node):
        self.nodes = [node]

    def __next__(self):
        try:
            node = self.nodes.pop(0)
            self.nodes += node.formulas

            return node
        except IndexError:
            raise StopIteration

class STL:
    """Base class for all logical operations and atoms."""

    def __iter__(self):
        return TreeIterator(self)

class Signal(STL):

    def __init__(self, name, range=None):
        self.formulas = []
        self.name = name
        self.range = range.copy() if range is not None else None
        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None
        # We return a copy so that subsequent robustness computations can
        # safely reuse arrays. We also enforce floats in order to avoid errors.
        return np.array(traces.signals[self.name], copy=True, dtype="float64"), effective_range_signal

class Constant(STL):

    def __init__(self, val):
        self.formulas = []
        self.val = val
        self.range = [val, val]
        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range:
            effective_range_signal = np.full(shape=(len(traces.timestamps), 2), fill_value=self.val)
        else:
            effective_range_signal = None
        # We must always produce a new array because subsequent robustness
        # computations can reuse arrays.
        return np.full(len(traces.timestamps), self.val), effective_range_signal

class Sum(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0] + self.formulas[1].range[0]
            B = self.formulas[0].range[1] + self.formulas[1].range[1]
            self.range = [A, B]

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.add(left_formula_robustness, right_formula_robustness, out=left_formula_robustness), effective_range_signal

class Subtract(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0] - self.formulas[1].range[1]
            B = self.formulas[0].range[1] - self.formulas[1].range[0]
            self.range = [A, B]

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.subtract(left_formula_robustness, right_formula_robustness, out=left_formula_robustness), effective_range_signal

class Multiply(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]
        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0] * self.formulas[1].range[0]
            B = self.formulas[0].range[1] * self.formulas[1].range[1]
            self.range = [A, B]
        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.multiply(left_formula_robustness, right_formula_robustness, out=left_formula_robustness), effective_range_signal

class Divide(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]
        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            if self.formulas[1].range[1] == 0:
                raise Exception("Cannot determine a finite range for division as the right formula upper bound is 0.")
            if self.formulas[1].range[0] == 0:
                raise Exception("Cannot determine a finite range for division as the right formula lower bound is 0.")
            A = self.formulas[0].range[0] / self.formulas[1].range[1]
            B = self.formulas[0].range[1] / self.formulas[1].range[0]
            self.range = [A, B]
        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.divide(left_formula_robustness, right_formula_robustness, out=left_formula_robustness), effective_range_signal

class GreaterThan(STL):

    def __init__(self, left_formula, right_formula):
        if isinstance(left_formula, (int, float)):
            left_formula = Constant(left_formula)
        if isinstance(right_formula, (int, float)):
            right_formula = Constant(right_formula)
        self.formulas = [left_formula, right_formula]

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0] - self.formulas[1].range[1]
            B = self.formulas[0].range[1] - self.formulas[1].range[0]
            self.range = [A, B]

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.subtract(left_formula_robustness, right_formula_robustness, out=left_formula_robustness), effective_range_signal

class LessThan(STL):

    def __init__(self, left_formula, right_formula):
        if isinstance(left_formula, (int, float)):
            left_formula = Constant(left_formula)
        if isinstance(right_formula, (int, float)):
            right_formula = Constant(right_formula)
        self.formulas = [left_formula, right_formula]

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[1].range[0] - self.formulas[0].range[1]
            B = self.formulas[1].range[1] - self.formulas[0].range[0]
            self.range = [A, B]

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        left_formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        right_formula_robustness, _ = self.formulas[1].eval(traces, return_effective_range=False)
        return np.subtract(right_formula_robustness, left_formula_robustness, out=right_formula_robustness), effective_range_signal

class Abs(STL):

    def __init__(self, formula):
        self.formulas = [formula]
        if self.formulas[0].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0]
            B = self.formulas[0].range[1]
            if A <= 0:
                self.range = [0, B] if B > 0 else [-B, -A]
            else:
                self.range = [A, B]

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        formula_robustness, _ = self.formulas[0].eval(traces, return_effective_range=False)
        return np.abs(formula_robustness, out=formula_robustness), effective_range_signal

class Equals(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]
        self.formula_robustness = Not(Abs(Subtract(self.formulas[0], self.formulas[1])))

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = self.formulas[0].range[0] - self.formulas[1].range[1]
            B = self.formulas[0].range[1] - self.formulas[1].range[0]
            if A >= 0:
                self.range = [-B, -A]
            elif B >= 0:
                self.range = [-max(-A, B), 0]
            else:
                self.range = [A, B]
            # Make sure that 1 is included in the interval.
            if self.range[0] > 1:
                self.range[0] = 1
            elif self.range[1] < 1:
                self.range[1] = 1

        self.horizon = 0

    def eval(self, traces, return_effective_range=True):
        if return_effective_range and self.range is not None:
            effective_range_signal = np.empty(shape=(len(traces.timestamps), 2))
            effective_range_signal[:] = np.array([self.range[0], self.range[1]]).reshape(1, 2)
        else:
            effective_range_signal = None

        robustness, _ = self.formula_robustness.eval(traces, return_effective_range=False)
        return np.where(robustness == 0, 1, robustness), effective_range_signal

class Next(STL):

    def __init__(self, formula):
        self.formulas = [formula]
        self.range = self.formulas[0].range.copy() if self.formulas[0].range is not None else None
        self.horizon = 1 + self.formulas[0].horizon

    def eval(self, traces, return_effective_range=True):
        formula_robustness, formula_effective_range_signal = self.formulas[0].eval(traces, return_effective_range)
        robustness = np.roll(formula_robustness, -1)[:-1]
        if return_effective_range and self.range is not None:
            effective_range_signal = np.roll(formula_effective_range_signal, -1)[:-1]
        else:
            effective_range_signal = None

        return robustness, formula_effective_range

class Until(STL):

    def __init__(self, lower_time_bound, upper_time_bound, left_formula, right_formula):
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.formulas = [left_formula, right_formula]
        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            A = max(self.formulas[0].range[1], self.formulas[1].range[1])
            B = min(self.formulas[0].range[0], self.formulas[1].range[0])
            self.range = [A, B]

        self.horizon = self.upper_time_bound +  max(self.formulas[0].horizon, self.formulas[1].horizon)

    def eval(self, traces, return_effective_range=True):
        left_formula_robustness, left_formula_effective_range_signal = self.formulas[0].eval(traces, return_effective_range)
        right_formula_robustness, right_formula_effective_range_signal = self.formulas[1].eval(traces, return_effective_range)

        robustness = np.empty(shape=(len(left_formula_robustness)))
        return_effective_range = return_effective_range and left_formula_effective_range_signal is not None and left_formula_effective_range_signal is not None
        if return_effective_range:
            effective_range_signal = np.empty(shape=(len(left_formula_effective_range_signal), 2))

        # We save the previously found positions; see the corresponding comment
        # in eval of Global.
        prev_lower_bound_pos = len(traces.timestamps) - 1
        prev_upper_bound_pos = len(traces.timestamps) - 1
        window = Window(left_formula_robustness)
        for current_time_pos in range(len(traces.timestamps) - 1, -1, -1):
            # Lower and upper times for the current time.
            lower_bound = traces.timestamps[current_time_pos] + self.lower_time_bound
            upper_bound = traces.timestamps[current_time_pos] + self.upper_time_bound

            # Find the corresponding positions in timestamps.
            # Lower bound.
            if lower_bound > traces.timestamps[-1]:
                # If the lower bound is out of scope, then the right robustness
                # term in the min clause does not exist, so it is reasonable to
                # compute the inf term to the end of the signal and use that as
                # the robustness.
                inf_min_idx = window.update(current_time_pos, len(traces.timestamps))
                robustness[current_time_pos] = left_formula_robustness[inf_min_idx]
                if return_effective_range:
                    effective_range_signal[current_time_pos] = left_formula_effective_range_signal[inf_min_idx]

                continue
            else:
                if traces.timestamps[prev_lower_bound_pos - 1] == lower_bound:
                    lower_bound_pos = prev_lower_bound_pos - 1
                else:
                    lower_bound_pos = traces.search_time_index(lower_bound, start=current_time_pos)
                    # TODO: This should never happen except for floating point
                    # inaccuracies. We now raise an exception as otherwise the
                    # user gets unexpected behavior.
                    if lower_bound_pos < 0:
                        raise Exception(
                            f"No timestamp '{lower_bound}' found even though it should exist."
                        )
            # Upper bound.
            if upper_bound > traces.timestamps[-1]:
                upper_bound_pos = len(traces.timestamps) - 1
            elif traces.timestamps[prev_upper_bound_pos - 1] == upper_bound:
                upper_bound_pos = prev_upper_bound_pos - 1
            else:
                upper_bound_pos = traces.search_time_index(upper_bound, start=lower_bound_pos)
                    # See above.
                if upper_bound_pos < 0:
                    raise Exception(
                        f"No timestamp '{upper_bound}' found even though it should exist."
                    )

            # Move a window with start position current_time_pos and end
            # position in the interval determined by lower_bound_pos and upper_bound_pos.
            # Compute
            # TODO:
            maximum = float("-inf")
            maximum_idx = None
            maximum_robustness = None
            for window_end_pos in range(lower_bound_pos, upper_bound_pos + 1):
                # This is the infimum term.
                if current_time_pos == window_end_pos:
                    # This is a special case where the infimum term is taken
                    # over an empty interval. We return an infinite value to
                    # always select other robustness value.
                    inf_min_idx = window_end_pos
                    L = float("inf")
                else:
                    inf_min_idx = window.update(current_time_pos, window_end_pos)
                    if inf_min_idx == -1:
                        # The window was out of scope. This happens only in
                        # exceptional circumstances. We guess the value then to be
                        # the final robustness value observed.
                        inf_min_idx = len(traces.timestamps) - 1
                    L = left_formula_robustness[inf_min_idx]

                # Compute the minimum of the right robustness and the inf term.
                R = right_formula_robustness[window_end_pos]
                if R < L:
                    minimum_idx = window_end_pos
                    minimum_robustness = 1
                    v = R
                else:
                    minimum_idx = inf_min_idx
                    minimum_robustness = 0
                    v = L

                # Update the maximum if needed.
                if v > maximum:
                    maximum = v
                    maximum_idx = minimum_idx
                    maximum_robustness = minimum_robustness

            if maximum_robustness == 0:
                robustness[current_time_pos] = left_formula_robustness[maximum_idx]
                if return_effective_range:
                    effective_range_signal[current_time_pos] = left_formula_effective_range_signal[maximum_idx]
            else:
                robustness[current_time_pos] = right_formula_robustness[maximum_idx]
                if return_effective_range:
                    effective_range_signal[current_time_pos] = right_formula_effective_range_signal[maximum_idx]

        return robustness, effective_range_signal if return_effective_range else None

class Global(STL):

    def __init__(self, lower_time_bound, upper_time_bound, formula):
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.formulas = [formula]
        self.range = None if self.formulas[0].range is None else self.formulas[0].range.copy()
        self.horizon = self.upper_time_bound + self.formulas[0].horizon

    def eval(self, traces, return_effective_range=True):
        formula_robustness, formula_effective_range_signal = self.formulas[0].eval(traces, return_effective_range)
        robustness = np.empty(shape=(len(formula_robustness)))
        if return_effective_range and formula_effective_range_signal is not None:
            effective_range_signal = np.empty(shape=(len(formula_effective_range_signal), 2))

        # We save the previously found positions as most often we use integer
        # timestamps and evenly sampled signals, so the correct answer is
        # directly previous position - 1. This has a huge speed benefit.
        prev_lower_bound_pos = len(traces.timestamps) - 1
        prev_upper_bound_pos = len(traces.timestamps) - 1
        window = Window(formula_robustness)
        for current_time_pos in range(len(traces.timestamps) - 1, -1, -1):
            # Lower and upper times for the current time.
            lower_bound = traces.timestamps[current_time_pos] + self.lower_time_bound
            upper_bound = traces.timestamps[current_time_pos] + self.upper_time_bound

            # Find the corresponding positions in timestamps.
            # Lower bound.
            if lower_bound > traces.timestamps[-1]:
                lower_bound_pos = len(traces.timestamps)
            elif traces.timestamps[prev_lower_bound_pos - 1] == lower_bound:
                lower_bound_pos = prev_lower_bound_pos - 1
            else:
                lower_bound_pos = traces.search_time_index(lower_bound, start=current_time_pos)
                    # TODO: This should never happen except for floating point
                    # inaccuracies. We now raise an exception as otherwise the
                    # user gets unexpected behavior.
                if lower_bound_pos < 0:
                    raise Exception(
                        f"No timestamp '{lower_bound}' found even though it should exist."
                    )
            # Upper bound.
            if upper_bound > traces.timestamps[-1]:
                upper_bound_pos = len(traces.timestamps) - 1
            elif traces.timestamps[prev_upper_bound_pos - 1] == upper_bound:
                upper_bound_pos = prev_upper_bound_pos - 1
            else:
                upper_bound_pos = traces.search_time_index(upper_bound, start=lower_bound_pos)
                    # See above.
                if upper_bound_pos < 0:
                    raise Exception(
                        f"No timestamp '{upper_bound}' found even though it should exist."
                    )

            # Slide a window corresponding to the indices and find the index of
            # the minimum. The value -1 signifies that the window was out of
            # scope.
            min_idx = window.update(lower_bound_pos, upper_bound_pos + 1)
            if min_idx == -1:
                # The window was out of scope. We guess here that the
                # robustness is the final robustness value observed. We don't
                # know the future, but this is our last observation.
                min_idx = len(traces.timestamps) - 1

            robustness[current_time_pos] = formula_robustness[min_idx]
            if return_effective_range and formula_effective_range_signal is not None:
                effective_range_signal[current_time_pos] = formula_effective_range_signal[min_idx]

            prev_lower_bound_pos = prev_lower_bound_pos
            prev_upper_bound_pos = prev_upper_bound_pos

        return robustness, effective_range_signal if return_effective_range and formula_effective_range_signal is not None else None

class Finally(STL):

    def __init__(self, lower_time_bound, upper_time_bound, formula):
        self.upper_time_bound = upper_time_bound
        self.lower_time_bound = lower_time_bound
        self.formulas = [formula]
        self.formula_robustness = Not(Global(self.lower_time_bound, self.upper_time_bound, Not(self.formulas[0])))
        self.range = self.formula_robustness.range.copy() if self.formula_robustness.range is not None else None
        self.horizon = self.upper_time_bound + self.formulas[0].horizon

    def eval(self, traces, return_effective_range=True):
        return self.formula_robustness.eval(traces, return_effective_range)

class Not(STL):

    def __init__(self, formula):
        self.formulas = [formula]
        if self.formulas[0].range is None:
            self.range = None
        else:
            self.range = [-1*self.formulas[0].range[1], -1*self.formulas[0].range[0]]

        self.horizon = self.formulas[0].horizon

    def eval(self, traces, return_effective_range=True):
        formula_robustness, formula_effective_range_signal = self.formulas[0].eval(traces, return_effective_range)
        if return_effective_range and formula_effective_range_signal is not None:
            np.multiply(-1, formula_effective_range_signal, out=formula_effective_range_signal)
            effective_range_signal = np.roll(formula_effective_range_signal, -1, axis=1)
        else:
            effective_range_signal = None

        return np.multiply(-1, formula_robustness, out=formula_robustness), effective_range_signal

class Implication(STL):

    def __init__(self, left_formula, right_formula):
        self.formulas = [left_formula, right_formula]
        self.formula_robustness = Or(Not(self.formulas[0]), self.formulas[1])

        if self.formulas[0].range is None or self.formulas[1].range is None:
            self.range = None
        else:
            self.range = self.formula_robustness.range.copy() if self.formula_robustness.range is not None else None

        self.horizon = max(self.formulas[0].horizon, self.formulas[1].horizon)

    def eval(self, traces, return_effective_range=True):
        return self.formula_robustness.eval(traces, return_effective_range)

class Or(STL):

    def __init__(self, *args, nu=None):
        self.formulas = list(args)
        # We save the actual definition in another attribute in order to work
        # correctly with nonassociativity and the parser.
        self.formula_robustness = Not(And(*[Not(f) for f in self.formulas]))
        self.range = self.formula_robustness.range.copy() if self.formula_robustness.range is not None else None
        self.horizon = self.formula_robustness.horizon

    def eval(self, traces, return_effective_range=True):
        return self.formula_robustness.eval(traces, return_effective_range)

class And(STL):

    def __init__(self, *args, nu=None):
        self.formulas = list(args)
        self.nu = nu

        if self.nu is not None and self.nu <= 0:
            raise ValueError("The nu parameter must be positive.")

        self.horizon = max(f.horizon for f in self.formulas)

        A = [f.range[0] if f.range is not None else None for f in self.formulas]
        B = [f.range[1] if f.range is not None else None for f in self.formulas]
        self.range = None if None in A or None in B else [min(A), min(B)]

    def eval(self, traces, return_effective_range=True):
        if self.nu is None:
            return self._eval_traditional(traces, return_effective_range)
        else:
            return self._eval_alternative(traces, self.nu, return_effective_range)

    def _eval_traditional(self, traces, return_effective_range):
        """This is the usual and."""

        # Evaluate the robustness of all subformulas and save the robustness
        # signals into one 2D array.
        M = len(self.formulas)
        ranges_initialized = False
        for i in range(M):
            formula_robustness, formula_range_signal = self.formulas[i].eval(traces, return_effective_range)
            if i == 0:
                rho = np.empty(shape=(M, len(formula_robustness)))
                if formula_range_signal is not None:
                    bounds = np.empty(shape=(M, formula_range_signal.shape[0], 2))
                    ranges_initialized = True

            rho[i,:] = formula_robustness
            if ranges_initialized:
                if formula_range_signal is not None:
                    bounds[i,:] = formula_range_signal
                else:
                    del bounds
                    ranges_initialized = False

        if ranges_initialized:
            min_idx = np.argmin(rho, axis=0)
            return rho[min_idx,np.arange(len(min_idx))], bounds[min_idx,np.arange(len(min_idx))]
        else:
            return np.min(rho, axis=0), None

    def _eval_alternative(self, traces, nu, return_effective_range=True):
        """This is the alternative and."""

        # Evaluate the robustness of all subformulas and save the robustness
        # signals into one 2D array.
        M = len(self.formulas)
        ranges_initialized = False
        for i in range(M):
            formula_robustness, formula_range_signal = self.formulas[i].eval(traces, return_effective_range)
            if i == 0:
                rho = np.empty(shape=(M, len(formula_robustness)))
                if return_effective_range and formula_range_signal is not None:
                    bounds = np.empty(shape=(M, formula_range_signal.shape[0], 2))
                    ranges_initialized = True

            rho[i,:] = formula_robustness
            if ranges_initialized:
                if formula_range_signal is not None:
                    bounds[i,:] = formula_range_signal
                else:
                    del bounds
                    ranges_initialized = False

        rho_argmin = np.argmin(rho, axis=0)

        robustness = np.empty(shape=(len(rho_argmin)))
        if ranges_initialized:
            range_signal = np.empty(shape=(len(rho_argmin), 2))
        for i in range(len(rho_argmin)):
            j = rho_argmin[i]

            if rho[j,i] == 0:
                robustness[i] = 0

                if ranges_initialized:
                    range_signal[i,0] = 0
                    range_signal[i,1] = 0
            else:
                # TODO: Would it make sense to compute rho_tilde for the complete
                # x-axis in advance? Does it use potentially much memory for no
                # speedup?
                rho_tilde = rho[:,i]/rho[j,i] - 1
                if rho[j,i] < 0:
                    weights = np.exp(np.multiply(nu, rho_tilde))
                    weighted = np.multiply(rho[j,i], np.exp(rho_tilde))
                elif rho[j,i] > 0:
                    weights = np.exp(np.multiply(-nu, rho_tilde))
                    weighted = rho[:,i]

                robustness[i] = np.dot(weights, weighted) / np.sum(weights)

                if ranges_initialized:
                    range_signal[i,0] = np.dot(weights, bounds[:,i,0]) / np.sum(weights)
                    range_signal[i,1] = np.dot(weights, bounds[:,i,1]) / np.sum(weights)

        return robustness, range_signal if ranges_initialized else None

# TODO: Implement these.
StrictlyLessThan = LessThan
StrictlyGreaterThan = GreaterThan

