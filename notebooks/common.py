import os, sys
import numpy as np

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib import animation
from IPython.display import HTML

sys.path.append(os.path.join(".."))
from stgem.generator import STGEM, STGEMResult
from stgem.budget import Budget

# Color maps
color_map_falsified = cm.get_cmap("Reds", 8)
color_map_other = cm.get_cmap("Blues_r", 8)

def collect_replica_files(path, prefix):
    """Collects all files under the given path (including subdirectories) that
    begin with the given prefix."""

    if not os.path.exists(path):
        raise Exception(f"No path '{path}'.")

    results = []
    for dir, subdirs, files in os.walk(path):
        results.extend(
            os.path.join(dir, file)
            for file in files
            if file.startswith(prefix)
        )
    return results

def load_results(files, load_sut_output=True):
    results = [STGEMResult.restore_from_file(file) for file in files]
    # This reduces memory usage if these values are not needed.
    if not load_sut_output:
        for result in results:
            result.test_repository._outputs = None

    return results

def loadExperiments(path, benchmarks, prefixes):
    experiments = {}
    for benchmark in benchmarks:
        experiments[benchmark] = {}
        for prefix in prefixes[benchmark]:
            files = collect_replica_files(os.path.join(path, benchmark), prefix)
            if len(files) == 0:
                raise Exception(
                    f"Empty experiment for prefix '{prefix}' for benchmark '{benchmark}'."
                )
            experiments[benchmark][prefix] = load_results(files)

    return experiments

def falsification_rate(experiment):
    if len(experiment) == 0:
        return None

    c = sum(
        1 if any(step.success for step in result.step_results) else 0
        for result in experiment
    )
    return c/len(experiment)

def times(replica):
    t = 0
    for i in range(replica.test_repository.tests):
        performance = replica.test_repository.performance(i)
        try:
            t += performance.obtain("execution_time")
        except:
            pass
        try:
            t += performance.obtain("generation_time")
        except:
            pass
        try:
            t += performance.obtain("training_time")
        except:
            pass

    return t

def min_along(X, length=None):
    # Return the minimum so far along X.
    m = 1.0
    A = []
    for i in range(len(X) if length is None else length):
        o = X[i] if i < len(X) else 1.0
        if o < m:
            m = o
        A.append(m)
    return A

def mean_min_along(results, length=None):
    A = []
    for i in range(len(results)):
        _, _, Y = results[i].test_repository.get()
        Y = np.array(Y).reshape(-1)
        B = min_along(Y, length=length)
        A.append(B)

    A = np.array(A)
    return np.mean(A, axis=0)

def first_falsification(replica):
    _, _, Y = replica.test_repository.get()
    return next((i for i in range(len(Y)) if min(Y[i]) <= 0.0), None)

def set_boxplot_color(bp, color):
    plt.setp(bp["boxes"], color=color)
    plt.setp(bp["whiskers"], color=color)
    plt.setp(bp["caps"], color=color)
    plt.setp(bp["medians"], color=color)

def color(x, color_map, robustness_interval=None):
    """Color for robustness value x (clipped to [0, 1]). A range for robustness
    values can be specified to display a better range of colors if the possible
    robustness range is narrow. By default this is
    """

    if robustness_interval is None:
        robustness_interval = [-1, 1]

    def scale(x, interval_original, interval_target):
        A = interval_original[0]
        B = interval_original[1]
        C = interval_target[0]
        D = interval_target[1]
        E = (-1 * A + x) / (-1 * A + B) # input percent of original interval
        return C + E * (-1 * C + D) # input scaled to target interval

    x = scale(x, robustness_interval, (-1, 1))
    return color_map(x)

def own_boxplot(data, x_labels, title="", ylabel="", line=None):
    fig = plt.figure(figsize=(2*len(data), 5))
    plt.title(title)
    plt.ylabel(ylabel)
    bp = bp = plt.boxplot(data, labels=x_labels)
    set_boxplot_color(bp, "black")

    if line is not None:
        plt.axhline(line, c="r")

    plt.tight_layout()
    return plt

