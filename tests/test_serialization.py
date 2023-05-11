import os, math, unittest
import numpy as np

from stgem.generator import STGEM, Search, STGEMResult
from stgem.sut.python import PythonFunction
from stgem.objective import Minimize
from stgem.algorithm.random.algorithm import Random
from stgem.algorithm.random.model import Uniform
from stgem.algorithm.ogan.algorithm import OGAN
from stgem.algorithm.ogan.model import OGAN_Model

def myfunction(input: [[-15, 15], [-15, 15], [-15, 15]]) -> [[0, 350], [0, 350], [0, 350]]:
    x1, x2, x3 = input[0], input[1], input[2]
    h1 = 305 - 100 * (math.sin(x1 / 3) + math.sin(x2 / 3) + math.sin(x3 / 3))
    h2 = 230 - 75 * (math.cos(x1 / 2.5 + 15) + math.cos(x2 / 2.5 + 15) + math.cos(x3 / 2.5 + 15))
    h3 = (x1 - 7) ** 2 + (x2 - 7) ** 2 + (x3 - 7) ** 2 - (
            math.cos((x1 - 7) / 2.75) + math.cos((x2 - 7) / 2.75) + math.cos((x3 - 7) / 2.75))

    return [h1, h2, h3]

class MyTestCase(unittest.TestCase):
    def test_dump(self):

        generator = STGEM(
            description="test-dump",
            sut=PythonFunction(function=myfunction),
            objectives=[Minimize(selected=[0, 1, 2], scale=True)],
            steps=[
                Search(budget_threshold={"executions": 2},
                       algorithm=Random(model_factory=(lambda: Uniform())),
                       ),
                Search(budget_threshold={"executions": 4},
                       algorithm=OGAN(model_factory=(lambda: OGAN_Model())),
                       results_include_models=True
                       )
            ]
        )

        r = generator.run()
        file_name = f"{generator.description}.pickle"
        r.dump_to_file(file_name)
        result2 = STGEMResult.restore_from_file(file_name)

        # check that the model still works
        y = result2.step_results[1].models[0][0].predict_objective(np.array([0,0,0]).reshape(1, -1))

        os.remove(file_name)

if __name__ == "__main__":
    unittest.main()
