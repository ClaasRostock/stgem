import copy, datetime, gzip, os, random

import torch

import dill as pickle
import numpy as np

from stgem.algorithm.algorithm import Algorithm
from stgem.budget import Budget
from stgem.exceptions import *
from stgem.logger import Logger
from stgem.objective_selector import ObjectiveSelectorAll
from stgem.sut import SearchSpace, SUT, SUTInput
from stgem.test_repository import TestRepository

class StepResult:

    def __init__(self, test_repository, success, parameters):
        self.timestamp = datetime.datetime.now()
        self.test_repository = test_repository
        self.success = success
        self.parameters = parameters
        self.models = []
        self.final_model = None

class STGEMResult:

    def __init__(self, description, sut_name, sut_parameters, seed, test_repository, step_results):
        self.timestamp = datetime.datetime.now()
        self.description = description
        self.sut_name = sut_name
        self.sut_parameters = sut_parameters
        self.seed = seed
        self.step_results = step_results
        self.test_repository = test_repository

    @staticmethod
    def restore_from_file(file_name: str):
        o = gzip.open if file_name.endswith(".gz") else open
        with o(file_name, "rb") as file:
            obj = pickle.load(file)
        return obj

    def dump_to_file(self, file_name: str):
        if os.path.exists(file_name):
            raise FileExistsError(file_name)

        o = gzip.open if file_name.endswith(".gz") else open
        # first create a temporary file
        temp_file_name = f"{file_name}.tmp"
        with o(temp_file_name, "wb") as file:
            pickle.dump(self, file)
        # then we rename it to its final name
        os.replace(temp_file_name, file_name)

class Step:

    def run(self) -> StepResult:
        raise NotImplementedError

    def setup(self, sut, search_space, test_repository, budget, objective_funcs, objective_selector, device, logger):
        self.sut = sut
        self.search_space = search_space
        self.test_repository = test_repository
        self.budget = budget
        self.objective_funcs = objective_funcs
        self.objective_selector = objective_selector
        self.device = device
        self.logger = logger
        self.log = lambda msg: (self.logger("step", msg) if logger is not None else None)