def plotTest(replica, idx):
    """Plots a single test from a replica."""

    if replica.sut_parameters["input_type"] == "vector":
        input_type = "vector"
    elif replica.sut_parameters["input_type"] in [
        "signal",
        "piecewise constant signal",
    ]:
        input_type = "signal"
    else:
        raise Exception(
            f"""Unknown input type '{replica.sut_parameters["input_type"]}'."""
        )
    output_type = replica.sut_parameters["output_type"]

    inputs = replica.sut_parameters["inputs"]
    outputs = replica.sut_parameters["outputs"]
    input_range = replica.sut_parameters["input_range"]
    output_range = replica.sut_parameters["output_range"]
    simulation_time = replica.sut_parameters["simulation_time"]

    X, Z, Y = replica.test_repository.get()
    Y = np.array(Y).reshape(-1)

    # Define the signal color based in the test index.
    color_map = cm.get_cmap("Reds", 8) # Use color() to add color to lines if desired

    if input_type == "signal":
        if output_type == "signal":
            fig, ax = plt.subplots(2, max(len(inputs), len(outputs)), figsize=(10*max(len(inputs), len(outputs)), 10))

            # Input.
            for i, var in enumerate(inputs):
                ax[0,i].set_title(var)
                ax[0,i].set_xlim((0, simulation_time))
                ax[0,i].set_ylim(input_range[i])
                x = X[idx].input_timestamps
                y = X[idx].input_denormalized[i]
                ax[0,i].plot(x, y)

            # Output.
            for i, var in enumerate(outputs):
                ax[1,i].set_title(var)
                ax[1,i].set_xlim((0, simulation_time))
                ax[1,i].set_ylim(output_range[i])
                x = Z[idx].output_timestamps
                y = Z[idx].outputs[i]
                ax[1,i].plot(x, y)
        else:
            fig, ax = plt.subplots(1, len(inputs), figsize=(10*len(inputs), 10))

            # Input.
            for i, var in enumerate(inputs):
                o = ax[i] if len(inputs) > 1 else ax
                o.set_title(var)
                o.set_xlim((0, simulation_time))
                o.set_ylim(input_range[i])
                x = X[idx].input_timestamps
                y = X[idx].input_denormalized[i]
                o.plot(x, y)

            # Output.
            print(", ".join(outputs))
            print(Y[idx].outputs)
    elif output_type == "signal":
        fig, ax = plt.subplots(1, len(outputs), figsize=(10*len(outputs), 10))

        # Input.
        print(", ".join(inputs))
        print(X[idx].input_denormalized)

        # Output.
        for i, var in enumerate(outputs):
            o = ax[i] if len(outputs) > 1 else ax
            o.set_title(var)
            o.set_xlim((0, simulation_time))
            o.set_ylim(output_range[i])
            x = Z[idx].output_timestamps
            y = Z[idx].outputs[i]
            o.plot(x, y)
    else:
        # Input.
        print(", ".join(inputs))
        print(X[idx].input_denormalized)
        print()

        # Output.
        print(", ".join(outputs))
        print(Y[idx].outputs)

def animateResult(replica):
    inputs = replica.sut_parameters["inputs"]
    outputs = replica.sut_parameters["outputs"]
    input_range = replica.sut_parameters["input_range"]
    output_range = replica.sut_parameters["output_range"]
    simulation_time = replica.sut_parameters["simulation_time"]

    robustness_threshold = 0.05

    X, Z, Y = replica.test_repository.get()
    Y = np.array(Y).reshape(-1)

    # Setup the figures.
    fig, ax = plt.subplots(2, max(len(inputs), len(outputs)), figsize=(5*max(len(inputs), len(outputs)), 5))

    for i, var in enumerate(inputs):
        ax[0,i].set_title(var)
        ax[0,i].set_xlim((0, simulation_time))
        ax[0,i].set_ylim(input_range[i])
    for i, var in enumerate(outputs):
        ax[1,i].set_title(var)
        ax[1,i].set_xlim((0, simulation_time))
        ax[1,i].set_ylim(output_range[i])

    lines = []
    for i in range(len(inputs)):
        lines.append(ax[0,i].plot([], [], lw=2)[0])
    for i in range(len(outputs)):
        lines.append(ax[1,i].plot([], [], lw=2)[0])
    text = ax[0,0].text(0.02, 0.95, "")
    #text = ax[0,0].text(0.02, 0.95, "", transform=ax.transAxes)

    def init():
        for line in lines:
            line.set_data([], [])

        return lines

    def animate(i):
        cm = color_map_falsified if Y[i] <= robustness_threshold else color_map_other
        c = color(Y[i], cm)
        c = "black"
        text.set_text("test {}, robustness {}".format(i+1, Y[i]))
        for j in range(len(inputs)):
            k = j
            x = X[i].input_timestamps
            y = X[i].input_denormalized[j]
            lines[k].set_color(c)
            lines[k].set_data(x, y)
        for j in range(len(outputs)):
            k = len(inputs) + j
            x = Z[i].output_timestamps
            y = Z[i].outputs[j]
            lines[k].set_color(c)
            lines[k].set_data(x, y)

        return lines

    plt.close()
    anim = animation.FuncAnimation(fig, animate, init_func=init, frames=len(Y), interval=200, blit=True)
    return anim

def condensed_boxplot(data, x_labels, pb_labels, colors):
    # TODO: Does this even work with the current code?
    fig = plt.figure(figsize =(7, 5))
    
    # Create boxplots and set colors.
    for i in range(len(data)):
        #bp = plt.boxplot(data[i])
        bp = plt.boxplot(data[i], positions=i+np.array(range(len(data[i])))*4-0.4, sym="", widths=0.6)
        set_boxplot_color(bp, colors[i])
    
    # Draw temporary lines and use them to create a legend.
    for i in range(len(pb_labels)):
        plt.plot([], c=colors[i], label=pb_labels[i])
    plt.legend()
    
    plt.xticks(range(0, len(x_labels)*4, 4), x_labels)
    plt.xlim(-2, len(x_labels)*4)
    #plt.ylim(0, 8)
    plt.tight_layout()

