import copy, importlib

import numpy as np
import torch

from stgem import algorithm
from stgem.algorithm import Model, ModelSkeleton
from stgem.exceptions import AlgorithmException

class OGAN_ModelSkeleton(ModelSkeleton):

    def __init__(self, parameters):
        super().__init__(parameters)
        self.modelG = None
        self.modelD = None

    def _generate_test(self, N=1, device=None):
        if self.modelG is None:
            raise Exception("No machine learning models available. Has the model been setup correctly?")

        if N <= 0:
            raise ValueError("The number of tests should be positive.")

        training_G = self.modelG.training
        # Generate uniform noise in [-1, 1].
        noise = (torch.rand(size=(N, self.modelG.input_shape))*2 - 1).to(device)
        self.modelG.train(False)
        result = self.modelG(noise)

        if torch.any(torch.isinf(result)) or torch.any(torch.isnan(result)):
            raise AlgorithmException("Generator produced a test with inf or NaN entries.")

        self.modelG.train(training_G)
        return result.cpu().detach().numpy()

    def generate_test(self, N=1, device=None):
        """Generate N random tests.

        Args:
          N (int):      Number of tests to be generated.
          device (obj): CUDA device or None.

        Returns:
          output (np.ndarray): Array of shape (N, self.input_ndimension).

        Raises:
        """

        try:
            return self._generate_test(N, device)
        except:
            raise

    def _predict_objective(self, test, device=None):
        if self.modelG is None or self.modelD is None:
            raise Exception("No machine learning models available. Has the model been setup correctly?")

        test_tensor = torch.from_numpy(test).float().to(device)
        return self.modelD(test_tensor).cpu().detach().numpy()

    def predict_objective(self, test, device=None):
        """Predicts the objective function value of the given tests.

        Args:
          test (np.ndarray): Array of shape (N, self.input_ndimension).
          device (obj):      CUDA device or None.

        Returns:
          output (np.ndarray): Array of shape (N, 1).

        Raises:
        """

        try:
            return self._predict_objective(test, device)
        except:
            raise

