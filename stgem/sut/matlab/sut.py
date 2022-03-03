#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys

import numpy as np

try:
    import matlab
    import matlab.engine
except ImportError:
    raise Exception("Error importing Python Matlab engine for AT.")

from stgem.sut import SUT

class Matlab_Simulink_Signal(SUT):
    """
    Generic class for using Matlab Simulink models using signal inputs.
    """

    def __init__(self, parameters):
        super().__init__(parameters)

        # How often input signals are sampled for execution (in time units).
        self.steps = self.simulation_time // self.sampling_step

        if not os.path.exists(self.model_file + ".mdl") and not os.path.exists(self.model_file + ".slx"):
            raise Exception("Neither '{0}.mdl' nor '{0}.slx' exists.".format(self.model_file))

        self.MODEL_NAME = os.path.basename(self.model_file)
        # Initialize the Matlab engine (takes a lot of time).
        self.engine = matlab.engine.start_matlab()
        # The path for the model file.
        self.engine.addpath(os.path.dirname(self.model_file))
        # Get options for the model (takes a lot of time).
        model_opts = self.engine.simget(self.MODEL_NAME)
        # Set the output format of the model.
        # TODO: Should this be done for models other than AT?
        self.model_opts = self.engine.simset(model_opts, "SaveFormat", "Array")

    def _execute_test_simulink(self, timestamps, signals):
        """
        Execute a test with the given input signals.
        """

        # Setup the parameters for Matlab.
        simulation_time = matlab.double([0, timestamps[-1]])
        model_input = matlab.double(np.row_stack((timestamps, *signals)).T.tolist())

        # Run the simulation.
        out_timestamps, _, data = self.engine.sim(self.MODEL_NAME, simulation_time, self.model_opts, model_input, nargout=self.odim)

        timestamps_array = np.array(out_timestamps).flatten()
        data_array = np.array(data)

        # Reshape the data.
        result = np.zeros(shape=(self.odim, len(timestamps_array)))
        for i in range(self.odim):
            result[i] = data_array[:, i]

        return timestamps_array, result

    def _execute_test(self, timestamps, signals):
        return self._execute_test_simulink(timestamps, signals)

class Matlab_Simulink(Matlab_Simulink_Signal):
    """
    Generic class for using Matlab Simulink models using piecewise constant
    inputs. We assume that the input is a vector of numbers in [-1, 1] and that
    the first K numbers specify the pieces of the first signal, the next K
    numbers the second signal, etc. The number K is specified by the simulation
    time and the length of the time interval during which the signal must stay
    constant.
    """

    def __init__(self, parameters):
        try:
            super().__init__(parameters)
        except:
            raise

        # How many inputs we have for each signal.
        self.pieces = self.simulation_time // self.time_slice

    def initialize(self):
        # Redefine input dimension.
        self.signals = self.idim
        self.idim = self.idim*self.pieces

        # Redo input ranges for vector inputs.
        new = []
        for i in range(len(self.irange)):
            for _ in range(self.pieces):
                new.append(self.irange[i])
        self.irange = new

    def _execute_test(self, test):
        """
        Execute the given test on the SUT.

        Args:
          test (np.ndarray): Array of floats with shape (1,N) or (N) with
                             N = self.idim.

        Returns:
          timestamps (np.ndarray): Array of shape (M, 1).
          signals (np.ndarray): Array of shape (self.odim, M).
        """

        test = self.descale(test.reshape(1, -1), self.irange).reshape(-1)

        # Convert the test input to signals.
        idx = lambda t: int(t // self.time_slice) if t < self.simulation_time else self.pieces - 1
        signal_f = []
        for i in range(self.signals):
            signal_f.append(lambda t: test[i*self.pieces + idx(t)])
        timestamps = np.linspace(0, self.simulation_time, int(self.steps))
        signals = []
        for i in range(self.signals):
            signals.append(np.asarray([signal_f[i](t) for t in timestamps]))

        # Execute the test.
        return self._execute_test_simulink(timestamps, signals)

    def execute_random_test(self):
        """
        Execute a random tests and return it and its output.

        Returns:
          test (np.ndarray): Array of shape (2*self.pieces) of floats in [-1, 1].
          timestamps (np.ndarray): Array of shape (N, 1).
          signals (np.ndarray): Array of shape (3, N).
        """

        test = self.sample_input_space()
        timestamps, signals = self.execute_test(test)
        return test, timestamps, signals


class Matlab(SUT):
    """
    Implements a SUT in matlab.
    """

    def __init__(self, parameters):
        SUT.__init__(self, parameters)

        self.parameters = parameters

        self.idim = len(self.parameters["input_range"])
        self.odim = len(self.parameters["output_range"])
        self.irange = np.asarray(self.parameters["input_range"])
        self.orange = np.asarray(self.parameters["output_range"])

        # start the matlab engine
        self.engine = matlab.engine.start_matlab()

    def _execute_test(self, test):
        test = self.descale(test.reshape(1, -1), self.irange).reshape(-1)

        # set matlab class directory, .m file
        self.engine.addpath(os.path.dirname(self.parameters["model_file"]))

        # make the matlab function from the input strings
        matlab_function_str = "self.engine.{}".format(os.path.basename(self.parameters["model_file"]))

        # create a callable function from the given string argument, from "model_file"
        # calls the matlab function with inputs list and get the output list
        # parse input parameters in any given dimension
        run_matlab_function = eval(matlab_function_str)([float(x) for x in test], nargout=1)

        return np.asarray([utpt for utpt in run_matlab_function])


