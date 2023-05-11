import importlib, os, sys

import click

# Some imports need to be done inside functions for the environment variable
# setup to take effect.
from stgem.algorithm.ogan.algorithm import OGAN
from stgem.algorithm.ogan.model import OGAN_Model
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.algorithm.wogan.algorithm import WOGAN
from stgem.algorithm.wogan.model import WOGAN_Model
from stgem.generator import Search
from stgem.objective import FalsifySTL
from stgem.objective_selector import ObjectiveSelectorAll

from sut import OdroidSUT

mode = "stop_at_first_objective"

ogan_parameters = {"fitness_coef": 0.95,
                   "train_delay": 1,
                   "N_candidate_tests": 1,
                   "reset_each_training": True
                   }

ogan_model_parameters = {
    "dense": {
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
        "discriminator_mlm": "DiscriminatorNetwork",
        "discriminator_mlm_parameters": {
            "hidden_neurons": [128,128,128],
            "hidden_activation": "leaky_relu"
        },
        "train_settings_init": {"epochs": 1, "discriminator_epochs": 15, "generator_batch_size": 32},
        "train_settings": {"epochs": 1, "discriminator_epochs": 15, "generator_batch_size": 32}
    }
}

def get_seed_factory(init_seed=0):
    def seed_generator(init_seed):
        c = init_seed
        while True:
            yield c
            c += 1

    g = seed_generator(init_seed)
    return lambda: next(g)

def get_experiment_factory(N, init_seed, callback=None):
    from stgem.generator import STGEM

    def step_factory():
        mode = "stop_at_first_objective"
        #mode = "exhaust_budget"

        step_1 = Search(mode=mode,
                        budget_threshold={"executions": 75},
                        algorithm=Random(model_factory=(lambda: Uniform()))
                       )      
        step_2 = Search(mode=mode,
                        budget_threshold={"executions": 300},
                        algorithm=OGAN(model_factory=(lambda: OGAN_Model(ogan_model_parameters["dense"])), parameters=ogan_parameters),
                        #algorithm=WOGAN(model_factory=(lambda: WOGAN_Model())),
                        results_include_models=False
                       )
        #steps = [step_1]
        steps = [step_1, step_2]
        return steps

    def generator_factory():
        nu = None
        #nu = 1
        specification = "POWER < 6"

        sut = OdroidSUT(parameters={"data_file": "odroid.npy"})

        ranges = {}
        for n in range(sut.idim):
            ranges["i{}".format(n)] = sut.input_range[n]
        for n in range(sut.odim):
            ranges[sut.outputs[n]] = sut.output_range[n]

        return STGEM(description="Odroid",
                     sut=sut,
                     objectives=[FalsifySTL(specification=specification, ranges=ranges, scale=True, strict_horizon_check=False, nu=nu)],
                     objective_selector=ObjectiveSelectorAll(),
                     steps=step_factory())

    from stgem.experiment import Experiment

    def experiment_factory():
        return Experiment(N=N,
                          stgem_factory=generator_factory,
                          seed_factory=get_seed_factory(init_seed),
                          result_callback=callback)

    return experiment_factory

@click.command()
@click.argument("n", type=int)
@click.argument("init_seed", type=int)
@click.argument("identifier", type=str, default="")
def main(n, init_seed, identifier):
    N = n

    N_workers = 5

    # Disable CUDA if multiprocessing is used.
    if N > 1 and N_workers > 1:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    def callback(idx, result, done):
        path = os.path.join("..", "..", "output", "Odroid")
        time = str(result.timestamp).replace(" ", "_")
        file_name = "{}_{}.pickle.gz".format(
            f"Odroid_{identifier}" if identifier is not None else "", time
        )
        os.makedirs(path, exist_ok=True)
        result.dump_to_file(os.path.join(path, file_name))

    experiment = get_experiment_factory(N, init_seed, callback=callback)()

    use_gpu = N == 1 or N_workers == 1
    experiment.run(N_workers=min(N, N_workers), silent=False, use_gpu=use_gpu)

if __name__ == "__main__":
    main()