class OGAN_Model(Model,OGAN_ModelSkeleton):
    """Implements the OGAN model."""

    default_parameters = {
        "optimizer": "Adam",
        "discriminator_lr": 0.001,
        "discriminator_betas": [0.9, 0.999],
        "generator_lr": 0.0001,
        "generator_betas": [0.9, 0.999],
        "noise_batch_size": 512,
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
        "train_settings_init": {
            "epochs": 1,
            "discriminator_epochs": 15,
            "generator_batch_size": 32
        },
        "train_settings": {
            "epochs": 1,
            "discriminator_epochs": 15,
            "generator_batch_size": 32
        }
    }

    def __init__(self, parameters=None):
        Model.__init__(self, parameters)
        OGAN_ModelSkeleton.__init__(self, parameters)

    def setup(self, search_space, device, logger=None, use_previous_rng=False):
        super().setup(search_space, device, logger, use_previous_rng)

        # Infer input and output dimensions for ML models.
        self.parameters["generator_mlm_parameters"]["output_shape"] = self.search_space.input_dimension
        self.parameters["discriminator_mlm_parameters"]["input_shape"] = self.search_space.input_dimension

        # Save current RNG state and use previous.
        if use_previous_rng:
            current_rng_state = torch.random.get_rng_state()
            torch.random.set_rng_state(self.previous_rng_state["torch"])
        else:
            self.previous_rng_state = {"torch": torch.random.get_rng_state()}
        self._initialize()

        # Restore RNG state.
        if use_previous_rng:
            torch.random.set_rng_state(current_rng_state)

    def _initialize(self):
        # Load the specified generator and discriminator machine learning
        # models and initialize them.
        module = importlib.import_module("stgem.algorithm.ogan.mlm")
        generator_class = getattr(module, self.generator_mlm)
        discriminator_class = getattr(module, self.discriminator_mlm)

        self.modelG = generator_class(**self.generator_mlm_parameters).to(self.device)
        self.modelD = discriminator_class(**self.discriminator_mlm_parameters).to(self.device)

        # Load the specified optimizers.
        module = importlib.import_module("torch.optim")
        optimizer_class = getattr(module, self.optimizer)
        generator_parameters = {k[10:]:v for k, v in self.parameters.items() if k.startswith("generator")}
        self.optimizerG = optimizer_class(self.modelG.parameters(), **algorithm.filter_arguments(generator_parameters, optimizer_class))
        discriminator_parameters = {k[14:]:v for k, v in self.parameters.items() if k.startswith("discriminator")}
        self.optimizerD = optimizer_class(self.modelD.parameters(), **algorithm.filter_arguments(discriminator_parameters, optimizer_class))

        # Loss functions.
        def get_loss(loss_s):
            loss_s = loss_s.lower()
            if loss_s == "mse":
                loss = torch.nn.MSELoss()
            elif loss_s == "l1":
                loss = torch.nn.L1Loss()
            elif loss_s in ["mse,logit", "l1,logit"]:
                # When doing regression with values in [0, 1], we can use a
                # logit transformation to map the values from [0, 1] to \R
                # to make errors near 0 and 1 more drastic. Since logit is
                # undefined in 0 and 1, we actually first transform the values
                # to the interval [0.01, 0.99].
                L = 0.001
                g = torch.logit
                if loss_s == "mse,logit":
                    def f(X, Y):
                        return ((g(0.98*X+0.01) - g(0.98*Y+0.01))**2 + L*(g((1+X-Y)/2))**2).mean()
                else:
                    def f(X, Y):
                        return (torch.abs(g(0.98*X+0.01) - g(0.98*Y+0.01)) + L*torch.abs(g((1+X-Y)/2))).mean()
                loss = f
            else:
                raise Exception("Unknown loss function '{}'.".format(loss_s))

            return loss

        try:
            self.lossG = get_loss(self.generator_loss)
            self.lossD = get_loss(self.discriminator_loss)
        except:
            raise

    @classmethod
    def setup_from_skeleton(cls, skeleton, search_space, device, logger=None, use_previous_rng=False):
        model = cls(skeleton.parameters)
        model.setup(search_space, device, logger, use_previous_rng)
        model.modelG = skeleton.modelG.to(device)
        model.modelD = skeleton.modelD.to(device)

        return model

    def skeletonize(self):
        skeleton = OGAN_ModelSkeleton(self.parameters)
        skeleton.modelG = copy.deepcopy(self.modelG).to("cpu")
        skeleton.modelD = copy.deepcopy(self.modelD).to("cpu")

        return skeleton

    def reset(self):
        self._initialize()

    def train_with_batch(self, dataX, dataY, train_settings=None):
        """Train the OGAN with a batch of training data.

        Args:
          dataX (np.ndarray): Array of tests of shape
                              (N, self.input_dimension).
          dataY (np.ndarray): Array of test outputs of shape (N, 1).
          train_settings (dict): A dictionary setting up the number of training
                                 epochs for various parts of the model. The
                                 keys are as follows:

                                   discriminator_epochs: How many times the
                                   discriminator is trained per call.

                                   generator_batch_size: How large batches of
                                   noise are used at a training step.

                                 The default for each missing key is 1. Keys
                                 not found above are ignored.

        Returns:
            D_losses (list): List of discriminator losses observed.
            G_losses (list): List of generator losses observed."""

        if self.modelG is None or self.modelD is None:
            raise Exception("No machine learning models available. Has the model been setup correctly?")

        if train_settings is None:
            train_settings = self.default_parameters["train_settings"]

        if len(dataY) < len(dataX):
            raise ValueError("There should be at least as many training outputs as there are inputs.")

        dataX = torch.from_numpy(dataX).float().to(self.device)
        dataY = torch.from_numpy(dataY).float().to(self.device)

        # Unpack values from the train_settings dictionary.
        discriminator_epochs = train_settings["discriminator_epochs"] if "discriminator_epochs" in train_settings else 1
        generator_batch_size = train_settings["generator_batch_size"] if "generator_batch_size" in train_settings else 32

        # Save the training modes for restoring later.
        training_D = self.modelD.training
        training_G = self.modelG.training

        # Train the discriminator.
        # ---------------------------------------------------------------------
        # We want the discriminator to learn the mapping from tests to test
        # outputs.
        self.modelD.train(True)
        D_losses = []
        for _ in range(discriminator_epochs):
            D_loss = self.lossD(self.modelD(dataX), dataY)
            D_losses.append(D_loss.cpu().detach().numpy().item())
            self.optimizerD.zero_grad()
            D_loss.backward()
            self.optimizerD.step()

        m = np.mean(D_losses)
        if discriminator_epochs > 0:
            self.log(
                f"Discriminator epochs {discriminator_epochs}, Loss: {D_losses[0]} -> {D_losses[-1]} (mean {m})"
            )

        self.modelD.train(False)

        # Visualize the computational graph.
        # print(make_dot(D_loss, params=dict(self.modelD.named_parameters())))

        # Train the generator on the discriminator.
        # -----------------------------------------------------------------------
        # We generate noise and label it to have output 0 (min objective).
        # Training the generator in this way should shift it to generate tests
        # with low output values (low objective). Notice that we need to
        # validate the generated tests as no invalid tests with high fitness
        # exist.
        self.modelG.train(False)
        inputs = np.zeros(shape=(self.noise_batch_size, self.modelG.input_shape))
        k = 0
        while k < inputs.shape[0]:
            noise = torch.rand(1, self.modelG.input_shape)*2 - 1
            new_test = self.modelG(noise.to(self.device)).cpu().detach().numpy()
            # TODO: Currently this can cause an infinite loop, so validity
            # check is disabled. On the other hand, it would make sense update
            # the generator based on valid tests only. What gives?
            #if self.search_space.is_valid(new_test) == 0: continue
            inputs[k,:] = noise[0,:]
            k += 1
        self.modelG.train(True)
        inputs = torch.from_numpy(inputs).float().to(self.device)

        fake_label = torch.zeros(size=(generator_batch_size, 1)).to(self.device)

        # Notice the following subtlety. Below the tensor 'outputs' contains
        # information on how it is computed (the computation graph is being kept
        # track off) up to the original input 'inputs' which does not anymore
        # depend on previous operations. Since 'self.modelD' is used as part of
        # the computation, its parameters are present in the computation graph.
        # These parameters are however not updated because the optimizer is
        # initialized only for the parameters of 'self.modelG' (see the
        # initialization of 'self.modelG').

        G_losses = []
        for n in range(0, self.noise_batch_size, generator_batch_size):
            outputs = self.modelD(self.modelG(inputs[n:n+generator_batch_size]))
            G_loss = self.lossG(outputs, fake_label[:outputs.shape[0]])
            G_losses.append(G_loss.cpu().detach().numpy().item())
            self.optimizerG.zero_grad()
            G_loss.backward()
            self.optimizerG.step()

        m = np.mean(G_losses)
        if self.noise_batch_size > 0:
            self.log(
                f"Generator steps {self.noise_batch_size // generator_batch_size + 1}, Loss: {G_losses[0]} -> {G_losses[-1]}, mean {m}"
            )

        self.modelG.train(False)

        # Visualize the computational graph.
        # print(make_dot(G_loss, params=dict(self.modelG.named_parameters())))

        # Restore the training modes.
        self.modelD.train(training_D)
        self.modelG.train(training_G)

        return D_losses, G_losses

    def generate_test(self, N=1):
        """Generate N random tests.

        Args:
          N (int):      Number of tests to be generated.

        Returns:
          output (np.ndarray): Array of shape (N, self.input_ndimension).

        Raises:
        """

        try:
            return self._generate_test(N, device=self.device)
        except:
            raise

    def predict_objective(self, test):
        """Predicts the objective function value of the given tests.

        Args:
          test (np.ndarray): Array of shape (N, self.input_ndimension).

        Returns:
          output (np.ndarray): Array of shape (N, 1).

        Raises:
        """

        try:
            return self._predict_objective(test, self.device)
        except:
            raise

