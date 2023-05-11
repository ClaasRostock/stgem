import importlib, os

import click

from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.generator import Search, STGEM
from stgem.objective import FalsifySTL
from stgem.objective_selector import ObjectiveSelectorAll
from stgem.sut.matlab.sut import Matlab, Matlab_Simulink

from run import benchmarks, specifications
from run import specifications as benchmark_specifications

@click.command()
@click.argument("selected_benchmark", type=click.Choice(benchmarks, case_sensitive=False))
@click.argument("selected_specification", type=str)
@click.argument("mode", type=str, default="")
@click.argument("n", type=int)
@click.argument("init_seed", type=int)
@click.argument("identifier", type=str, default="")
def main(selected_benchmark, selected_specification, mode, n, init_seed, identifier):
    N = n

    if (
        selected_specification
        not in benchmark_specifications[selected_benchmark]
    ):
        raise Exception(
            f"No specification '{selected_specification}' for benchmark {selected_benchmark}."
        )

    output_file = f"{identifier}.npy.gz"
    if os.path.exists(output_file):
        raise Exception(f"Output file '{output_file}' already exists.")

    benchmark_module = importlib.import_module(
        f"{selected_benchmark.lower()}.benchmark"
    )

    sut_parameters, specifications, strict_horizon_check = benchmark_module.build_specification(selected_specification, mode)

    if "type" in sut_parameters and sut_parameters["type"] == "simulink":
        sut = Matlab_Simulink(sut_parameters)
    else:
        sut = Matlab(sut_parameters)

    ranges = {
        sut_parameters["inputs"][n]: sut_parameters["input_range"][n]
        for n in range(len(sut_parameters["input_range"]))
    }
    for n in range(len(sut_parameters["output_range"])):
        ranges[sut_parameters["outputs"][n]] = sut_parameters["output_range"][n]

    step = Search(mode="exhaust_budget",
                  budget_threshold={"executions": N},
                  algorithm=Random(model_factory=(lambda: Uniform()))
                 )      

    objectives = [FalsifySTL(specification=specification, ranges=ranges, scale=True, strict_horizon_check=strict_horizon_check) for specification in specifications]

    generator = STGEM(
        description="",
        sut=sut,
        objectives=objectives,
        objective_selector=ObjectiveSelectorAll(),
        steps=[step]
    )

    r = generator.run(seed=init_seed)
    r.dump_to_file(output_file)

if __name__ == "__main__":
    main()

