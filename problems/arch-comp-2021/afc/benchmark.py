from stgem.algorithm.ogan.algorithm import OGAN
from stgem.algorithm.ogan.model import OGAN_Model
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.algorithm.wogan.algorithm import WOGAN
from stgem.algorithm.wogan.model import WOGAN_Model
from stgem.generator import Search
from stgem.objective_selector import ObjectiveSelectorAll

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
        "train_settings_init": {"epochs": 1, "discriminator_epochs": 15, "generator_batch_size": 32},
        "train_settings": {"epochs": 1, "discriminator_epochs": 15, "generator_batch_size": 32}
    }
}

def build_specification(selected_specification, afc_mode="normal"):
    """Builds a specification object and a SUT for the selected specification.
    In addition, returns if scaling and strict horizon check should be used for
    the specification. A previously created SUT can be passed as an argument,
    and then it will be reused."""

    if afc_mode == "normal":
        throttle_range = [0, 61.2]
    elif afc_mode == "power":
        throttle_range = [61.2, 81.2]

    # Notice that the output MODE is never used in the requirements.
    sut_parameters = {"model_file": "afc/run_powertrain",
                      "init_model_file": "afc/init_powertrain",
                      "input_type": "piecewise constant signal",
                      "output_type": "signal",
                      "inputs": ["THROTTLE", "ENGINE"],
                      "outputs": ["MU", "MODE"],
                      "input_range": [throttle_range, [900, 1100]],
                      "output_range": [[-1, 1], [0, 1]],
                      "simulation_time": 50,
                      "time_slices": [5, 50],
                      "sampling_step": 0.01
                     }

    # Some ARCH-COMP specifications have requirements whose horizon is longer than
    # the output signal for some reason. Thus strict horizon check needs to be
    # disabled in some cases.
    if selected_specification == "AFC27":
        E = 0.1 # Used in Ernst et al.
        #E = 0.05 # Used in ARCH-COMP 2021.
        rise = f"(THROTTLE < 8.8) and (eventually[0,{E}](THROTTLE > 40.0))"
        fall = f"(THROTTLE > 40.0) and (eventually[0,{E}](THROTTLE < 8.8))"
        specification = (
            f"always[11,50](({rise} or {fall}) -> always[1,5](|MU| < 0.008))"
        )

        specifications = [specification]
        strict_horizon_check = False
    elif selected_specification == "AFC29":
        gamma = 0.007
        specification = "always[11,50](|MU| < 0.007)"

        specifications = [specification]
        strict_horizon_check = True
    else:
        raise Exception(f"Unknown specification '{selected_specification}'.")

    return sut_parameters, specifications, strict_horizon_check

def objective_selector_factory():
    return ObjectiveSelectorAll()

def get_objective_selector_factory():
    return objective_selector_factory

def step_factory():
    mode = "stop_at_first_objective"
    #mode = "exhaust_budget"

    step_1 = Search(mode=mode,
                    budget_threshold={"executions": 75},
                    algorithm=Random(model_factory=(lambda: Uniform()))
                   )
    step_2 = Search(mode=mode,
                    budget_threshold={"executions": 300},
                    algorithm=OGAN(model_factory=(lambda: OGAN_Model(ogan_model_parameters["convolution"])), parameters=ogan_parameters)
                    #algorithm=WOGAN(model_factory=(lambda: WOGAN_Model())
                   )
    return [step_1, step_2]

def get_step_factory():
    return step_factory

