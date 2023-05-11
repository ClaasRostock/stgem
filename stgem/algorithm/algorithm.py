"""
See Algorithm.md for detailed documentation and ideas. Remember to edit this
documentation if you make changes to Algorithm!
"""

import copy

class Algorithm:
    """Base class for all test suite generation algorithms."""

    default_parameters = {}

    def __init__(self, model_factory=None, model=None, models=None, parameters=None):
        if sum([model is not None, models is not None, model_factory is not None]) > 1:
            raise TypeError("You can provide only one of these input parameters: model_factory, model, models")
        if not models:
            models = []

        self.model = model
        self.models = models
        self.model_factory = model_factory
        self.search_space = None

        if parameters is None:
            parameters = {}

        # Merge default_parameters and parameters, the latter takes priority if a key appears in both dictionaries.
        # We would like to write the following but this is not supported in Python 3.7.
        #self.parameters = self.default_parameters | parameters
        self.parameters = parameters
        for key in self.default_parameters:
            if key not in self.parameters:
                self.parameters[key] = self.default_parameters[key]

    def setup(self, search_space, device=None, logger=None):
        """Set up an algorithm before usage.

        Args:
            search_space (SearchSpace): The search space for the algorithm
            device (pytorch, optional): CUDA device
            logger (Logger, optional):  The logger
        """

        self.search_space = search_space
        self.device = device
        self.logger = logger
        self.log = lambda msg: (self.logger("algorithm", msg) if logger is not None else None)

        # Set input dimension.
        if "input_dimension" not in self.parameters:
            self.parameters["input_dimension"] = self.search_space.input_dimension

        # Create models by cloning
        if self.model:
            self.models = []
            self.models.extend(
                copy.deepcopy(self.model)
                for _ in range(self.search_space.objectives)
            )
        # Create models by factory
        if self.model_factory:
            self.models = [self.model_factory() for _ in range(self.search_space.objectives)]

        # set up the models
        self.N_models = len(self.models)
        for m in self.models:
            m.setup(self.search_space, self.device, self.logger)

    def __getattr__(self, name):
        if "parameters" in self.__dict__ and name in self.parameters:
            return self.parameters.get(name)

        raise AttributeError(name)

    def initialize(self):
        """A Step calls this method before the first generate_test call"""

        pass

    def train(self, active_outputs, test_repository, budget_remaining):
        performance = test_repository.performance(test_repository.current_test)
        performance.timer_start("training")
        self.do_train(active_outputs, test_repository, budget_remaining)
        performance.record("training_time", performance.timer_reset("training"))

    def do_train(self, active_outputs, test_repository, budget_remaining):
        raise NotImplementedError

    def generate_next_test(self, active_outputs, test_repository, budget_remaining):
        performance = test_repository.performance(test_repository.current_test)
        performance.timer_start("generation")
        try:
            r = self.do_generate_next_test(active_outputs, test_repository, budget_remaining)
        except:
            raise
        finally:
            performance.record("generation_time", performance.timer_reset("generation"))

        return r

    def do_generate_next_test(self, active_outputs, test_repository, budget_remaining):
       raise NotImplementedError

    def finalize(self):
        """A Step calls this method after the budget has been exhausted and the
        algorithm will no longer be used."""

        pass

