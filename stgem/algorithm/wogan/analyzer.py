import importlib

import numpy as np
import torch

from stgem import algorithm

class Analyzer:
    """Base class for WOGAN analyzers."""

    default_parameters = {}

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = copy.deepcopy(self.default_parameters)
        self.parameters = parameters

    def setup(self, device, logger=None):
        self.device = device

        self.logger = logger
        self.log = lambda s: self.logger.model.info(s) if logger is not None else None

        self.modelA = None

    def __getattr__(self, name):
        if "parameters" in self.__dict__ and name in self.parameters:
            return self.parameters.get(name)

        raise AttributeError(name)

    def train_with_batch(self, dataX, dataY, train_settings, log=False):
        raise NotImplementedError()

    def predict(self, test):
        raise NotImplementedError()

class Analyzer_NN(Analyzer):
    """
    Analyzer based on a neural network for regression.
    """

    def setup(self, device, logger):
        super().setup(device, logger)

        # Load the specified analyzer machine learning model and initialize it.
        module = importlib.import_module("stgem.algorithm.wogan.mlm")
        analyzer_class = getattr(module, self.analyzer_mlm)
        self.modelA = analyzer_class(**algorithm.filter_arguments(self.analyzer_mlm_parameters, analyzer_class)).to(self.device)

        # Load the specified optimizer.
        module = importlib.import_module("torch.optim")
        optimizer_class = getattr(module, self.optimizer)
        self.optimizerA = optimizer_class(self.modelA.parameters(), **algorithm.filter_arguments(self.parameters, optimizer_class))

        # Loss functions.
        def get_loss(loss_s):
            loss_s = loss_s.lower()
            if loss_s == "crossentropy":
                loss = torch.nn.CrossEntropyLoss()
            elif loss_s == "mse":
                loss = torch.nn.MSELoss()
            elif loss_s == "l1":
                loss = torch.nn.L1Loss()
            elif loss_s in ["mse,logit", "l1,logit"]:
                # When doing regression with values in [0, 1], we can use a
                # logit transformation to map the values from [0, 1] to \R
                # to make errors near 0 and 1 more drastic. Since logit is
                # undefined in 0 and 1, we actually first transform the values
                # to the interval [0.01, 0.99].
                g = torch.nn.MSELoss() if loss_s == "mse,logit" else torch.nn.L1Loss()
                def f(X, Y):
                    return g(torch.logit(0.98*X + 0.01), torch.logit(0.98*Y + 0.01))

                loss = f
            else:
                raise Exception("Unknown loss function '{}'.".format(loss_s))

            return loss

        try:
            self.loss_A = get_loss(self.loss)
        except:
            raise

    def analyzer_loss(self, data_X, data_Y):
        """
        Computes the analyzer loss for data_X given real outputs data_Y.
        """

        # Compute the configured loss.
        model_loss = self.loss_A(data_X, data_Y)

        # Compute L2 regularization if needed.
        l2_regularization = 0
        if "l2_regularization_coef" in self.parameters and self.l2_regularization_coef != 0:
            for parameter in self.modelA.parameters():
                l2_regularization += torch.sum(torch.square(parameter))
        else:
            self.parameters["l2_regularization_coef"] = 0

        return model_loss + self.l2_regularization_coef*l2_regularization

    def _train_with_batch(self, data_X, data_Y, train_settings):
        # Save the training modes for later restoring.
        training_A = self.modelA.training

        # Train the analyzer.
        # ---------------------------------------------------------------------
        self.modelA.train(True)
        A_loss = self.analyzer_loss(self.modelA(data_X), data_Y)
        self.optimizerA.zero_grad()
        A_loss.backward()
        self.optimizerA.step()

        # Visualize the computational graph.
        # print(make_dot(A_loss, params=dict(self.modelA.named_parameters())))

        self.modelA.train(training_A)

        return A_loss.item()

    def train_with_batch(self, data_X, data_Y, train_settings):
        """
        Train the analyzer part of the model with a batch of training data.

        Args:
            data_X (np.ndarray): Array of tests of shape
                (N, self.modelA.input_shape).
            data_Y (np.ndarray): Array of test outputs of shape (N, 1).
                train_settings (dict): A dictionary for setting up the training.
                Currently all keys are ignored.
        """

        data_X = torch.from_numpy(data_X).float().to(self.device)
        data_Y = torch.from_numpy(data_Y).float().to(self.device)
        return self._train_with_batch(data_X, data_Y, train_settings)

    def predict(self, test):
        """
        Predicts the objective function value of the given test.

        Args:
            test (np.ndarray): Array with shape (1, N) or (N)
                where N is self.modelA.input_shape.

        Returns:
            output (np.ndarray): Array with shape (1).
        """

        test_tensor = torch.from_numpy(test).float().to(self.device)
        return np.array([self.modelA(test_tensor).cpu().detach().numpy()])

class Analyzer_NN_classifier(Analyzer_NN):
    """
    Analyzer using classification in place of regression.
    """

    def __init__(self, parameters, logger=None):
        super().__init__(parameters, logger)

    def _put_to_class(self, Y):
        """
        Classifies the floats in Y.
        """

        Z = (Y*self.classes).int()
        return (Z - (Z == self.classes).int()).long()

    def train_with_batch(self, data_X, data_Y, train_settings, log=False):
        """
        Train the analyzer part of the model with a batch of training data.

        Args:
            data_X (np.ndarray):   Array of tests of shape
                (N, self.modelA.input_shape).
            data_Y (np.ndarray):   Array of test outputs of shape (N, 1).
            train_settings (dict): A dictionary for setting up the training.
                Currently all keys are ignored.
        """

        data_X = torch.from_numpy(data_X).float().to(self.device)
        data_Y = self.put_to_class(torch.from_numpy(data_Y).float().to(self.device))
        return self._train_with_batch(data_X, data_Y)

    def predict(self, test):
        """
        Predicts the objective function value of the given test.

        Args:
            test (np.ndarray): Array of shape (N, self.modelA.input_shape).

        Returns:
            output (np.ndarray): Array of shape (N, 1).
        """

        training_A = self.modelA.training
        self.modelA.train(False)

        test_tensor = torch.from_numpy(test).float().to(self.device)
        p = self.modelA(test_tensor)
        result = torch.argmax(p, dim=1)/self.classes + 1/(2*self.classes)

        self.modelA.train(training_A)
        return result.cpu().detach().numpy().reshape(-1, 1)

