import torch
import torch.nn as nn
import torch.nn.functional as F

class GeneratorNetwork(nn.Module):
    """Defines the neural network model for the GAN generator. """

    def __init__(self, noise_dim, output_shape, hidden_neurons, hidden_activation):
        super().__init__()

        # The dimension of the input vector.
        self.input_shape = noise_dim
        # The dimension of the output vector.
        self.output_shape = output_shape
        # List of numbers of neurons in the hidden layers.
        self.hidden_neurons = hidden_neurons

        activations = {"leaky_relu": F.leaky_relu,
                       "linear": nn.Identity(),
                       "relu": F.relu,
                       "sigmoid": torch.sigmoid,
                       "tanh": torch.tanh}

        if hidden_activation not in activations:
            raise Exception(f"Unknown activation function '{hidden_activation}'.")
        self.hidden_activation = activations[hidden_activation]

        self.layers = nn.ModuleList()

        # We use Xavier (Glorot) initialization with tanh and sigmoid
        # activations and Kaiming (He) initialization with ReLU.

        # Top layer.
        top = nn.Linear(self.input_shape, self.hidden_neurons[0])
        torch.nn.init.kaiming_uniform_(top.weight)
        self.layers.append(top)

        # Hidden layers.
        for i, neurons in enumerate(self.hidden_neurons[1:]):
            hidden_layer = nn.Linear(self.hidden_neurons[i], neurons)
            if hidden_activation in ["relu", "leaky_relu"]:
                torch.nn.init.kaiming_uniform_(hidden_layer.weight)
            else:
                torch.nn.init.xavier_uniform_(hidden_layer.weight)
            self.layers.append(hidden_layer)

        # Bottom layer.
        bottom = nn.Linear(self.hidden_neurons[-1], self.output_shape)
        torch.nn.init.xavier_uniform_(bottom.weight)
        self.layers.append(bottom)

    def forward(self, x):
        """:meta private:"""
        for layer in self.layers[:-1]:
            x = self.hidden_activation(layer(x))
        x = torch.tanh(self.layers[-1](x)) # Squash the output values to [-1, 1].

        return x

class DiscriminatorNetwork(nn.Module):
    """Defines the neural network model for the GAN discriminator."""

    def __init__(self, input_shape, hidden_neurons, hidden_activation, discriminator_output_activation="sigmoid"):
        super().__init__()

        # The dimension of the input vector.
        self.input_shape = input_shape
        # List of numbers of neurons in the hidden layers.
        self.hidden_neurons = hidden_neurons

        activations = {"leaky_relu": F.leaky_relu,
                       "linear": nn.Identity(),
                       "relu": F.relu,
                       "sigmoid": torch.sigmoid,
                       "tanh": torch.tanh}

        if hidden_activation not in activations:
            raise Exception(f"Unknown activation function '{hidden_activation}'.")
        self.hidden_activation = activations[hidden_activation]

        self.layers = nn.ModuleList()

        # Top layer.
        top = nn.Linear(self.input_shape, self.hidden_neurons[0])
        torch.nn.init.kaiming_uniform_(top.weight)
        self.layers.append(top)

        # Hidden layers.
        for i, neurons in enumerate(self.hidden_neurons[1:]):
            hidden_layer = nn.Linear(self.hidden_neurons[i], neurons)
            if hidden_activation in ["relu", "leaky_relu"]:
                torch.nn.init.kaiming_uniform_(hidden_layer.weight)
            else:
                torch.nn.init.xavier_uniform_(hidden_layer.weight)
            self.layers.append(hidden_layer)

        # Bottom layer.
        bottom = nn.Linear(self.hidden_neurons[-1], 1)
        torch.nn.init.xavier_uniform_(bottom.weight)
        self.layers.append(bottom)

        # Select the output activation function.
        a = discriminator_output_activation
        if a == "linear":
            self.output_activation = torch.nn.Identity()
        elif a == "sigmoid":
            self.output_activation = torch.sigmoid
        else:
            raise Exception(f"Unknown output activation function '{a}'.")

    def forward(self, x):
        """:meta private:"""
        for layer in self.layers[:-1]:
            x = self.hidden_activation(layer(x))
        x = self.output_activation(self.layers[-1](x))

        return x

