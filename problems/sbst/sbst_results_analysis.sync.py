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
import itertools, math, os, sys

sys.path.append(os.path.join("..", ".."))
sys.path.append(os.path.join("..", "..", "notebooks"))
from common import *
from util import test_to_road_points

# %% [markdown]
# # Domain-Specific Code

# %%
def descale(test, input_range):
    """Descale a test without loading the actual SBST SUT."""

    from stgem.sut import SUT
    sut = SUT()
    input_range = [input_range]*len(test)
    return sut.descale(test.reshape(1, -1), input_range).reshape(-1)

def road_visualization(result, start, end):
    """Function for visualizing roads in a replica. The numbers start and end
    indicate which roads (tests) to include. For best results, ensure that
    end - start is a multiple of 10."""
    
    columns = 10
    rows = int((end - start)/columns)

    # Input range for descaling tests.
    input_range = [-result.sut_parameters["curvature_range"], result.sut_parameters["curvature_range"]]

    fig, axes = plt.subplots(rows, columns, figsize=(64, 64), sharex = True, sharey = True)
    plt.xticks([])
    plt.yticks([])
    idx = 0
    failed_cnt = 0
    for row, column in itertools.product(range(rows), range(columns)):
        _input, _, _objective = result.test_repository.get(start + idx)
        robustness = round(_objective[0], 3)
        axes[row, column].title.set_text(f"[{(start+idx)}] - Robustness: {robustness}")

        # Highlight the roads that produced a failed test
        if robustness <= 0.05:
            color = "r"
            failed_cnt += 1
        else:
            color = "b"

        # Plot interpolated points connected by lines.
        x, y = _input.input_denormalized
        axes[row,column].plot(x, y, color=color)

        # Plot the control points.
        points = np.array(test_to_road_points(descale(_input.inputs, input_range), result.sut_parameters["step_length"], result.sut_parameters["map_size"]))
        axes[row,column].plot(points[:,0], points[:,1], f"{color}o")

        idx += 1

    fig.suptitle(f'Road visualization of {idx} test runs where {failed_cnt} failed - Seed: {result.seed}', fontsize=40)
    #plt.savefig(f'road_images/{filename}.png', pad_inches=0.1, dpi=150)
    #plt.close(fig)
    plt.show()

def move_road(P, x0, y0):
    """Moves the sequence of points P in such a way that the initial point is
    at (x0, y0) and the initial direction is up."""

    X = np.array(P)

    if len(X) == 1:
        Q = np.array([x0, y0])
    else:
        # Find the translation angle.
        angle = math.pi / 2 - math.atan2(X[1,1] - X[0,1], X[1,0] - X[0,0])
        # Translation vector to origin.
        o_x = -X[0,0]
        o_y = -X[0,1]

        Q = np.empty_like(X)
        for n in range(len(X)):
            # Map to origin for rotation.
            x = X[n,0] + o_x
            y = X[n,1] + o_y
            # Rotate the point and translate the resulting point back.
            Q[n,0] = math.cos(angle) * x - math.sin(angle) * y + x0
            Q[n,1] = math.sin(angle) * x + math.cos(angle) * y + y0

    return Q.tolist() if isinstance(P, list) else Q

def steering_sd(test_repository):
    """Compute the standard deviation of the steering angles for each test in
    the test suite. This is a behavioral diversity measure used in the SBST
    2022 report."""

    _, Z, _ = test_repository.get()

    return [np.std(sut_output.outputs[3]) for sut_output in Z]

def direction_coverage(test_repository, bins=36):
    """Compute the coverage of road directions of the test suite. That is, for
    each road, compute the angles between two consecutive road points and place
    the angles into bins (default 36 bins, i.e., bins cover 10 degrees) and
    return the proportion of bins covered. The angle is defined as the angle to
    the vertical axis. This is a structural diversity measure used in the SBST
    2022 report."""

    def road_coverage(sut_input, bins):
        points = sut_input.input_denormalized

        # Compute the angles.
        angles = []
        for i in range(0, points.shape[1] - 1, 2):
            vector = np.array([points[0,i+1] - points[0,i], points[1,i+1] - points[1,i]])
            angle = math.degrees(np.arccos( vector[1] / np.linalg.norm(vector) ))
            angles.append(angle)

        # Place into bins.
        bins = np.linspace(0.0, 360.0, num=bins + 1)
        covered_bins = set(np.digitize(angles, bins))

        return len(covered_bins) / len(bins)

    X, _, _ = test_repository.get()

    data = [road_coverage(sut_input, bins) for sut_input in X]

    return data

