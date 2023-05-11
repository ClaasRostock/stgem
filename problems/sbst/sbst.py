import os

import click

import numpy as np

from stgem.generator import STGEM, Search, Load
from stgem.algorithm import Model
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform, LHS
from stgem.algorithm.wogan.algorithm import WOGAN
from stgem.algorithm.wogan.model import WOGAN_Model
from stgem.budget import Budget
from stgem.experiment import Experiment
from stgem.objective import Objective
from stgem.objective_selector import ObjectiveSelectorAll

from sut import SBSTSUT, SBSTSUT_validator

class CustomBudget(Budget):
    """A custom budget that adds a new budget 'total_GTS' time which tracks the
    total of generation time, training time, and simulated time."""

    def __init__(self):
        super().__init__()
        self.quantities["simulated_time"] = 0
        self.budgets["simulated_time"] = lambda quantities: quantities["simulated_time"]
        self.budgets["total_GTS_time"] = lambda quantities: quantities["generation_time"] + quantities["training_time"] + quantities["simulated_time"]

    def _consume_on_output(self, output):
        self.quantities["simulated_time"] += output.features["simulation_time"]

class UniformDependent(Model):
    """Model for uniformly random search which does not select components
    independently."""

    def generate_test(self):
        # The components of the actual test are curvature values in the input
        # range (default [-0.07, 0.07]). Here we do not choose the components
        # of a test independently in [-1, 1] but we do as in the Frenetic
        # algorithm where the next component is in the range of the previous
        # value +- 0.05 (in the scale [-0.07, 0.07]).

        test = np.zeros(self.search_space.input_dimension)
        test[0] = np.random.uniform(-1, 1)
        for i in range(1, len(test)):
            test[i] = max(-1, min(1, test[i - 1] + (0.05/0.07) * np.random.uniform(-1, 1)))

        return test

class MaxOOB(Objective):
    """Objective which picks the maximum M from the first output signal and
    returns 1-M for minimization."""

    def __call__(self, t, r):
        return 1 - max(r.outputs[0])

class ScaledDistance(Objective):
    """Objective based on distance to the left and right edges of the lane."""

    def __call__(self, t, r):
        # alpha is a number such that -alpha distance to the right of the right
        # edge of the lane corresponds to a falsification with falsification
        # threshold of BOLP < 0.95. The value is obtained experimentally from
        # 1000 random test executions. The same holds symmetrically from the
        # left. In fact, the minimum for the left distance was -2.03 and -1.69
        # for the right distance, so this is a sort of compromise.
        alpha = 1.70
        L = (np.clip(r.outputs[1], -alpha, 2) + alpha) / (2 + alpha)
        R = (np.clip(r.outputs[2], -alpha, 2) + alpha) / (2 + alpha)

        return min(np.min(L), np.min(R))

# These are the settings used to get the results of "Wasserstein Generative
# Adversarial Networks for Online Test Generation for Cyber Physical Systems".
mode = "exhaust_budget"

sut_parameters = {
    "beamng_home": "C:/BeamNG/BeamNG.tech.v0.24.0.1",
    "curvature_points": 5,
    "curvature_range": 0.07,
    "step_size": 15,
    "map_size": 200,
    "max_speed": 70.0
}

wogan_parameters = {
    "bins": 10,
    "wgan_batch_size": 32,
    "fitness_coef": 0.95,
    "train_delay": 3,
    "N_candidate_tests": 1,
    "shift_function": "linear",
    "shift_function_parameters": {"initial": 0, "final": 3},
}

analyzer_mlm_parameters = {
    "dense": {
        "hidden_neurons": [32,32],
        "layer_normalization": False
    },
    "convolution": {
        "feature_maps": [16, 16],
        "kernel_sizes": [[2, 2], [2, 2]],
        "convolution_activation": "leaky_relu",
        "dense_neurons": 128
    }
}