class DiscriminatorNetwork1dConv(nn.Module):
    """Defines a neural network module for the GAN discriminator which uses 1D
    convolution. Useful when the test can be viewed as a time series."""

    def __init__(self, input_shape, feature_maps, kernel_sizes, convolution_activation, dense_neurons):
        """
        Creates a convolutional network with the following structure. For each
        number in the list feature_maps, create a 1D convolutional layer with
        the specified number of feature maps followed by a maxpool layer. The
        kernel sizes of the convolutional layer and the maxpool layer are
        specified by the first tuple in kernel_sizes. We use the specified
        activation function after each convolution layer. After the
        convolutions and maxpools, we use a single dense layer of the specified
        size with sigmoid activation.

        We always pad K-1 zeros when K is the kernel size. For now, we use a
        stride of 1.
        """

        super().__init__()

        # The dimension of the input vector.
        self.input_shape = input_shape
        # Number of feature maps.
        self.feature_maps = feature_maps
        # Corresponding kernel sizes.
        self.kernel_sizes = kernel_sizes
        # Number of neurons on the bottom dense layer.
        self.dense_neurons = dense_neurons

        activations = {"leaky_relu": F.leaky_relu,
                       "linear": nn.Identity(),
                       "relu": F.relu,
                       "sigmoid": torch.sigmoid,
                       "tanh": torch.tanh}

        # Convolution activation function.
        if convolution_activation not in activations:
            raise Exception(f"Unknown activation function '{convolution_activation}'.")
        self.convolution_activation = activations[convolution_activation]

        # Define the convolutional layers and maxpool layers. Compute
        # simultaneously the number of inputs for the final dense layer by
        # feeding an input vector through the network.
        self.conv_layers = nn.ModuleList()
        self.maxpool_layers = nn.ModuleList()
        x = torch.zeros(1, 1, self.input_shape)
        C = nn.Conv1d(in_channels=1,
                      out_channels=feature_maps[0],
                      kernel_size=kernel_sizes[0][0],
                      padding=kernel_sizes[0][0]-1
                     )
        M = nn.MaxPool1d(kernel_size=kernel_sizes[0][1],
                         padding=kernel_sizes[0][1]-1
                        )
        x = M(C(x))
        self.conv_layers.append(C)
        self.maxpool_layers.append(M)
        for i, K in enumerate(feature_maps[1:]):
            C = nn.Conv1d(in_channels=feature_maps[i],
                          out_channels=K,
                          kernel_size=kernel_sizes[i+1][0],
                          padding=kernel_sizes[i+1][0]-1
                         )
            torch.nn.init.kaiming_uniform_(C.weight)
            M = nn.MaxPool1d(kernel_size=kernel_sizes[i+1][1],
                             padding=kernel_sizes[i+1][1]-1
                            )
            x = M(C(x))
            self.conv_layers.append(C)
            self.maxpool_layers.append(M)

        # Define the final dense layer.
        self.flatten = nn.Flatten()
        I = x.reshape(-1).size()[0]
        self.dense_layer = nn.Linear(I, self.dense_neurons)
        torch.nn.init.xavier_uniform_(self.dense_layer.weight)
        self.bottom = nn.Linear(self.dense_neurons, 1)

    def forward(self, x):
        """:meta private:"""
        # Reshape to 1 channel.
        x = x.view(x.size()[0], 1, x.size()[1])
        for n in range(len(self.conv_layers)):
            C = self.conv_layers[n].to(x.device)
            M = self.maxpool_layers[n].to(x.device)
            x = self.convolution_activation(C(x))
            x = M(x)

        x = self.flatten(x)
        x = self.dense_layer(x)
        x = torch.sigmoid(self.bottom(x))

        return x