class Search(Step):
    """A search step."""

    def __init__(self, algorithm: Algorithm, budget_threshold, mode="exhaust_budget", results_include_models=False, results_checkpoint_period=1):
        self.algorithm = algorithm
        self.budget = None
        self.budget_threshold = budget_threshold
        if mode not in ["exhaust_budget", "stop_at_first_objective"]:
            raise Exception(f"Unknown test generation mode '{mode}'.")
        self.mode = mode

        self.results_include_models = results_include_models
        self.results_checkpoint_period = results_checkpoint_period

    def setup(self, sut, search_space, test_repository, budget, objective_funcs, objective_selector, device, logger):
        super().setup(sut, search_space, test_repository, budget, objective_funcs, objective_selector, device, logger)

        self.algorithm.setup(
            search_space=self.search_space,
            device=self.device,
            logger=self.logger)

    def run(self) -> StepResult:
        self.budget.update_threshold(self.budget_threshold)

        # This stores the test indices that were executed during this step.
        test_idx = []
        # A list for saving model skeletons.
        model_skeletons = []

        # Allow the algorithm to initialize itself.
        self.algorithm.initialize()

        self.success = True
        if (
            self.mode != "stop_at_first_objective"
            or self.test_repository.minimum_objective > 0.0
        ):
            self.success = False

            # Below we omit including a test into the test repository if the
            # budget was exhausted during training, generation, or test
            # execution. We do not care for the special case where the budget
            # is exactly 0 as this is unlikely.

            i = 0
            while self.budget.remaining() > 0:
                self.log(f"Budget remaining {self.budget.remaining()}.")

                # Create a new test repository record to be filled.
                performance = self.test_repository.new_record()

                self.algorithm.train(self.objective_selector.select(), self.test_repository, self.budget.remaining())
                self.budget.consume("training_time", performance.obtain("training_time"))
                if self.budget.remaining() <= 0:
                    self.log("Ran out of budget during training. Discarding the test.")
                    self.test_repository.discard_record()
                    break

                self.log(f"Starting to generate test {self.test_repository.tests + 1}.")
                could_generate = True
                try:
                    next_test = self.algorithm.generate_next_test(self.objective_selector.select(), self.test_repository, self.budget.remaining())
                except AlgorithmException:
                    # We encountered an algorithm error. There might be many
                    # reasons such as explosion of gradients. We take this as
                    # an indication that the algorithm is unable to keep going,
                    # so we exit.
                    break
                except GenerationException:
                    # We encountered a generation error. We take this as an
                    # indication that another training phase could correct the
                    # problem, so we do not exit completely.
                    could_generate = False

                self.budget.consume("generation_time", performance.obtain("generation_time"))
                if self.budget.remaining() <= 0:
                    self.log("Ran out of budget during test generation. Discarding the test.")
                    self.test_repository.discard_record()
                    break
                if could_generate:
                    self.log(f"Generated test {next_test}.")
                    self.log("Executing the test...")

                    performance.timer_start("execution")
                    sut_input = SUTInput(next_test, None, None)
                    sut_output = self.sut.execute_test(sut_input)
                    performance.record("execution_time", performance.timer_reset("execution"))

                    self.test_repository.record_input(sut_input)
                    self.test_repository.record_output(sut_output)

                    self.budget.consume("execution_time", performance.obtain("execution_time"))
                    self.budget.consume(sut_output)
                    if self.budget.remaining() <= 0:
                        self.log("Ran out of budget during test execution. Discarding the test.")
                        self.test_repository.discard_record()
                        break
                    self.budget.consume("executions")

                    self.log(f"Input to the SUT: {sut_input}")

                    if sut_output.error is None:
                        self.log(f"Output from the SUT: {sut_output}")

                        objectives = [objective(sut_input, sut_output) for objective in self.objective_funcs]
                        self.test_repository.record_objectives(objectives)

                        self.log(f"The actual objective: {objectives}")

                        # TODO: Argmin does not take different scales into account.
                        self.objective_selector.update(np.argmin(objectives))
                    else:
                        self.log(
                            f"An error '{sut_output.error}' occurred during the test execution. No output available."
                        )
                        self.test_repository.record_objectives([])

                    idx = self.test_repository.finalize_record()
                    test_idx.append(idx)

                    if not self.success and self.test_repository.minimum_objective <= 0.0:
                        self.success = True
                        self.log(f"First success at test {i + 1}.")
                else:
                    self.log("Encountered a problem with test generation. Skipping to next training phase.")

                # Save the models if requested.
                if self.results_include_models and self.results_checkpoint_period != 0 and i % self.results_checkpoint_period == 0:
                    model_skeletons.append([model.skeletonize() for model in self.algorithm.models])
                else:
                    model_skeletons.append(None)

                i += 1

                if self.success and self.mode == "stop_at_first_objective":
                    break

        # Allow the algorithm to store trained models or other generated data.
        self.algorithm.finalize()

        # Report results.
        self.log(
            f"Step minimum objective component: {self.test_repository.minimum_objective}"
        )

        return self._generate_step_result(test_idx, model_skeletons)

    def _generate_step_result(self, test_idx, model_skeletons):
        # Save certain parameters in the StepResult object.
        parameters = {
            "algorithm_name": self.algorithm.__class__.__name__,
            "algorithm": copy.deepcopy(self.algorithm.parameters),
        }
        parameters["model_name"] = [self.algorithm.models[i].__class__.__name__ for i in range(self.algorithm.N_models)]
        parameters["model"] = [copy.deepcopy(self.algorithm.models[i].parameters) for i in range(self.algorithm.N_models)]
        parameters["objective_name"] = [objective.__class__.__name__ for objective in self.objective_funcs]
        parameters["objective"] = [copy.deepcopy(objective.parameters) for objective in self.objective_funcs]
        parameters["objective_selector_name"] = self.objective_selector.__class__.__name__
        parameters["objective_selector"] = copy.deepcopy(self.objective_selector.parameters)
        parameters["executed_tests"] = test_idx

        # Build the StepResult object.
        step_result = StepResult(self.test_repository, self.success, parameters)
        if self.results_include_models:
            step_result.models = model_skeletons
            step_result.final_models = [model.skeletonize() for model in self.algorithm.models]

        return step_result

