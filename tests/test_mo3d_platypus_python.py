import math, os, unittest

from stgem.generator import STGEM, Search
from stgem.sut.python import PythonFunction
from stgem.objective import Minimize
from stgem.objective_selector import ObjectiveSelectorMAB
from stgem.algorithm.platypus.algorithm import PlatypusOpt
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform, LHS

def myfunction(input: [[-15, 15], [-15, 15], [-15, 15]]) -> [[0, 350], [0, 350], [0, 350]]:
    x1, x2, x3 = input[0], input[1], input[2]
    h1 = 305 - 100 * (math.sin(x1 / 3) + math.sin(x2 / 3) + math.sin(x3 / 3))
    h2 = 230 - 75 * (math.cos(x1 / 2.5 + 15) + math.cos(x2 / 2.5 + 15) + math.cos(x3 / 2.5 + 15))
    h3 = (x1 - 7) ** 2 + (x2 - 7) ** 2 + (x3 - 7) ** 2 - (
            math.cos((x1 - 7) / 2.75) + math.cos((x2 - 7) / 2.75) + math.cos((x3 - 7) / 2.75))

    return [h1, h2, h3]

class PlatypusTest(unittest.TestCase):
    def test_plattypus1(self):
        generator = STGEM(
            description="mo3d-playpus",
            sut=PythonFunction(function=myfunction),
            objectives=[Minimize(selected=[0], scale=True),
                        Minimize(selected=[1], scale=True),
                        Minimize(selected=[2], scale=True)
                        ],
            objective_selector=ObjectiveSelectorMAB(warm_up=5),
            steps=[
                Search(budget_threshold={"executions": 2000},
                       mode="stop_at_first_objective",
                       algorithm=PlatypusOpt()
                )
            ]
        )

        r = generator.run()
        file_name = f"{generator.description}.pickle"
        r.dump_to_file(file_name)
        os.remove(file_name)

if __name__ == "__main__":
    unittest.main()

