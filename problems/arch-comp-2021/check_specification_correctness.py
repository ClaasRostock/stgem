import importlib

import numpy as np

from stgem.objective import FalsifySTL
from stgem.sut import SUTInput
from stgem.sut.matlab.sut import Matlab, Matlab_Simulink

if __name__ == "__main__":
    data = {"AT": {
                "AT1":   ((0, -0.1819, 4), [0.9995966, 0.9984858, 0.99905604, 0.9996593, -0.9959437, -0.9985024, -0.9991235, -0.9989661, -0.995739, -0.9995906, 0.9965855, 0.99919313]),
                "ATX2":  ((0, -0.5625, 4), [0.12298248, -0.06031702, -0.79451796, -0.98263103, -0.74734473, -0.27100616, -0.05087789, 0.07564675, -0.85285562, -0.68206928, -0.80491848, -0.29071007]),
                "ATX61": ((0, -3.8843, 4), [0.7109798, 0.64034004, 0.44575836, -0.5571968, -0.42234251, 0.86140067, -0.6660015, -0.43786175, 0.08356674, -0.98862135, 0.9722936, 0.51912145]),
                "ATX62": ((0, -1.3139, 4), [-0.27232345, -0.1372991, -0.69118904, -0.52561967, -0.82506686, -0.3621167, 0.63643551, -0.97496361, -0.47280239, 0.9679158, 0.5165628, 0.52382468])
            },
            "SC": {
                "SC":    ((0, -9.2078, 4), [1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1, 1, -1])
            }
           }

    """
    Missing:
    AFC27
    AFC29

    AT2
    AT51
    AT52
    AT53
    AT54
    AT6A
    AT6B
    AT6C
    ATX13
    ATX14

    CC1
    CC2
    CC3
    CC4
    CC5
    CCX

    F16

    NN
    NNX
    """


    for benchmark, value in data.items():
        module = importlib.import_module(f"{benchmark.lower()}.benchmark")
        build_specification = module.build_specification
        for specification, ((idx, robustness, precision), test) in value.items():
            sut_parameters, specifications, strict_horizon_check = build_specification(specification)
            sut = (
                Matlab_Simulink(sut_parameters)
                if "type" in sut_parameters
                and sut_parameters["type"] == "simulink"
                else Matlab(sut_parameters)
            )
            sut.setup()
            objectives = [FalsifySTL(specification=s, scale=False, strict_horizon_check=strict_horizon_check) for s in specifications]
            for objective in objectives:
                objective.setup(sut)

            sut_input = SUTInput(np.array(test), None, None)
            sut_output = sut.execute_test(sut_input)
            output = [objective(sut_input, sut_output) for objective in objectives]

            if abs(output[idx] - robustness) >= 10**(-precision):
                raise SystemExit(
                    f"Incorrect output robustness {output[idx]} for benchmark '{benchmark}' and specification '{specification}'. Expected {robustness}."
                )

    print("All correct!")

