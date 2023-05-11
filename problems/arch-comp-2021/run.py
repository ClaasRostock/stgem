import importlib, os, sys
from stgem.sut.matlab.sut import Matlab, Matlab_Simulink

import click

# Some imports need to be done inside functions for the environment variable
# setup to take effect.
from stgem.objective import FalsifySTL

def get_generator_factory(description, sut_factory, objective_factory, objective_selector_factory, step_factory):
    from stgem.generator import STGEM

    def generator_factory():
        return STGEM(description=description,
                     sut=sut_factory(),
                     objectives=objective_factory(),
                     objective_selector=objective_selector_factory(),
                     steps=step_factory())

    return generator_factory

def get_seed_factory(init_seed=0):
    def seed_generator(init_seed):
        c = init_seed
        while True:
            yield c
            c += 1

    g = seed_generator(init_seed)
    return lambda: next(g)

def get_sut_objective_factory(benchmark_module, selected_specification, mode):
    sut_parameters, specifications, strict_horizon_check = benchmark_module.build_specification(selected_specification, mode)

    if "type" in sut_parameters and sut_parameters["type"] == "simulink":
        sut = Matlab_Simulink(sut_parameters)
    else:
        sut = Matlab(sut_parameters)

    ranges = {}
    for n in range(len(sut_parameters["input_range"])):
        ranges[sut_parameters["inputs"][n]] = sut_parameters["input_range"][n]
    for n in range(len(sut_parameters["output_range"])):
        ranges[sut_parameters["outputs"][n]] = sut_parameters["output_range"][n]

    def sut_factory():
        # Return the already instantiated SUT many times as Matlab uses a lot
        # of memory.
        return sut

    def objective_factory():
        nu = None
        #nu = 1
        return [FalsifySTL(specification=specification, ranges=ranges, scale=True, strict_horizon_check=strict_horizon_check, nu=nu) for specification in specifications]

    return sut_factory, objective_factory

def get_experiment_factory(N, benchmark_module, selected_specification, mode, init_seed, callback=None):
    sut_factory, objective_factory = get_sut_objective_factory(benchmark_module, selected_specification, mode)

    from stgem.experiment import Experiment

    def experiment_factory():
        return Experiment(N=N,
                          stgem_factory=get_generator_factory("", sut_factory, objective_factory, benchmark_module.get_objective_selector_factory(), benchmark_module.get_step_factory()),
                          seed_factory=get_seed_factory(init_seed),
                          result_callback=callback)

    return experiment_factory

benchmarks = ["AFC", "AT", "CC", "F16", "NN", "SC"]
descriptions = {
        "AFC": "Fuel Control of an Automotive Powertrain",
        "AT":  "Automatic Transmission",
        "CC":  "Chasing Cars",
        "F16": "Aircraft Ground Collision Avoidance System",
        "NN":  "Neural-Network Controller",
        "SC":  "Steam Condenser with Recurrent Neural Network Controller"
}
specifications = {
        "AFC": ["AFC27", "AFC29"],
        "AT":  ["AT1", "AT2", "AT51", "AT52", "AT53", "AT54", "AT6A", "AT6B", "AT6C", "AT6ABC", "ATX13", "ATX14", "ATX1", "ATX2", "ATX61", "ATX62"],
        "CC":  ["CC1", "CC2", "CC3", "CC4", "CC5", "CCX"],
        "F16": ["F16"],
        "NN":  ["NN", "NNX"],
        "SC":  ["SC"]
}
N_workers = {
        "AFC": 3,
        "AT": 3,
        "CC": 4,
        "F16": 2,
        "NN": 3,
        "SC": 2
}

@click.command()
@click.argument("selected_benchmark", type=click.Choice(benchmarks, case_sensitive=False))
@click.argument("selected_specification", type=str)
@click.argument("mode", type=str, default="")
@click.argument("n", type=int)
@click.argument("init_seed", type=int)
@click.argument("identifier", type=str, default="")
def main(selected_benchmark, selected_specification, mode, n, init_seed, identifier):
    N = n

    # Disable CUDA if multiprocessing is used.
    if N > 1 and N_workers[selected_benchmark] > 1:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    if selected_specification not in specifications[selected_benchmark]:
        raise Exception("No specification '{}' for benchmark {}.".format(selected_specification, selected_benchmark))

    def callback(idx, result, done):
        path = os.path.join("..", "..", "output", selected_benchmark)
        time = str(result.timestamp).replace(" ", "_")
        file_name = "{}{}_{}.pickle.gz".format(
            selected_specification,
            f"_{identifier}" if identifier is not None else "",
            time,
        )
        os.makedirs(path, exist_ok=True)
        result.dump_to_file(os.path.join(path, file_name))

    benchmark_module = importlib.import_module("{}.benchmark".format(selected_benchmark.lower()))

    experiment = get_experiment_factory(N, benchmark_module, selected_specification, mode, init_seed, callback=callback)()

    use_gpu = N == 1 or N_workers[selected_benchmark] == 1
    experiment.run(N_workers=min(N, N_workers[selected_benchmark]), silent=False, use_gpu=use_gpu)

if __name__ == "__main__":
    main()

