from stgem.algorithm.ogan.algorithm import OGAN
from stgem.algorithm.ogan.model import OGAN_Model
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.algorithm.wogan.algorithm import WOGAN
from stgem.algorithm.wogan.model import WOGAN_Model
from stgem.generator import Search
from stgem.objective_selector import ObjectiveSelectorAll

mode = "stop_at_first_objective"

# Running the model requires Deep Learning Toolbox in Matlab.

ogan_parameters = {"fitness_coef": 0.95,
                   "train_delay": 1,
                   "N_candidate_tests": 1,
                   "reset_each_training": True
                   }

ogan_model_parameters = {
    "convolution": {
        "optimizer": "Adam",
        "discriminator_lr": 0.001,
        "discriminator_betas": [0.9, 0.999],
        "generator_lr": 0.0001,
        "generator_betas": [0.9, 0.999],
        "noise_batch_size": 8192,
        "generator_loss": "MSE,Logit",
        "discriminator_loss": "MSE,Logit",
        "generator_mlm": "GeneratorNetwork",
        "generator_mlm_parameters": {
            "noise_dim": 20,
            "hidden_neurons": [128,128,128],
            "hidden_activation": "leaky_relu"
        },
        "discriminator_mlm": "DiscriminatorNetwork1dConv",
        "discriminator_mlm_parameters": {
            "feature_maps": [16, 16],
            "kernel_sizes": [[2,2], [2,2]],
            "convolution_activation": "leaky_relu",
            "dense_neurons": 128
        },
        "train_settings_init": {"epochs": 2, "discriminator_epochs": 15, "generator_batch_size": 32},
        "train_settings": {"epochs": 1, "discriminator_epochs": 15, "generator_batch_size": 32}
    }
}

def build_specification(selected_specification, mode=None):
    """Builds a specification object and a SUT for the selected specification.
    In addition, returns if scaling and strict horizon check should be used for
    the specification. A previously created SUT can be passed as an argument,
    and then it will be reused."""

    # Notice that this only implements the Instance 2 version of the problem where
    # the input signal is split into exactly 20 segments.

    sut_parameters = {"model_file": "sc/run_steamcondenser",
                      "input_type": "piecewise constant signal",
                      "output_type": "signal",
                      "inputs": ["FS"],
                      "outputs": ["T", "FCW", "Q", "PRESSURE"],
                      "input_range": [[3.99, 4.01]],
                      "output_range": [None, None, None, [86, 90]],
                      "simulation_time": 35,
                      "time_slices": [1.75],
                      "sampling_step": 0.5
                     }

    if selected_specification != "SC":
        raise Exception(f"Unknown specification '{selected_specification}'.")

    specifications = ["always[30,35](87 <= PRESSURE and PRESSURE <= 87.5)"]
    strict_horizon_check = True
    return sut_parameters, specifications, strict_horizon_check

def objective_selector_factory():
    objective_selector = ObjectiveSelectorAll()

def get_objective_selector_factory():
    return objective_selector_factory

def step_factory():
    mode = "stop_at_first_objective"

    step_1 = Search(mode=mode,
                    budget_threshold={"executions": 75},
                    algorithm=Random(model_factory=(lambda: Uniform()))
                   )
    step_2 = Search(mode=mode,
                    budget_threshold={"executions": 300},
                    algorithm=OGAN(model_factory=(lambda: OGAN_Model(ogan_model_parameters["convolution"])), parameters=ogan_parameters)
                    #algorithm=WOGAN(model_factory=(lambda: WOGAN_Model()))
                   )
    return [step_1, step_2]

def get_step_factory():
    return step_factory

