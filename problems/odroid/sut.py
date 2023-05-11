import os

import numpy as np

from stgem.sut import SUT, SUTOutput, SUTInput
from util import generate_odroid_data

class OdroidSUT(SUT):
    """Implements the Odroid system under test.

    The input is a configuration of 6 parameters in [-1, 1], and the output is
    a 3-tuple (POWER, PERFORMANCE, EFFICIENCY)."""

    def __init__(self, parameters):
        super().__init__(parameters)

        self.idim = 6
        self.odim = 3
        self.outputs = ["POWER", "PERFORMANCE", "EFFICIENCY"]
        self.input_range = [[-1, 1] for _ in range(self.idim)]
        self.output_range = [[0, 9], [1850000, 16120770000], [4790000, 8129710000]]

        self.ndimensions = None
        self.dataX = None
        self.dataY = None
        self.scaleX = None
        self.scaleY1 = None
        self.scaleY2 = None
        self.scaleY3 = None

        try:
            self._load_odroid_data()
        except:
            raise

    def _load_odroid_data(self):
        # Check if we have a npy file. Otherwise we attempt to generate such a file
        # from a csv file.
        if not os.path.exists(self.data_file):
            if not self.data_file.endswith(".npy"):
                raise Exception("The Odroid data file does not have extension .npy.")
            csv_file = f"{self.data_file[:-4]}.csv"
            if not os.path.exists(csv_file):
                raise Exception(
                    f"No Odroid csv file '{csv_file}' available for data generation."
                )
            generate_odroid_data(csv_file)

        data = np.load(self.data_file)

        # Set number of input dimensions.
        self.ndimensions = 6

        self.dataX = data[:, 0 : self.ndimensions]
        self.dataY = data[:, self.ndimensions :]

        # Normalize the inputs to [-1, 1].
        self.scaleX = self.dataX.max(axis=0)
        self.dataX = (self.dataX / self.scaleX) * 2 - 1

    def _execute_test(self, sut_input):
        """
        Execute the given tests on the SUT. As not all possible parameters have a
        test value in the data, we find the closest test from the test data
        (Euclidean distance) and return its value.

        Args:
          test (np.ndarray): Array with shape (1,N) or (N) with
                             N = self.idim of floats in [-1, 1].

        Returns:
          result (np.ndarray): Array of shape (3) of floats in [0, 1].
        """

        test = sut_input.inputs
        if test.shape not in [(1, self.idim), (self.idim,)]:
            raise ValueError("Input array expected to have shape (1, {0}) or ({0}).".format(self.ndimensions))

        distances = np.sum((self.dataX - test)**2, axis=1)
        retdata = self.dataY[np.argmin(distances)]
        return SUTOutput(retdata, None, None, None)