wogan_model_parameters = {
    "critic_optimizer": "Adam",
    "critic_lr": 0.00005,
    "critic_betas": [0, 0.9],
    "generator_optimizer": "Adam",
    "generator_lr": 0.00005,
    "generator_betas": [0, 0.9],
    "noise_batch_size": 32,
    "gp_coefficient": 10,
    "eps": 1e-6,
    "report_wd": True,
    "analyzer": "Analyzer_NN",
    "analyzer_parameters": {
        "optimizer": "Adam",
        "lr": 0.001,
        "betas": [0, 0.9],
        "loss": "MSE,logit",
        "l2_regularization_coef": 0.01,
        "analyzer_mlm": "AnalyzerNetwork",
        #"analyzer_mlm": "AnalyzerNetwork_conv",
        "analyzer_mlm_parameters": analyzer_mlm_parameters["dense"],
        #"analyzer_mlm_parameters": analyzer_mlm_parameters["convolution"],
    },
    "generator_mlm": "GeneratorNetwork",
    "generator_mlm_parameters": {
        "noise_dim": 10,
        "hidden_neurons": [128, 128],
        "hidden_activation": "relu",
        "batch_normalization": True,
        "layer_normalization": False
    },
    "critic_mlm": "CriticNetwork",
    "critic_mlm_parameters": {
        "hidden_neurons": [128, 128],
        "hidden_activation": "leaky_relu",
    },
    "train_settings_init": {
        "epochs": 3,
        "analyzer_epochs": 20,
        "critic_steps": 5,
        "generator_steps": 1
    },
    "train_settings": {
        "epochs": 2,
        "analyzer_epochs": 10,
        "critic_steps": 5,
        "generator_steps": 1
    },
}

@click.command()
@click.argument("n", type=int)
@click.argument("init_seed", type=int)
@click.argument("identifier", type=str, default="")
def main(n, init_seed, identifier):
    N = n

    # Share SUT objects.
    if identifier.startswith("DAVE2"):
        sut_parameters["dave2_model"] = "dave2/self-driving-car-010-2020.h5"
        sut_parameters["max_speed"] = 35.0
    sbst_sut = SBSTSUT(sut_parameters)

    def stgem_factory():
        nonlocal sbst_sut, identifier

        load_pregenerated_tests = True
        pregenerated_test_file = os.path.join("..", "..", "output", "SBST", "1000_2022-11-10.pickle.gz")

        budget_thresholds = [{"total_GTS_time": 900}, {"total_GTS_time": 3600}]

        if identifier in ["NEW_DISTANCE", "DAVE2_NEW_DISTANCE"]:
            objective = ScaledDistance()
        else:
            objective = MaxOOB()

        if load_pregenerated_tests:
            first_step = Load(
                file_name=pregenerated_test_file,
                mode="random",
                load_range=75,
                recompute_objective=True
            )
        else:
            first_step = Search(
                mode=mode,
                budget_threshold=budget_thresholds[0],
                algorithm=Random(model_factory=(lambda: UniformDependent()))
            )

        generator = STGEM(
            description="SBST 2022 BeamNG.tech simulator",
            sut=sbst_sut,
            budget=CustomBudget(),
            objectives=[objective],
            objective_selector=ObjectiveSelectorAll(),
            steps=[
                first_step,
                Search(mode=mode,
                       budget_threshold=budget_thresholds[1],
                       algorithm=WOGAN(model_factory=(lambda: WOGAN_Model(wogan_model_parameters)),
                                       parameters=wogan_parameters))
            ]
        )
        return generator

    def get_seed_factory(init_seed=0):
        def seed_generator(init_seed):
            c = init_seed
            while True:
                yield c
                c += 1

        g = seed_generator(init_seed)
        return lambda: next(g)

    def result_callback(idx, result, done):
        path = os.path.join("..", "..", "output", "sbst")
        time = str(result.timestamp).replace(" ", "_").replace(":", "")
        file_name = "SBST{}_{}_{}.pickle.gz".format(
            f"_{identifier}" if len(identifier) > 0 else "", time, idx
        )
        os.makedirs(path, exist_ok=True)
        result.dump_to_file(os.path.join(path, file_name))

    experiment = Experiment(N, stgem_factory, get_seed_factory(init_seed), result_callback=result_callback)
    experiment.run(N_workers=1)

if __name__ == "__main__":
    main()
