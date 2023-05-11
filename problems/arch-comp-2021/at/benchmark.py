from stgem.algorithm.ogan.algorithm import OGAN
from stgem.algorithm.ogan.model import OGAN_Model
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.algorithm.wogan.algorithm import WOGAN
from stgem.algorithm.wogan.model import WOGAN_Model
from stgem.generator import Search
from stgem.objective_selector import ObjectiveSelectorAll, ObjectiveSelectorMAB
from stgem.sut.matlab.sut import Matlab_Simulink

mode = "stop_at_first_objective"

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

def build_specification(selected_specification, mode=None):
    """Builds a specification object and a SUT for the selected specification.
    In addition, returns if scaling and strict horizon check should be used for
    the specification. A previously created SUT can be passed as an argument,
    and then it will be reused."""

    sut_parameters = {"type": "simulink",
                      "model_file": "at/Autotrans_shift",
                      "input_type": "piecewise constant signal",
                      "output_type": "signal",
                      "inputs": ["THROTTLE", "BRAKE"],
                      "outputs": ["SPEED", "RPM", "GEAR"],
                      "input_range": [[0, 100], [0, 325]],
                      "output_range": [[0, 125], [0, 4800], [0, 4]],
                      "simulation_time": 30,
                      "time_slices": [5, 5],
                      "sampling_step": 0.01
                     }

    # Some ARCH-COMP specifications have requirements whose horizon is longer than
    # the output signal for some reason. Thus strict horizon check needs to be
    # disabled in some cases.
    #
    # The requirements ATX1* and ATX2 are from "Falsification of hybrid systems
    # using adaptive probabilistic search" by Ernst et al.
    if selected_specification == "AT1":
        specification = "always[0,20](SPEED < 120)"

        specifications = [specification]
        strict_horizon_check = True
    elif selected_specification == "AT2":
        specification = "always[0,10](RPM < 4750)"

        specifications = [specification]
        strict_horizon_check = True
    elif selected_specification.startswith("AT5"):
        G = int(selected_specification[-1])
        specification = "always[0,30]( ( GEAR != {0} and (eventually[0.001,0.1](GEAR == {0})) ) -> ( eventually[0.001,0.1]( always[0,2.5](GEAR == {0}) ) ) )".format(G)

        specifications = [specification]
        strict_horizon_check = False
    elif selected_specification.startswith("AT6"):
        A = selected_specification[-1]

        def getSpecification(A):
            if A == "A":
                UB = 4
                SL = 35
            elif A == "B":
                UB = 8
                SL = 50
            else:
                UB = 20
                SL = 65
              
            return "always[0,30](RPM < 3000) -> always[0,{0}](SPEED < {1})".format(UB, SL)

        if selected_specification.endswith("ABC"):
            specification = "{} and {} and {}".format(getSpecification("A"), getSpecification("B"), getSpecification("C"))

            #specifications = [getSpecification("A"), getSpecification("B"), getSpecification("C")]
            specifications = [specification]
        else:
            specification = getSpecification(A)

            specifications = [specification]

        strict_horizon_check = True
    elif selected_specification.startswith("ATX1"):
        G = int(selected_specification[-1])
        # Only for G == 3 or G == 4.
        specification = "always[0,30]( (GEAR == {0}) -> (SPEED > 10*{0}) )".format(G)

        specifications = [specification]
        strict_horizon_check = True
    elif selected_specification == "ATX2":
        specification = "not(always[10,30]( (50 <= SPEED) and (SPEED <= 60) ))"

        specifications = [specification]
        strict_horizon_check = True
    elif selected_specification.startswith("ATX6"):
        # This is a variant of AT6 from "Falsification of Hybrid Systems Using
        # Adaptive Probabilistic Search".
        V = int(selected_specification[-1])
        if V == 1:
            V1 = 80
            V2 = 4500
            T = 30
        else:
            V1 = 50
            V2 = 2700
            T = 30

        specification = "always[0,10](SPEED < {}) or eventually[0,{}]({} < RPM)".format(V1, T, V2)

        specifications = [specification]
        strict_horizon_check = True
    else:
        raise Exception("Unknown specification '{}'.".format(selected_specification))

    return sut_parameters, specifications, strict_horizon_check

def objective_selector_factory():
    objective_selector = ObjectiveSelectorMAB(warm_up=100)

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
                    algorithm=OGAN(model_factory=(lambda: OGAN_Model(ogan_model_parameters["convolution"])), parameters=ogan_parameters),
                    #algorithm=WOGAN(model_factory=(lambda: WOGAN_Model())),
                    results_include_models=False
                   )
    return [step_1, step_2]

def get_step_factory():
    return step_factory