def visualize3DTestSuite(experiment, idx):
    """Visualizes a test suite for SUTs with vector output and input dimension
    <= 3."""

    angle = 25
    result = experiment[idx]

    if result.sut_parameters["input_type"] != "vector":
        raise Exception("Test suite visualization available only for vector input SUTs.")

    X, _, Y = result.test_repository.get()
    X = np.asarray([x.inputs for x in X]) # Inputs
    Y = np.asarray(Y).reshape(-1) # Robustness

    sut_inputs = result.sut_parameters["inputs"]

    fig = plt.figure(figsize=(10, 10))

    # Adding support for 2d and 1d
    if (len(sut_inputs) == 1):
        ax = fig.add_subplot()#TODO: find acceptable one dimensional plot
        ax.set_xlabel(sut_inputs[0])
        ax.set_xlim(-1, 1)
    elif (len(sut_inputs) == 2):
        ax = fig.add_subplot()
        ax.set_xlabel(sut_inputs[0])
        ax.set_xlim(-1, 1)
        ax.set_ylabel(sut_inputs[1])
        ax.set_ylim(-1, 1)
    elif (len(sut_inputs) == 3):
        ax = fig.add_subplot(projection="3d") # 111
        ax.set_xlabel(sut_inputs[0])
        ax.set_xlim(-1, 1)
        ax.set_ylabel(sut_inputs[1])
        ax.set_ylim(-1, 1)
        ax.set_zlabel(sut_inputs[2])
        ax.set_zlim(-1, 1)
    else:
        raise ValueError("Too many dimensions ({}) to visualize.".format(len(sut_inputs)))

    ax.azim = angle # rotate around the z axis

    falsify_pct = 0.05 # Robustness percent needed for classifying as a falsified test

    # Divide the tests indices into two classes: those that correspond to tests
    # with robustness below the given threshold and the rest. Find also the range
    # of the robustness values in both classes.
    interval_false = [1, -1] # Min & Max robustness values
    interval_persist = [1, -1]
    c = []

    for i in range(len(X)):
        if (Y[i] <= falsify_pct):
            c.append(i)
            if (Y[i] < interval_false[0]):
                interval_false[0] = Y[i]
            if (Y[i] > interval_false[1]):
                interval_false[1] = Y[i]
        else:
            if (Y[i] < interval_persist[0]):
                interval_persist[0] = Y[i]
            if (Y[i] > interval_persist[1]):
                interval_persist[1] = Y[i]

    # Initiate arrays
    points_false = np.zeros(shape=(len(c), len(sut_inputs)))
    points_persist = np.zeros(shape=(len(X)-len(c), len(sut_inputs)))
    colors_false = np.zeros(shape=(len(c), 4)) # color values use 4 float values
    colors_persist = np.zeros(shape=(len(X)-len(c), 4))

    # split inputs into falsifying and persistent and calculate colors
    f, p = 0, 0
    for i in range(len(X)):
        if i in c:
            points_false[f] = X[i]
            colors_false[f] = color(Y[i], color_map_falsified, interval_false) # (-1, 0) = left side of colormap
            f += 1
        else:
            points_persist[p] = X[i]
            colors_persist[p] = color(Y[i], color_map_other, interval_persist) # (0, 1) = right side of colormap
            p += 1

    def label(interval, invert_lightness=False):
        if invert_lightness:
            format = (round(interval[1], 5), round(interval[0], 5))
        else:
            format = (round(interval[0], 5), round(interval[1], 5))
        return "Darkest: {}\nLightest: {}".format(format[0], format[1])

    # TODO: Implement multidimensional support
    if (len(sut_inputs) == 1):
        raise NotImplementedError()
    elif (len(sut_inputs) == 2):
        raise NotImplementedError()
    elif (len(sut_inputs) == 3):
        ax.scatter(points_false[:, 0], points_false[:, 1], points_false[:, 2], s=50, alpha=0.6, edgecolors="w", c=colors_false, label=label(interval_false))
        ax.scatter(points_persist[:, 0], points_persist[:, 1], points_persist[:, 2], s=50, alpha=0.06, edgecolors="w", c=colors_persist, label=label(interval_persist, invert_lightness=True)) # Uses inverted map => invert label
    else:
        raise ValueError("Too many dimensions ({}) to visualize. Max amount {}".format(len(sut_inputs), 3)) #ValueError correct error?

    ax.set_title("{} out of {} inputs led to falsifying results due to having a robustness value of {} or lower".format(len(points_false) ,len(X) ,falsify_pct))
    ax.legend(title="Robustness according to color", loc="upper right") # bbox_to_anchor=(1,1)

    plt.show()

