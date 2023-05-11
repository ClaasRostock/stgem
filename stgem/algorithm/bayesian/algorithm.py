import numpy as np
import GPyOpt

from stgem.algorithm import Algorithm

class BayesianOptimization(Algorithm):
    """Implements Bayesian optimization algorithm.

    Currently defined only for continuous domains."""

    def setup(self, search_space, device=None, logger=None):
        super().setup(search_space, device, logger)

        self.bounds = [
            {"name": f"x_{i}", "type": "continuous", "domain": (-1, 1)}
            for i in range(self.search_space.input_dimension)
        ]

    def do_train(self, active_outputs, test_repository, budget_remaining):
        pass

    def do_generate_next_test(self, active_outputs, test_repository, budget_remaining):
        X, _, Y = test_repository.get()
        X = np.asarray([x.inputs for x in X])
        Y = np.array([min(y[i] for i in active_outputs) for y in Y]).reshape(X.shape[0], 1)
        BO = GPyOpt.methods.BayesianOptimization(
                f=None,
                batch_size=1,
                domain=self.bounds,
                X=X,
                Y=Y,
                normalize_Y=False)
        test = BO.suggest_next_locations()[0]
        return np.asarray(test)

