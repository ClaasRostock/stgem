#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

class ObjectiveSelector:
    def __init__(self):
        self.parameters = {}
        self.dim = 0

    def setup(self, objectives):
        self.dim = len(objectives)

    def __getattr__(self, name):
        if "parameters" in self.__dict__ and name in self.parameters:
            return self.parameters.get(name)

        raise AttributeError(name)

    def select_all(self):
        return list(range(self.dim))

    def select(self):
        raise NotImplementedError()

    def update(self, idx):
        return

class ObjectiveSelectorAll(ObjectiveSelector):
    """
    Model selector which ignores everything and just returns all models.
    """

    def select(self):
        return self.select_all()

class ObjectiveSelectorMAB(ObjectiveSelector):
    """
    Simple multi-armed bandit inspired model selector which uses the success
    frequency of obtaining the best objective component to randomly select one
    model. A warm-up period can be defined where all models are returned.
    """

    def __init__(self, warm_up=30):
        super().__init__()
        self.parameters["warm_up"] = warm_up
        self.total_calls = 0
        self.model_successes = []

    def setup(self, objectives):
        super().setup(objectives)
        self.model_successes = [0 for _ in range(self.dim)]

    def select(self):
        if self.total_calls <= self.warm_up:
            return self.select_all()
        p = [s / self.total_calls for s in self.model_successes]
        return [np.random.choice(range(0, self.dim), p=p)]

    def update(self, idx):
        try:
            self.model_successes[idx] += 1
        except IndexError:
            raise Exception(f"No model with index {idx}.")
        self.total_calls += 1
