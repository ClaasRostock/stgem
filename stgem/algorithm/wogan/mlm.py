import torch
import torch.nn as nn
import torch.nn.functional as F

class WOGAN_NN(nn.Module):
    """Base class for simple dense neural networks."""

    def __init__(self, input_shape, hidden_neurons, output_shape, output_activation, hidden_activation, batch_normalization=False, layer_normalization=False):
        super().__init__()

        # The dimension of the input vector.
        self.input_shape = input_shape
        # The dimension of the output vector.
        self.output_shape = output_shape
        # List of numbers of neurons in the hidden layers.
        self.hidden_neurons = hidden_neurons
        # Use batch normalization before each activation (except the last one).
        self.batch_normalization = batch_normalization
        # Use layer normalization before each activation (except the last one).
        self.layer_normalization = layer_normalization

        if self.batch_normalization and self.layer_normalization:
            raise Exception("Cannot use both batch normalization and layer normalization (not recommended).")

        # Map for activations.
        activations = {"leaky_relu": F.leaky_relu,
                       "linear": nn.Identity(),
                       "relu": F.relu,
                       "sigmoid": torch.sigmoid,
                       "tanh": torch.tanh}

        # Hidden layer activation.
        if hidden_activation not in activations:
            raise Exception(f"Unknown activation function '{hidden_activation}'.")
        self.hidden_activation = activations[hidden_activation]

        # Output activation.
        if output_activation not in activations:
            raise Exception(f"Unknown activation function '{output_activation}'.")
        self.output_activation = activations[output_activation]

        # We use fully connected layers with the specified number of neurons.
        self.top = nn.Linear(self.input_shape, self.hidden_neurons[0])
        self.hidden = nn.ModuleList()
        if self.batch_normalization:
            self.norm = nn.ModuleList([nn.BatchNorm1d(self.hidden_neurons[0])])
        if self.layer_normalization:
            self.norm = nn.ModuleList([nn.LayerNorm(self.hidden_neurons[0])])
        for i, neurons in enumerate(self.hidden_neurons[1:]):
            self.hidden.append(nn.Linear(self.hidden_neurons[i], neurons))
            if self.batch_normalization:
                self.norm.append(nn.BatchNorm1d(neurons))
            if self.layer_normalization:
                self.norm.append(nn.LayerNorm(neurons))
        self.bottom = nn.Linear(self.hidden_neurons[-1], self.output_shape)
        if self.batch_normalization:
            self.norm.append(nn.BatchNorm1d(self.output_shape))
        if self.layer_normalization:
            self.norm.append(nn.LayerNorm(self.output_shape))

    def forward(self, x):
        """:meta private:"""
        x = self.hidden_activation(self.top(x))
        for i, L in enumerate(self.hidden):
            L = L.to(x.device)
            if self.batch_normalization or self.layer_normalization:
                x = self.hidden_activation(self.norm[i](L(x)))
            else:
                x = self.hidden_activation(L(x))
        if self.batch_normalization or self.layer_normalization:
            x = self.output_activation(self.norm[-1](self.bottom(x)))
        else:
            x = self.output_activation(self.bottom(x))

        return x

class CriticNetwork(WOGAN_NN):
    """Define the neural network model for the WGAN critic."""

    def __init__(self, input_shape, hidden_neurons, hidden_activation="leaky_relu", batch_normalization=False, layer_normalization=False):
        super().__init__(input_shape=input_shape,
                         hidden_neurons=hidden_neurons,
                         output_shape=1,
                         output_activation="linear",
                         hidden_activation=hidden_activation,
                         batch_normalization=batch_normalization,
                         layer_normalization=layer_normalization
        )

class GeneratorNetwork(WOGAN_NN):
    """Define the neural network model for the WGAN generator."""

    def __init__(self, noise_dim, hidden_neurons, output_shape, hidden_activation="relu", batch_normalization=False, layer_normalization=False):
        super().__init__(input_shape=noise_dim,
                         hidden_neurons=hidden_neurons,
                         output_shape=output_shape,
                         output_activation="tanh",
                         hidden_activation=hidden_activation,
                         batch_normalization=batch_normalization,
                         layer_normalization=layer_normalization
                        )

class AnalyzerNetwork(WOGAN_NN):
    """Define a regression neural network model for the WOGAN analyzer."""

    def __init__(self, input_shape, hidden_neurons, hidden_activation="relu", layer_normalization=False):
        super().__init__(input_shape=input_shape,
                         hidden_neurons=hidden_neurons,
                         output_shape=1,
                         output_activation="sigmoid",
                         hidden_activation=hidden_activation,
                         layer_normalization=layer_normalization
                        )
    
class AnalyzerNetwork_classifier(WOGAN_NN):
    """Define a classification neural network model for the WOGAN analyzer."""

    def __init__(self, classes, input_shape, hidden_neurons):
        # Number of classes.
        self.classes = classes
        super().__init__(input_shape=input_shape,
                         hidden_neurons=hidden_neurons,
                         output_shape=self.classes,
                         output_activation="linear",
                         hidden_activation="relu",
                         batch_normalization=True
                        )

class AnalyzerNetwork_conv(nn.Module):
    """Defines a neural network model for the WOGAN analyzer which uses 1D
    convolution."""

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