class Load(Step):
    """Step which simply loads pregenerated data from a file. By default we
    record every loaded test into the test repository and consume the budget
    based on the information found in the data file. The budget consumption can
    be disabled by setting consume_budget to False. This can be useful if the
    user wants to populate the test repository with prior data which is not
    meant to consume any budget."""

    def __init__(self, file_name, mode="initial", load_range=None, consume_budget=True, recompute_objective=False):
        self.file_name = file_name
        if not os.path.exists(self.file_name):
            raise Exception(f"Pregenerated date file '{self.file_name}' does not exist.")
        if mode not in ["initial", "random"]:
            raise ValueError(f"Unknown load mode '{mode}'.")
        if load_range < 0:
            raise ValueError(f"The load range {load_range} cannot be negative.")
        self.mode = mode
        self.load_range = load_range
        self.consume_budget = consume_budget
        self.recompute_objective = recompute_objective

    def run(self, results_include_models=False, results_checkpoint_period=1) -> StepResult:

        """
        Notice that below we obtain the training time and generation time of
        the loaded test and use it to consume budget and populate training and
        generation times of the loaded test in the test repository. This might
        not make sense in every context. For example if the loaded test was
        generated using OGAN and loaded as a random initial data, then the
        training and generation times are too high. Thus this class is mostly
        meant to load pregenerated random data and then the training and
        generation times make sense. If the training and generation time do not
        make sense, the user can set self.consume_budget to False.
        """

        # This stores the test indices that were executed during this step.
        test_idx = []

        try:
            raw_data = STGEMResult.restore_from_file(self.file_name)
        except:
            raise Exception(
                f"Error loading STGEMResult object from file '{self.file_name}'."
            )

        """
        If load_range is defined and consume_budget is True, then we stop when
        either the budget is consumed or we have loaded load_range many tests.
        """

        range_max = raw_data.test_repository.tests
        if self.load_range is None:
            self.load_range = range_max
        elif self.load_range > range_max:
            raise ValueError(
                f"The load range {self.load_range} is out of bounds. The maximum range for loaded data is {range_max}."
            )

        if self.mode == "random":
            # Use the search space RNG to ensure deterministic selection.
            idx = self.search_space.rng.choice(np.arange(range_max), size=self.load_range, replace=False)
        elif self.mode == "initial":
            idx = range(self.load_range)

        for i in idx:
            if self.budget.remaining() == 0: break
            self.log(f"Budget remaining {self.budget.remaining()}.")
            X, Z, Y = raw_data.test_repository.get(i)
            old_performance = raw_data.test_repository.performance(i)

            if len(X.inputs) != self.search_space.input_dimension:
                raise ValueError(
                    f"Loaded sample input dimension {len(X.inputs)} does not match SUT input dimension {self.search_space.input_dimension}"
                )
            if Z.output_timestamps is None:
                if len(Z.outputs) != self.search_space.output_dimension:
                    raise ValueError(
                        f"Loaded sample vector output dimension {len(Z.outputs)} does not match SUT vector output dimension {self.search_space.output_dimension}."
                    )
            elif Z.outputs.shape[0] != self.search_space.output_dimension:
                raise ValueError(
                    f"Loaded sample signal number {Z.outputs.shape[0]} does not match SUT signal number {self.search_space.output_dimension}."
                )

            # Consume the budget if requested.
            if self.consume_budget:
                self.budget.consume("training_time", old_performance.obtain("training_time"))
                self.budget.consume("generation_time", old_performance.obtain("generation_time"))
                self.budget.consume("execution_time", old_performance.obtain("execution_time"))
                if self.budget.remaining() <= 0:
                    self.log("Ran out of budget during training, generation, or execution. Discarding the test.")
                    break
                self.budget.consume("executions")
                self.budget.consume(Z)

            # Recompute the objective of requested.
            if self.recompute_objective and Z.error is None:
                Y = [objective(X, Z) for objective in self.objective_funcs]

            # Record the test and its performance into the test repository.
            performance = self.test_repository.new_record()
            self.test_repository.record_input(X)
            self.test_repository.record_output(Z)
            self.test_repository.record_objectives(Y)
            performance.record("training_time", old_performance.obtain("training_time"))
            performance.record("generation_time", old_performance.obtain("generation_time"))
            performance.record("execution_time", old_performance.obtain("execution_time"))
            idx = self.test_repository.finalize_record()
            test_idx.append(idx)

            self.log("Loaded randomly a test with input")
            self.log(str(X))
            if Z.error is not None:
                self.log("and output")
                self.log(str(Z))
                self.log(f"and objective {Y}.")
            else:
                self.log("which failed to execute and produce output.")

        if self.mode == "initial":
            self.log(
                f"Loaded initial {self.load_range} tests from the result file {self.file_name}."
            )
        else:
            self.log(
                f"Loaded randomly {self.load_range} tests from the result file {self.file_name}."
            )

        success = self.test_repository.minimum_objective <= 0

        # Save certain parameters in the StepResult object.
        parameters = {
            "file_name": self.file_name,
            "mode": self.mode,
            "load_range": self.load_range,
            "consume_budget": self.consume_budget,
            "recompute_objective": self.recompute_objective,
            "executed_tests": test_idx,
        }
        return StepResult(self.test_repository, success, parameters)

