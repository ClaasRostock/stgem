# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.3.4
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---
%matplotlib widget
import os, sys

import numpy as np
import torch
import matplotlib.pyplot as plt

sys.path.append(os.path.join(".."))
from stgem.algorithm.ogan.mlm import GeneratorNetwork
from stgem.generator import STGEM, STGEMResult

# %% [markdown]
Here we setup identifiers for both validation data and the actual data from a
single benchmark. Edit the path as needed.

# %%
path = os.path.join("..", "problems", "arch-comp-2021")
validation_identifier = "AT1_validation"
data_identifier = "AT1_data"

validation_data_file = os.path.join(path, "{}.npy.gz".format(validation_identifier))
data_file = os.path.join(path, "{}.npy.gz".format(data_identifier))

# %% [markdown]
# # Load Validation Data

# %% [markdown]
This is a data file produced by
`problems/arch-comp-2021/create_validation_data.py`.

# %%
test_repository = STGEMResult.restore_from_file(validation_data_file).step_results[0].test_repository
X_v, _, Y_v = test_repository.get()
X_v = np.array([x.inputs for x in X_v])
Y_v = np.array(Y_v)

# %% [markdown]
# # Load Benchmark Data

# %% [markdown]
The current code assumes that OGAN algorithm was used as the second step. The
remaining code does not work correctly with other algorithms. In addition, we
assume that there is a single objective.

# %%
def get_model_loss(result, idx):
    """Returns the OGAN model indicated by the given index and the
    discriminator loss function."""

    # We assume a single objective.
    objective_idx = 0

    # Load a model.
    try:
        model_skeleton = result.step_results[1].models[idx][objective_idx]
    except IndexError:
        raise Exception("Unable to load model with index {}. Either the index is out of bounds or the replica data file does not contain saved models.")

    # TODO: remove these when done
    #model_skeleton.parameters["discriminator_mlm_parameters"]["convolution_activation"] = "leaky_relu"
    #del model_skeleton.parameters["discriminator_mlm_parameters"]["hidden_activation"]
    model_skeleton.parameters["generator_mlm_parameters"]["hidden_activation"] = "leaky_relu"

    # Get the loss of the model on the validation data.
    from stgem.sut import SearchSpace
    search_space = SearchSpace()
    search_space.input_dimension = model_skeleton.input_dimension

    from stgem.algorithm.ogan.model import OGAN_Model
    model = OGAN_Model.setup_from_skeleton(model_skeleton, search_space, torch.device("cpu"))

    loss = lambda X, Y: model.lossD(torch.from_numpy(X).float(), torch.from_numpy(Y).float()).cpu().detach().numpy()

    return model, loss

# %%
objective_idx = 0 # Which objective is used.
model_idx = 0 # Which model to load from the replica data.
result = STGEMResult.restore_from_file(data_file)
model, loss = get_model_loss(result, model_idx)

# %% [markdown]
# # Model Predictions on Validation Data

# %%
model_predictions = model.predict_objective(X_v)
print("Model loss on complete validation data:")
print(loss(model_predictions, Y_v))
print()
print("Prediction: Ground truth:")
for i, x in enumerate(X_v):
    print(model.predict_objective(x.reshape(1, -1))[0,0], Y_v[i][0])

# %% [markdown]
# # All Model Predictions on Validation Data

# %%
no_of_models = 225 # How many models were saved.
for idx in range(0, no_of_models):
    _model, _loss = get_model_loss(result, idx)
    model_predictions = _model.predict_objective(X_v)
    value = loss(model_predictions, Y_v)
    print("Model = {}, loss on validation = {}".format(idx, value))

# %% [markdown]
# # Plot Loss of Final Model over Epochs

# %%
epochs = model.train_settings["discriminator_epochs"]
step_tests = result.step_results[1].parameters["tests_executed"]
data = [result.test_repository.performance(i).obtain("discriminator_loss")[objective_idx] for i in step_tests]
data = np.array(data).reshape(-1)
fig = plt.figure()
plt.plot(np.arange(1, epochs + 1), data)

# %% [markdown]
# # Train New Discriminator

# %% [markdown]
Here we train a new discriminator based on the replica test repository data.
Its performance is measured by computing loss on the validation data. The
resulting discriminator is found in the variable `model`.

