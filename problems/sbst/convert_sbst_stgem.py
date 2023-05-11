#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json, os, sys

import numpy as np
import pandas as pd

from stgem.generator import STGEMResult, StepResult
from stgem.sut import SUTInput, SUTOutput
from stgem.test_repository import TestRepository

from sbst import MaxOOB

base_path = sys.argv[1]
if not os.path.exists(base_path):
    raise SystemExit(f"Directory {base_path} not found.")

output_path = sys.argv[2]
if not os.path.exists(output_path):
    raise SystemExit(f"Directory {output_path} not found.")

identifier = sys.argv[3]

objective = MaxOOB()

# Find the generators* directories related to each replica.
replica_dirs = []
for replica_dir in os.listdir(base_path):
    for dir_name in os.listdir(os.path.join(base_path, replica_dir)):
        if dir_name.startswith("generators"):
            replica_dirs.append(os.path.join(base_path, replica_dir, dir_name))
            break

results = []
for i, dir_name in enumerate(replica_dirs):
    test_repository = TestRepository()
    step_parameters = {}

    csv_file = os.path.join(dir_name, "generation_stats.csv")
    if not os.path.exists(csv_file):
        continue
    data = pd.read_csv(csv_file)
    tests = int(data["test_generated"][0])
    generation_time = float(data["real_time_generation"][0]) / tests
    real_execution_time = float(data["real_time_execution"][0]) / tests

    success = False
    for file_name in os.listdir(dir_name):
        if not file_name.endswith(".json"): continue
        data = json.load(open(os.path.join(dir_name, file_name)))

        # Input
        # ---------------------------------------------------------------------
        nodes = data["interpolated_points"]
        input_signals = np.zeros(shape=(2, len(nodes)))
        for i, point in enumerate(nodes):
            input_signals[0,i] = point[0]
            input_signals[1,i] = point[1]

        sut_input = SUTInput(None, input_signals, None)

        # Output
        # ---------------------------------------------------------------------
        # Fields in order: timer, pos, dir, vel, steering, steering_input, brake, brake_input, throttle, throttle_input, wheelspeed, vel_kmh, is_oob, oob_counter, max_oob_percentage, oob_distance, oob_percentage
        # The final test whose execution is partially saved and needs to be omitted.
        if "execution_data" not in data: continue
        timestamps = np.zeros(len(data["execution_data"]))
        signals = np.zeros(shape=(4, len(data["execution_data"])))
        for i, state in enumerate(data["execution_data"]):
            timestamps[i] = state[0]
            signals[0,i] = state[-1]
            signals[1,i] = -1
            signals[2,i] = -1
            signals[3,i] = state[5]

        sut_output = SUTOutput(signals, timestamps, {"simulated_time": timestamps[-1]}, None)

        # Objective
        # ---------------------------------------------------------------------
        objectives = [objective(sut_input, sut_output)]

        # Performance
        # ---------------------------------------------------------------------
        performance = test_repository.new_record()
        performance.record("training_time", 0)
        performance.record("generation_time", generation_time)
        performance.record("execution_time", real_execution_time)

        test_repository.record_input(sut_input)
        test_repository.record_output(sut_output)
        test_repository.record_objectives(objectives)
        test_repository.finalize_record()

    step_result = StepResult(
        test_repository,
        success,
        {}
    )

    result = STGEMResult(
        description=f"SBST converted results replica {i + 1}",
        sut_name="BeamNG",
        sut_parameters={},
        seed=None,
        step_results=[step_result],
        test_repository=test_repository,
    )
    results.append(result)

for i, result in enumerate(results):
    file_name = os.path.join(output_path, "{}_{:>2}.pickle.gz".format(identifier, i))
    result.dump_to_file(file_name)

