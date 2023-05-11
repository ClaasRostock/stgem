import time

import numpy as np

class TestRepository:

    def __init__(self):
        self._tests = []               # SUTInput objects.
        self._outputs = []             # SUTOutput objects.
        self._objectives = []          # Objectives for the SUTOutput.
        self._performance_records = [] # PerformanceRecord objects.

        self.unfinalized = False
        self.current_test = -1
        self.tests = 0
        self.minimum_objective = float("inf")

    @property
    def indices(self):
        return list(range(self.tests))

    def new_record(self):
        self._performance_records.append({})
        self.unfinalized = True
        self.current_test += 1
        return PerformanceRecordHandler(self._performance_records[-1])

    def record_input(self, sut_input):
        if not self.unfinalized: return
        if len(self._tests) <= self.current_test:
            self._tests.append(sut_input)
        else:
            self._tests[-1] = sut_input

    def record_output(self, sut_output):
        if not self.unfinalized: return
        if len(self._outputs) <= self.current_test:
            self._outputs.append(sut_output)
        else:
            self._outputs[-1] = sut_output

    def record_objectives(self, objectives):
        if not self.unfinalized: return
        if len(self._objectives) <= self.current_test:
            self._objectives.append(objectives)
        else:
            self._objectives[-1] = objectives

        # TODO: This does not work correctly if this method is called twice.
        # Save minimum objective component observed.
        m = min(objectives)
        if m < self.minimum_objective:
            self.minimum_objective = m

    def discard_record(self):
        pass

    def finalize_record(self):
        self.unfinalized = False
        self.tests += 1

        return self.current_test

    def get(self, *args, **kwargs):
        """Return test, its output from the SUT, and the computed objective for
        the given test indices. If no arguments are given, all tests are
        returned. If there is a single argument and it is a list-like object,
        the results are returned for all indices in the object.

        By default, we return only results for tests that have been
        successfully executed on the SUT, that is, only results for tests for
        which sut_output.error is not None are returned. All results including
        the failed executions can be obtained by passing the keyword argument
        include_all=True."""

        return_list = True

        if not args:
            # Return all tests.
            args = self.indices

        if len(args) == 1:
            if isinstance(args[0], (int, np.integer)):
                # Return a single test.
                return_list = False
                args = [args[0]]
            else:
                args = args[0]

        # Return multiple tests.
        include_all = "include_all" in kwargs and kwargs["include_all"]
        X = []
        Z = []
        Y = []
        for i in args:
            if i >= self.tests or (i < 0 and i < -self.tests):
                raise IndexError(f"Index {i} out of bounds.")
            if self._outputs[i].error is not None and not include_all: continue
            X.append(self._tests[i])
            Z.append(self._outputs[i])
            Y.append(self._objectives[i])

        if not return_list:
            if not X:
                raise Exception(
                    f"The test with index {args[0]} failed to execute, so it is not returned. Set include_all=True to obtain it."
                )
            X = X[0]
            Z = Z[0]
            Y = Y[0]

        return X, Z, Y

    def performance(self, test_idx):
        return PerformanceRecordHandler(self._performance_records[test_idx])

class PerformanceRecordHandler:

    def __init__(self, record):
        self._record = record
        self.timers = {}

    def timer_start(self, timer_id):
        if timer_id in self.timers and self.timers[timer_id] is not None:
            raise Exception(f"Restarting timer '{timer_id}' without resetting.")

        self.timers[timer_id] = time.perf_counter()

    def timer_reset(self, timer_id):
        if timer_id not in self.timers:
            raise Exception(f"No timer '{timer_id}' to be reset.")
        if self.timers[timer_id] is None:
            raise Exception(f"Timer '{timer_id}' already reset.")

        time_elapsed = time.perf_counter() - self.timers[timer_id]
        self.timers[timer_id] = None

        return time_elapsed

    def timers_hold(self):
        for timer_id, t in self.timers.items():
            if t is not None:
                self.timers[timer_id] = time.perf_counter() - t

    def timers_resume(self):
        self.timers_hold()

    def obtain(self, performance_id):
        if performance_id not in self._record:
            raise Exception(f"No record with identifier '{performance_id}'.")
        return self._record[performance_id]

    def record(self, performance_id, value):
        self._record[performance_id] = value

