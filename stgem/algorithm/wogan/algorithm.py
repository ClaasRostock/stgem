import heapq

import numpy as np

from stgem.algorithm import Algorithm

class WOGAN(Algorithm):
    """Implements the test suite generation based on online Wasserstein
    generative adversarial networks."""

    default_parameters = {
        "bins": 10,
        "wgan_batch_size": 32,
        "fitness_coef": 0.95,
        "train_delay": 3,
        "N_candidate_tests": 1,
        "invalid_threshold": 100,
        "shift_function": "linear",
        "shift_function_parameters": {"initial": 0, "final": 3},
    }

    def setup(self, search_space, device=None, logger=None):
        super().setup(search_space, device, logger)

        # Set up the shift function for sampling training data.
        # ---------------------------------------------------------------------
        # The initial shift value is determined at the minimum budget left when
        # the function do_train is called for the first time. The final shift
        # value is determined at budget 0.0.
        if self.shift_function is None:
            raise Exception("No shift function defined.")
        if self.shift_function_parameters is None:
            raise Exception("No shift function parameters defined.")

        if self.shift_function not in ["linear"]:
            raise Exception(f"No shift function type '{self.shift_function}'.")

        # Set up the function for computing the bin weights.
        # ---------------------------------------------------------------------
        self.bin_weight = lambda x: 1 - 1 / (1 + np.exp(-1 * x))

        self.get_bin = (lambda x: int(x * self.bins) if x < 1.0 else self.bins - 1)

    def initialize(self):
        self.test_bins = [{i:[] for i in range(self.bins)} for _ in range(self.N_models)] # a dictionary to tell which test is in which bin for each model
        self.model_trained = [0 for _ in range(self.N_models)]                            # keeps track how many tests were generated when a model was previously trained

        self.first_training = True

    def bin_sample(self, N, shift):
        """Samples N bin indices."""

        """
        The distribution on the indices is defined as follows. Suppose that S
        is a nonnegative and decreasing function satisfying S(-x) = 1 - S(x)
        for all x. Consider the middle points of the bins. We map the middle
        point of the middle bin to 0 and the remaining middle points
        symmetrically around 0 with first middle point corresponding to -1 and
        the final to 1. We then shift these mapped middle points to the left by
        the given amount. The weight of the bin will is S(x) where x is the
        mapped and shifted middle point. We use the function self.bin_weight
        for S.
        """

        # If the number of bins is odd, then the middle point of the middle bin
        # interval is mapped to 0 and otherwise the point common to the two
        # middle bin intervals is mapped to 0.
        # TODO: This could be predefined in __init__.
        if self.bins % 2 == 0:
            h = lambda x: x - (int(self.bins/2) + 0.0) * (1/self.bins)
        else:
            h = lambda x: x - (int(self.bins/2) + 0.5) * (1/self.bins)

        # We basically take the middle point of a bin interval, map it to
        # [-1, 1] and apply S on the resulting point to find the unnormalized
        # bin weight.
        weights = np.zeros(shape=(self.bins))
        for n in range(self.bins):
            weights[n] = self.bin_weight(h((n + 0.5) * (1/self.bins)) + shift)
        # Normalize weights.
        weights = weights / np.sum(weights)

        return np.random.choice(list(range(self.bins)), N, p=weights)

    def training_sample(self, N, X, B, shift):
        """Samples N elements from X. The sampling is done by picking a bin and
        uniformly randomly selecting a test from the bin, but we do not select
        the same test twice. The probability of picking each bin is computed
        via the function bin_sample."""

        sample_X = np.zeros(shape=(N, X.shape[1]))
        available = {n: v.copy() for n, v in B.items()}
        for n, bin_idx in enumerate(self.bin_sample(N, shift)):
            # If a bin is empty, try one greater bin.
            while len(available[bin_idx]) == 0:
                bin_idx += 1
                bin_idx %= self.bins
            idx = np.random.choice(available[bin_idx])
            available[bin_idx].remove(idx)
            sample_X[n] = X[idx]

        return sample_X

    def do_train(self, active_outputs, test_repository, budget_remaining):
        # PerformanceRecordHandler for the current test.
        performance = test_repository.performance(test_repository.current_test)
        analyzer_losses = [[] for _ in range(self.N_models)]
        critic_losses = [[] for _ in range(self.N_models)]
        generator_losses = [[] for _ in range(self.N_models)]
        gradient_penalties = [[] for _ in range(self.N_models)]
        performance.record("analyzer_loss", analyzer_losses)
        performance.record("critic_loss", critic_losses)
        performance.record("generator_loss", generator_losses)
        performance.record("gradient_penalty", gradient_penalties)

        if self.first_training and self.shift_function == "linear":
            # We increase the shift linearly according to the given initial and
            # given final value.
            alpha = (self.shift_function_parameters["initial"] - self.shift_function_parameters["final"])/budget_remaining
            beta = self.shift_function_parameters["final"]
            self.shift = lambda x: alpha * x + beta

        # Take into account how many tests a previous step (usually a random
        # search) has generated.
        tests_generated = test_repository.tests

        # TODO: Check that we have previously generated at least a couple of
        #       tests. Otherwise we get a cryptic error.

        # Put tests into bins.
        idx = test_repository.indices if self.first_training else [test_repository.tests - 1]
        for i in range(self.N_models):
            for j in idx:
                self.test_bins[i][self.get_bin(test_repository.get(j)[-1][i])].append(j)

        # We train only the models corresponding to active outputs and only if
        # there has been enough delay since the last training. During the first
        # training, we ignore the delay.
        for i in active_outputs:
            if self.first_training or tests_generated - self.model_trained[i] >= self.train_delay:
                X, _, Y = test_repository.get()
                dataX = np.asarray([sut_input.inputs for sut_input in X])
                dataY = np.array(Y)[:,i].reshape(-1, 1)
                epochs = self.models[i].train_settings_init["epochs"] if self.first_training else self.models[i].train_settings["epochs"]
                train_settings = self.models[i].train_settings_init if self.first_training else self.models[i].train_settings
                for _ in range(epochs):
                    self.log(f"Training analyzer {i + 1}...")
                    losses = self.models[i].train_analyzer_with_batch(dataX,
                                                                      dataY,
                                                                      train_settings=train_settings
                                                                     )
                    analyzer_losses[i].append(losses)

                    # Train the WGAN.
                    self.log(f"Training the WGAN model {i + 1}...")
                    # We include the new tests to the batch with high
                    # probability if and only if they have low objective.
                    # Moreover, when we are not doing initial training, we
                    # always attempt to include the latest tests in order to
                    # utilize the latest information.
                    BS = min(self.wgan_batch_size, test_repository.tests)
                    train_X = np.zeros(shape=(BS, self.search_space.input_dimension))
                    latest = 0 if self.first_training else self.train_delay
                    c = 0
                    for j in range(latest):
                        test, _, output = test_repository.get(test_repository.indices[-(j+1)])
                        if self.get_bin(output[i]) >= self.bin_sample(1, self.shift(budget_remaining))[0]:
                            train_X[c] = test.inputs
                            c += 1
                    train_X[c:] = self.training_sample(BS - c,
                                                       np.asarray([sut_input.inputs for sut_input in test_repository.get()[0]]),
                                                       self.test_bins[i],
                                                       self.shift(budget_remaining),
                                                      )
                    C_losses, G_losses, gps = self.models[i].train_with_batch(train_X,
                                                                              train_settings=train_settings
                                                                             )
                    critic_losses[i].append(C_losses)
                    generator_losses[i].append(G_losses)
                    gradient_penalties[i].append(gps)

                self.model_trained[i] = tests_generated

        self.first_training = False

    def do_generate_next_test(self, active_outputs, test_repository, budget_remaining):
        # We generate a new valid test as follows. For each active model, we
        # generate new tests using the model, discard invalid tests, and
        # estimate the corresponding objective function values. The test
        # closest to target fitness 0 (minimization) is treated as the
        # candidate, and the candidate is accepted if the estimate exceeds the
        # current target threshold. The target threshold is changed on each
        # loop execution in order to make acceptance easier. We use a priority
        # queue to track the best tests in case that an estimated good test was
        # generated just before the target threshold was changed enough for it
        # to be selected.
        heap = []
        target_fitness = 0
        entry_count = 0 # this is to avoid comparing tests when two tests added to the heap have the same predicted objective
        N_generated = 0
        N_invalid = 0
        self.log(
            f'Generating using WOGAN models {",".join(str(m + 1) for m in active_outputs)}.'
        )

        # PerformanceRecordHandler for the current test.
        performance = test_repository.performance(test_repository.current_test)

        while True:
            # TODO: Avoid selecting similar or same tests.
            for i in active_outputs:
                while True:
                    # If we have already generated many tests and all have been
                    # invalid, we give up and hope that the next training phase
                    # will fix things.
                    if N_invalid >= self.invalid_threshold:
                        raise GenerationException(
                            f"Could not generate a valid test within {N_invalid} tests."
                        )

                    # Generate several tests and pick the one with best
                    # predicted objective function component. We do this as
                    # long as we find at least one valid test.
                    try:
                        candidate_tests = self.models[i].generate_test(self.N_candidate_tests)
                    except:
                        raise

                    # Pick only the valid tests.
                    valid_idx = [i for i in range(self.N_candidate_tests) if self.search_space.is_valid(candidate_tests[i]) == 1]
                    candidate_tests = candidate_tests[valid_idx]
                    N_generated += self.N_candidate_tests
                    N_invalid += self.N_candidate_tests - len(valid_idx)
                    if candidate_tests.shape[0] == 0:
                        continue

                    # Estimate objective function values and add the tests
                    # to heap.
                    tests_predicted_objective = self.models[i].predict_objective(candidate_tests)
                    for j in range(tests_predicted_objective.shape[0]):
                        heapq.heappush(heap, (tests_predicted_objective[j,0], entry_count, i, candidate_tests[j]))
                        entry_count += 1

                    break

            # We go up from 0 like we would go down from 1 when multiplied by self.fitness_coef.
            target_fitness = 1 - self.fitness_coef*(1 - target_fitness)

            # Check if the best predicted test is good enough.
            # Without eps we could get stuck if prediction is always 1.0.
            eps = 1e-4
            if heap[0][0] - eps <= target_fitness: break

        # Save information on how many tests needed to be generated etc.
        # -----------------------------------------------------------------
        performance.record("N_tests_generated", N_generated)
        performance.record("N_invalid_tests_generated", N_invalid)

        best_test = heap[0][3]
        best_model = heap[0][2]
        best_estimated_objective = heap[0][0]

        self.log(
            f"Chose test {best_test} with predicted minimum objective {best_estimated_objective} on WGAN model {best_model + 1}. Generated total {N_generated} tests of which {N_invalid} were invalid."
        )

        return best_test