class STGEM:

    def __init__(self, description, sut: SUT, objectives, objective_selector=None, budget: Budget = None, steps=None):
        self.description = description
        # The description might be used as a file name, so we check for some
        # nongood characters.
        # TODO: Is this complete enough?
        nonsafe_chars = "/\<>:\"|?*"
        for c in self.description:
            if c in nonsafe_chars:
                raise ValueError(
                    f"Character '{c}' not allowed in a description (could be used as a file name)."
                )
        self.sut = sut
        self.step_results = []

        if budget is None:
            budget = Budget()
        self.budget = budget

        self.objectives = objectives
        if objective_selector is None:
            objective_selector = ObjectiveSelectorAll()
        self.objective_selector = objective_selector

        self.steps = [] if steps is None else steps
        self.device = None

        self.logger = Logger()
        self.log = lambda msg: (self.logger("stgem", msg) if self.logger is not None else None)

    def setup_seed(self, seed=None):
        self.seed = seed
        # We use a random seed unless it is specified.
        # Notice that making Pytorch deterministic makes it a lot slower.
        if self.seed is not None:
            torch.use_deterministic_algorithms(mode=True)
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
        else:
            self.seed = random.randint(0, 2**15)

        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)

        # A random source for SUT for deterministic random samples from the
        # input space.
        self.search_space_rng = np.random.RandomState(seed=self.seed)

    def setup_sut(self):
        self.sut.setup()

    def setup_search_space(self):
        self.search_space = SearchSpace()
        self.search_space.setup(sut=self.sut, objectives=self.objectives, rng=self.search_space_rng)

    def setup_objectives(self):
        for o in self.objectives:
            o.setup(self.sut)

        self.objective_selector.setup(self.objectives)

    def setup_steps(self):
        for step in self.steps:
            step.setup(
                sut=self.sut,
                search_space=self.search_space,
                test_repository=self.test_repository,
                budget=self.budget,
                objective_funcs=self.objectives,
                objective_selector=self.objective_selector,
                device=self.device,
                logger=self.logger)

    def setup(self, seed=None, use_gpu=True):
        if use_gpu:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if self.device.type != "cuda":
                self.log(
                    f"Warning: requested torch device 'cuda' but got '{self.device.type}'."
                )
        else:
            self.device = torch.device("cpu")

        self.test_repository = TestRepository()

        self.setup_seed(seed=seed)
        self.setup_sut()
        self.setup_search_space()
        self.setup_objectives()
        self.setup_steps()

    def _generate_result(self, step_results):
        return STGEMResult(self.description, self.sut.__class__.__name__, copy.deepcopy(self.sut.parameters), self.seed, self.test_repository, step_results)

    def _run(self) -> STGEMResult:
        # Running this assumes that setup has been run.

        # Setup and run steps sequentially.
        self.step_results = []
        self.step_results.extend(step.run() for step in self.steps)
        return self._generate_result(self.step_results)

    def run(self, seed=None) -> STGEMResult:
        self.setup(seed)
        return self._run()

