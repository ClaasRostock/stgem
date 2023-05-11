import copy

"""
Currently the use_previous_rng parameter is used so that the setup method can
be called several times without the RNG being advanced. This is especially
important with hyperparameter tuning as then setup is called when
hyperparameters are changed and if the setup involves setting up machine
learning models, the initial weights or other parameters can be completely
different.

It is up to the child class to implement RNG saving and restoration.
"""

class ModelSkeleton:
    """Base class for a model skeleton. A model skeleton is a snapshot of a
    model that is frozen and stripped of all extraneous information and which
    can thus be easily pickled and completed into a full model. It can also be
    used for model inference but not for training."""

    def __init__(self, parameters):
        # This is for handling multiple inheritance.
        if parameters is not None:
            self.parameters = copy.deepcopy(parameters)

    def __getattr__(self, name):
        if "parameters" in self.__dict__ and name in self.parameters:
            return self.parameters.get(name)

        raise AttributeError(name)

    def generate_test(self, N=1):
        """Generate N random tests.

        Args:
            N (int): Number of tests to be generated.

        Returns:
            output (np.ndarray): Array of shape (N, self.search_space.input_dimension)."""

        raise NotImplementedError()

    def predict_objective(self, test):
        """Predicts the objective function value of the given tests.

        Args:
            test (np.ndarray): Array of shape (N, self.search_space.input_dimension).

        Returns:
            output (np.ndarray): Array of shape (N, 1)."""

        raise NotImplementedError()

class Model(ModelSkeleton):
    """Base class for all models. """

    default_parameters = {}

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}

        # Merge default_parameters and parameters. The latter takes priority if
        # a key appears in both dictionaries.
        # We would like to write the following but this is not supported in Python 3.7.
        #super().__init__(self.default_parameters | parameters)
        for key in self.default_parameters:
            if key not in parameters:
                parameters[key] = self.default_parameters[key]
        super().__init__(parameters)

        self.previous_rng_state = None

    def setup(self, search_space, device, logger=None, use_previous_rng=False):
        if use_previous_rng and self.previous_rng_state is None:
            raise Exception("No previous RNG state to be used.")

        self.search_space = search_space
        self.parameters["input_dimension"] = self.search_space.input_dimension
        self.device = device
        self.logger = logger
        self.log = lambda msg: (self.logger("model", msg) if logger is not None else None)

    @classmethod
    def setup_from_skeleton(cls, skeleton, search_space, device, logger=None, use_previous_rng=False):
        model = cls(skeleton.parameters)
        model.setup(search_space, device, logger, use_previous_rng)
        return cls

    def skeletonize(self):
        return ModelSkeleton(self.parameters)

    def reset(self):
        pass

    def train_with_batch(self, dataX, dataY):
        pass