# %%
def loss_on_validation(model):
    model_predictions = model.predict_objective(X_v)
    return model.lossD(torch.from_numpy(model_predictions).float(), torch.from_numpy(Y_v).float()).cpu().detach().numpy()

# %%
X, _, Y = result.test_repository.get()
X = np.array([x.inputs for x in X])
Y = np.array(Y)

# Setup discriminator parameters.
#model.parameters["optimizer"] = "Adam"
#model.train_settings["discriminator_epochs"] = 30
#model.parameters["discriminator_lr"] = 0.005
#model.parameters["discriminator_mlm_parameters"]["hidden_neurons"] = [128,128,128]
#model.parameters["discriminator_mlm_parameters"]["feature_maps"] = [16,16]
#model.parameters["discriminator_mlm_parameters"]["kernel_sizes"] = [[2,2],[2,2]]
#model.parameters["discriminator_mlm_parameters"]["dense_neurons"] = 128
#model.parameters["discriminator_mlm_parameters"]["convolution_activation"] = "leaky_relu"

model.reset()

validation_losses = []
epochs = model.train_settings["discriminator_epochs"]
for i in range(epochs):
    model.train_with_batch(X, Y, train_settings=model.parameters["train_settings"])
    validation_losses.append(loss_on_validation(model))
    print("epoch = {:>2}, validation loss = {}".format(i + 1, validation_losses[-1]))

fig = plt.figure()
plt.plot(np.arange(1, epochs + 1), validation_losses)

# %% [markdown]
# # Train New Generator

# %% [markdown]
Here we train a new generator on the discriminator found in `model`. We report
the training losses.

# %%
def discriminator_loss_on_batch(model, batch_size):
    """Finds the discriminator loss on a random batch of inputs."""

    noise = 2*torch.rand(batch_size, model.modelD.input_shape) - 1
    inputs = noise.float().to("cpu")

    fake_label = torch.zeros(size=(batch_size, 1)).to("cpu")

    outputs = model.modelD(inputs)
    loss = model.lossD(outputs, fake_label)

    return loss.detach().cpu().item()

def generator_loss_on_batch(model, batch_size):
    """Finds the discriminator loss on a random batch of noise fed through the
    generator."""

    noise = 2*torch.rand(batch_size, model.modelG.input_shape) - 1
    inputs = noise.float().to("cpu")

    fake_label = torch.zeros(size=(batch_size, 1)).to("cpu")

    outputs = model.modelD(model.modelG(inputs))
    loss = model.lossG(outputs, fake_label)

    return loss.detach().cpu().item()

# %%
X = np.array([])
Y = np.array([])

discriminator_epochs_saved = model.parameters["train_settings"]["discriminator_epochs"]
epochs_saved = model.parameters["train_settings"]["epochs"]
model.parameters["train_settings"]["epochs"] = 1
model.parameters["train_settings"]["discriminator_epochs"] = 0

# Setup generator parameters.
#model.parameters["noise_batch_size"] = 12000
#model.parameters["generator_lr"] = 0.0001
#model.parameters["generator_mlm_parameters"]["noise_dim"] = 20
#model.parameters["generator_mlm_parameters"]["hidden_neurons"] = [128,128,128]
#model.parameters["generator_mlm_parameters"]["hidden_neurons"] = [64,64]

model.modelG = GeneratorNetwork(**model.generator_mlm_parameters)
model.optimizerG = torch.optim.Adam(model.modelG.parameters(), lr=model.generator_lr, betas=model.generator_betas)

model.parameters["train_settings"]["discriminator_epochs"] = discriminator_epochs_saved
model.parameters["train_settings"]["epochs"] = epochs_saved

model.train_with_batch(X, Y, train_settings=model.parameters["train_settings"])

# %%
batch_size = 500
# TODO: This needs to be updated to use the latest performance records. What does this do?
A = model.perf.histories["generator_loss"][-1][0]
B = model.perf.histories["generator_loss"][-1][-1]
print(f"training loss: {A} -> {B}")
print(f"noise batch loss: {generator_loss_on_batch(model, batch_size)}")
print(
    f"discriminator batch loss: {discriminator_loss_on_batch(model, batch_size)}"
)