def euclidean_diversity(test_repository, adjusted_points, threshold):
    """Computes the median of the pairwise Euclidean distances of the
    failed tests of the given test suite after the roads of the test suite
    have been normalized to have a common number of points and turned into
    angles."""

    def adjust_road_signal(road_points, points):
        """Adjusts an interpolated road to have the specified number of points."""

        # Notice that the road points are given a signal of plane points of shape
        # (2, N).
        road_points = np.transpose(road_points).reshape(-1, 2)
        idx = np.round(np.linspace(0, len(road_points) - 1, points)).astype(int)
        adjusted = road_points[idx]
        return move_road(adjusted, 0, 0)

    X, _, Y = test_repository.get()
    Y = np.array(Y).reshape(-1)

    converted_failed_tests = []
    for n in range(len(Y)):
        if Y[n] >= threshold: continue
        # Adjust the road to have a common number of points.
        adjusted_road = adjust_road_signal(X[n].input_denormalized, adjusted_points)
        # Convert the adjusted road into a sequence of angles.
        diff = np.diff(adjusted_road, axis=0)
        angles = np.arctan2(diff[:,0], diff[:,1])
        converted_failed_tests.append(angles)

    # Compute pairwise Euclidean distances for the tests.
    euclidean_distances = [np.linalg.norm(t1 - t2) for t1, t2 in itertools.combinations(converted_failed_tests, 2)]
    # Compute the median Euclidean distance.
    median = np.median(euclidean_distances)

    return median

# %% [markdown]
# # Load Experiments

# %%
output_path_base = os.path.join("..", "..", "output")

# Replica prefixes for collecting the experiments.
replica_prefixes = {
    "SBST": ["SBST_OLD"]
}

experiments = loadExperiments(output_path_base, ["SBST"], replica_prefixes)
experiments = experiments["SBST"]

failure_threshold = 0.05

# %% [markdown]
# # Number of Failed Tests

# %%
def number_of_failed_tests(experiment, threshold):
    out = []
    for result in experiment:
        _, _, Y = result.test_repository.get()
        Y = np.array(Y).reshape(-1)
        N = sum(y <= threshold for y in Y)
        out.append(N)

    return out

# %%
data = []
for identifier in experiments:
    failed_tests = number_of_failed_tests(experiments[identifier], failure_threshold)
    data.append(failed_tests)
    print(failed_tests)

own_boxplot(data, list(experiments), title="Number of Failed Tests", ylabel="Number of Failed Tests")

# %% [markdown]
# # Test Suite Diversity

# %%
def test_suite_euclidean_diversity(experiment, threshold):
    # We have determined this number experimentally.
    adjusted_points = 75
    return [euclidean_diversity(result.test_repository, adjusted_points, threshold) for result in experiment]

# %%
# We have determined this number experimentally.
adjusted_points = 75

diversity_values = [[euclidean_diversity(result.test_repository, adjusted_points, failure_threshold) for result in experiments[identifier]] for identifier in experiments]

#print(diversity_values)
own_boxplot(diversity_values, list(experiments), title="Test Suite Diversity Euclidean", ylabel="Test Suite Diversity Euclidean")

# %%
diversity_values = [[steering_sd(result.test_repository) for result in experiments[identifier]] for identifier in experiments]

print(diversity_values)

# %%
diversity_values = [[direction_coverage(result.test_repository) for result in experiments[identifier]] for identifier in experiments]

print(diversity_values)

# %% [markdown]
# # Replica Road Visualization

#%%
experiment_identifier = "SBST_OLD"
replica = 0

start = 200
end = 300
#end = experiments[experiment_identifier][replica].test_repository.tests

road_visualization(experiments[experiment_identifier][replica], start, end)

