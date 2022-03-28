import time
import math

class Budget:

    def __init__(self):
        self.budget_ids = ["executions", "execution_time", "generation_time"]
        self.budget_values = {name:0 for name in self.budget_ids}
        self.budget_values["wall_time"] = 0
        self.budget_threshold = {name:math.inf for name in self.budget_ids}
        self.budget_threshold["wall_time"] = math.inf
        self.wall_time_start = -1

    def update_threshold(self, budget_threshold):
        # We setup the wall time counter here if it has not been started yet.
        if self.wall_time_start < 0:
            self.wall_time_start = time.perf_counter()

        # Use specified values, infinite budget for nonspecified budgets.
        for name in self.budget_ids:
            self.budget_threshold[name] = budget_threshold[name] if name in budget_threshold else math.inf

    def remaining(self):
        return min(self.used().values()) > 0

    def used(self):
        result = {name:max(0, 1 - self.budget_values[name]/self.budget_threshold[name]) for name in self.budget_ids}
        result["wall_time"] = max(0, 1 - (time.perf_counter() - self.wall_time_start)/self.budget_threshold["wall_time"])

        return result

    def consume(self, budget_id, *args, **kwargs):
        """Consume a budget, i.e., add the given value (default 1) to the used
        budget corresponding to the budget id.

        It is assumed that this method is not called on consumable budgets like
        wall time. No checks are made to prevent this.

        If the budget id is not recognized, nothing is done."""

        if budget_id in self.budget_ids:
            value = args[0] if len(args) > 0 else 1
            self.budget_values[budget_id] += value

