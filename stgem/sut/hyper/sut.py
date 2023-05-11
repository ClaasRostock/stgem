import numpy as np

from stgem.sut import SUT, SUTOutput

"""
Notice: it is extremely important that no global or hidden state is modified
when the functions described in the 'hyperparameters' parameter are executed.
Extra care needs to be taken when machine learning models are initialized as
this often advances a random number generator.
"""

class Range:
    """Continuous range [A, B]."""

    def __init__(self, A, B):
        self.A = A
        self.B = B

    def __call__(self, x):
        # Scale from [-1, 1] to [A, B].
        return 0.5*((self.B - self.A)*x + self.A + self.B)

class Categorical:
    """Categorical variable."""

    def __init__(self, values):
        self.values = values

    def __call__(self, x):
        # We split [-1, 1] into len(self.values) parts, the first part
        # corresponds to the first variable value, second to second variable,
        # etc.
        idx = int(0.5*(x + 1)*len(self.values)) if x < 1 else len(self.values) - 1
        return self.values[idx]

class HyperParameter(SUT):

    default_parameters = {"mode": "falsification_rate",
                          "N_workers": 1}

    def __init__(self, experiment_factory, parameters=None):
        super().__init__(parameters)

        if "hyperparameters" not in self.parameters:
            raise Exception("No hyperparameters selected for optimization.")

        self.experiment_factory = experiment_factory

        self.idim = len(self.hyperparameters)
        self.input_type = "vector"
        self.output_type = "vector"

        # Check what type of thing is computed: FR etc.
        if self.mode == "falsification_rate":
            def reset():
                self.stored = []

            def callback(idx, result, done):
                """Append 1 if falsified, 0 otherwise."""

                self.stored.append(any(step.success for step in result.step_results))

            def report():
                # We return 1 - FR as we do minimization.
                return 1 - sum(1 if x else 0 for x in self.stored) / len(self.stored)

            self.reset_callback = reset
            self.stgem_result_callback = callback
            self.report = report

            self.odim = 1
        else:
            raise Exception("Unknown mode '{}'.".format(self.mode))

    def edit_generator(self, generator, test):
        for n, (hp_func, _) in enumerate(self.hyperparameters):
            hp_func(generator, test[n])

    def _execute_test(self, test):
        denormalized = np.array([hp_domain(test.inputs[n]) for n, (_, hp_domain) in enumerate(self.hyperparameters)])
        experiment = self.experiment_factory()
        experiment.generator_callback = lambda g: self.edit_generator(g, denormalized)
        experiment.result_callback = self.stgem_result_callback

        self.reset_callback()

        # We disable GPU as it often does not work well with multiprocessing.
        use_gpu = self.N_workers == 1
        experiment.run(N_workers=self.N_workers, silent=True, use_gpu=use_gpu)

        test.input_denormalized = denormalized
        return SUTOutput(np.array([self.report()]), None, None, None)

