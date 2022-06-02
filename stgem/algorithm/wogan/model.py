#!/usr/bin/python3
# -*- coding: utf-8 -*-

import importlib

import numpy as np
import torch
import copy
from stgem import algorithm
from stgem.algorithm import Model

class WOGAN_Model(Model):
    """
    Implements the WOGAN model.
    """

    default_parameters = {
        "critic_optimizer": "Adam",
        "critic_lr": 0.001,
        "critic_betas": [0, 0.9],
        "generator_optimizer": "Adam",
        "generator_lr": 0.001,
        "generator_betas": [0, 0.9],
        "noise_batch_size": 32,
        "gp_coefficient": 10,
        "eps": 1e-6,
        "report_wd": True,
        "analyzer": "Analyzer_NN",
        "analyzer_parameters": {
            "optimizer": "Adam",
            "lr": 0.005,
            "betas": [0, 0.9],
            "loss": "MSE,Logit",
            "l2_regularization_coef": 0.001,
            "analyzer_mlm": "AnalyzerNetwork",
            "analyzer_mlm_parameters": {
                "hidden_neurons": [64, 64],
                "layer_normalization": False
            },
        },
        "generator_mlm": "GeneratorNetwork",
        "generator_mlm_parameters": {
            "noise_dim": 20,
            "hidden_neurons": [128, 128],
            "batch_normalization": False,
            "layer_normalization": False
        },
        "critic_mlm": "CriticNetwork",
        "critic_mlm_parameters": {"hidden_neurons": [128, 128]},
        "train_settings_init": {
            "epochs": 3,
            "analyzer_epochs": 20,
            "critic_steps": 5,
            "generator_steps": 1
        },
        "train_settings": {
            "epochs": 10,
            "analyzer_epochs": 1,
            "critic_steps": 5,
            "generator_steps": 1
        }
    }

    def setup(self, search_space, device, logger):
        super().setup(search_space, device, logger)

        self.noise_dim = self.generator_mlm_parameters["noise_dim"]

        # Infer input and output dimensions for ML models.
        self.parameters["analyzer_parameters"]["analyzer_mlm_parameters"]["input_shape"] = self.search_space.input_dimension
        self.parameters["generator_mlm_parameters"]["output_shape"] = self.search_space.input_dimension
        self.parameters["critic_mlm_parameters"]["input_shape"] = self.search_space.input_dimension

        # Load the specified analyzer and initialize it.
        module = importlib.import_module("stgem.algorithm.wogan.analyzer")
        analyzer_class = getattr(module, self.analyzer)
        self.modelA = analyzer_class(parameters=self.analyzer_parameters)
        self.modelA.setup(device=self.device, logger=self.logger)

        # Load the specified generator and critic and initialize them.
        module = importlib.import_module("stgem.algorithm.wogan.mlm")
        generator_class = getattr(module, self.generator_mlm)
        critic_class = getattr(module, self.critic_mlm)
        self.modelG = generator_class(**self.generator_mlm_parameters).to(self.device)
        self.modelC = critic_class(**self.critic_mlm_parameters).to(self.device)

        # Load the specified optimizers.
        module = importlib.import_module("torch.optim")
        generator_optimizer_class = getattr(module, self.generator_optimizer)
        generator_parameters = {k[10:]:v for k, v in self.parameters.items() if k.startswith("generator")}
        self.optimizerG = generator_optimizer_class(self.modelG.parameters(), **algorithm.filter_arguments(generator_parameters, generator_optimizer_class))
        critic_optimizer_class = getattr(module, self.critic_optimizer)
        critic_parameters = {k[7:]:v for k, v in self.parameters.items() if k.startswith("critic")}
        self.optimizerC = critic_optimizer_class(self.modelC.parameters(), **algorithm.filter_arguments(critic_parameters, critic_optimizer_class))

        # Setup loss saving etc.
        self.losses_A = []
        self.losses_C = []
        self.gradient_penalties = []
        self.losses_G = []

        # We set single = True in case setup is called repeatedly.
        self.perf.save_history("analyzer_loss", self.losses_A, single=True)
        self.perf.save_history("critic_loss", self.losses_C, single=True)
        self.perf.save_history("gradient_penalty", self.gradient_penalties, single=True)
        self.perf.save_history("generator_loss", self.losses_G, single=True)

    def train_analyzer_with_batch(self, data_X, data_Y, train_settings):
        """
        Train the analyzer part of the model with a batch of training data.

        Args:
          data_X (np.ndarray):   Array of tests of shape
                                 (N, self.sut.ndimensions).
          data_Y (np.ndarray):   Array of test outputs of shape (N, 1).
          train_settings (dict): A dictionary setting up the number of training
                                 epochs for various parts of the model. The
                                 keys are as follows:

                                   analyzer_epochs: How many total runs are
                                   made with the given training data.

                                 The default for each missing key is 1. Keys
                                 not found above are ignored.
        """

        losses = []
        for _ in range(train_settings["analyzer_epochs"]):
            loss = self.modelA.train_with_batch(data_X, data_Y, train_settings)
            losses.append(loss)

        m = np.mean(losses)
        self.losses_A.append(losses)
        self.log("Analyzer epochs {}, Loss: {} -> {} (mean {})".format(train_settings["analyzer_epochs"], losses[0], losses[-1], m))

    def train_with_batch(self, data_X, train_settings):
        """
        Train the WGAN with a batch of training data.

        Args:
          data_X (np.ndarray):   Array of tests of shape
                                 (M, self.sut.ndimensions).
          train_settings (dict): A dictionary setting up the number of training
                                 epochs for various parts of the model. The
                                 keys are as follows:

                                   critic_steps: How many times the critic is
                                   trained per epoch.

                                   generator_steps: How many times the
                                   generator is trained per epoch.

                                 The default for each missing key is 1. Keys
                                 not found above are ignored.
        """

        data_X = torch.from_numpy(data_X).float().to(self.device)

        # Unpack values from the epochs dictionary.
        critic_steps = train_settings["critic_steps"] if "critic_steps" in train_settings else 1
        generator_steps = train_settings["generator_steps"] if "generator_steps" in train_settings else 1

        # Save the training modes for later restoring.
        training_C = self.modelC.training
        training_G = self.modelG.training

        # Train the critic.
        # ---------------------------------------------------------------------
        self.modelC.train(True)
        losses = torch.zeros(critic_steps)
        gradient_penalties = torch.zeros(critic_steps)
        for m in range(critic_steps):
            # Here the mini batch size of the WGAN-GP is set to be the number
            # of training samples for the critic
            M = data_X.shape[0]

            # Loss on real data.
            real_inputs = data_X
            real_outputs = self.modelC(real_inputs)
            real_loss = real_outputs.mean(0)

            # Loss on generated data.
            # For now we use as much generated data as we have real data.
            noise = (2*torch.rand(size=(M, self.modelG.input_shape)) - 1).to(self.device)
            fake_inputs = self.modelG(noise)
            fake_outputs = self.modelC(fake_inputs)
            fake_loss = fake_outputs.mean(0)

            # Gradient penalty.
            # Compute interpolated data.
            e = torch.rand(size=(M, 1)).to(self.device)
            interpolated_inputs = e * real_inputs + (1 - e) * fake_inputs
            # Get critic output on interpolated data.
            interpolated_outputs = self.modelC(interpolated_inputs)
            # Compute the gradients wrt to the interpolated inputs.
            # Warning: Showing the validity of the following line requires some
            # pen and paper calculations.
            gradients = torch.autograd.grad(inputs=interpolated_inputs,
                                            outputs=interpolated_outputs,
                                            grad_outputs=torch.ones_like(interpolated_outputs).to(self.device),
                                            create_graph=True,
                                            retain_graph=True,
                                           )[0]

            # We add epsilon for stability.
            epsilon = self.eps if "eps" in self.parameters else 1e-7
            gradients_norms = torch.sqrt(torch.sum(gradients**2, dim=1) + epsilon)
            gradient_penalty = ((gradients_norms - 1) ** 2).mean()
            # gradient_penalty = ((torch.linalg.norm(gradients, dim=1) - 1)**2).mean()

            C_loss = fake_loss - real_loss + self.gp_coefficient*gradient_penalty
            losses[m] = C_loss
            gradient_penalties[m] = self.gp_coefficient*gradient_penalty
            self.optimizerC.zero_grad()
            C_loss.backward()
            self.optimizerC.step()

        self.losses_C.append(losses)
        self.gradient_penalties += gradient_penalties
        m1 = losses.mean()
        m2 = gradient_penalties.mean()
        self.log("Critic steps {}, Loss: {} -> {} (mean {}), GP: {} -> {} (mean {})".format(critic_steps, losses[0], losses[-1], m1, gradient_penalties[0], gradient_penalties[-1], m2))

        self.modelC.train(False)

        # Visualize the computational graph.
        # print(make_dot(C_loss, params=dict(self.modelC.named_parameters())))

        # Train the generator.
        # ---------------------------------------------------------------------
        self.modelG.train(True)
        losses = torch.zeros(generator_steps)
        noise_batch_size = self.noise_batch_size
        for m in range(generator_steps):
            noise = (2*torch.rand(size=(noise_batch_size, self.modelG.input_shape)) - 1).to(self.device)
            outputs = self.modelC(self.modelG(noise))

            G_loss = -outputs.mean(0)
            losses[m] = G_loss
            self.optimizerG.zero_grad()
            G_loss.backward()
            self.optimizerG.step()

        m = losses.mean()
        self.losses_G.append(losses)
        self.log("Generator steps {}, Loss: {} -> {} (mean {})".format(generator_steps, losses[0], losses[-1], m))

        self.modelG.train(False)

        report_wd = self.report_wd if "report_wd" in self.parameters else False
        if report_wd:
            # Same as above in critic training.
            real_inputs = data_X
            real_outputs = self.modelC(real_inputs)
            real_loss = real_outputs.mean(0)

            # For now we use as much generated data as we have real data.
            noise = (2*torch.rand(size=(real_inputs.shape[0], self.modelG.input_shape)) - 1).to(self.device)
            fake_inputs = self.modelG(noise)
            fake_outputs = self.modelC(fake_inputs)
            fake_loss = fake_outputs.mean(0)

            W_distance = real_loss - fake_loss

            self.log("Batch W. distance: {}".format(W_distance[0]))

        # Visualize the computational graph.
        # print(make_dot(G_loss, params=dict(self.modelG.named_parameters())))

        # Restore the training modes.
        self.modelC.train(training_C)
        self.modelG.train(training_G)

    def generate_test(self, N=1):
        """
        Generate N random tests.

        Args:
          N (int): Number of tests to be generated.

        Returns:
          output (np.ndarray): Array of shape (N, self.sut.ndimensions).
        """

        if N <= 0:
            raise ValueError("The number of tests should be positive.")

        training_G = self.modelG.training
        # Generate uniform noise in [-1, 1].
        noise = (2*torch.rand(size=(N, self.modelG.input_shape)) - 1).to(self.device)
        self.modelG.train(False)
        result = self.modelG(noise).cpu().detach().numpy()
        self.modelG.train(training_G)
        return result

    def predict_objective(self, test):
        """
        Predicts the objective function value for the given test.

        Args:
          test (np.ndarray): Array with shape (1, N) or (N).

        Returns:
          output (float)
        """

        return self.modelA.predict(test)

