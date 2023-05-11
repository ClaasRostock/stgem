"""
Here you can find SUTs relevant to the SBST CPS competition where the
BeamNG.tech car simulator is being tested for faults.

The parameters dictionary for the SUT has the following parameters:

  beamng_home (str):       Path to the simulators home directory (i.e., where
                           the simulator zip was unpacked; has Bin64 etc. as
                           subdirectories).
  curvature_points (int):  How many curvature values are taken as input. This
                           determines the SUT idim.
  curvature_range (float): Scales values in [-1, 1] to the curvature range
                           [-K, K] where K = curvature_range.
  step_length (float):     (Integration) distance between two plane points.
  map_size (int):          Map size in pixels (total map map_size*map_size).
  max_speed (float):       Maximum speed (km/h) for the vehicle during the
                           simulation.
"""

import os, time, traceback
import logging

import numpy as np

# Disable BeamNG logs etc.
for id in ["shapely.geos", "beamngpy.BeamNGpy", "beamngpy.beamng", "beamngpy.Scenario", "beamngpy.Vehicle", "beamngpy.Camera", "matplotlib", "matplotlib.pyplot", "matplotlib.font_manager", "PIL.PngImagePlugin"]:
    logger = logging.getLogger(id)
    logger.setLevel(logging.CRITICAL)
    logger.disabled = True

from shapely.geometry import Point

from stgem.sut import SUT, SUTOutput
from util import test_to_road_points, frechet_distance, sbst_validate_test

if __name__ == "__main__":
    from self_driving.beamng_brewer import BeamNGBrewer
    from self_driving.beamng_car_cameras import BeamNGCarCameras
    from self_driving.beamng_tig_maps import maps, LevelsFolder
    from self_driving.beamng_waypoint import BeamNGWaypoint
    from self_driving.nvidia_prediction import NvidiaPrediction
    from self_driving.simulation_data_collector import SimulationDataCollector
    from self_driving.utils import get_node_coords, points_distance
    from self_driving.vehicle_state_reader import VehicleStateReader

    from code_pipeline.tests_generation import RoadTestFactory
    from code_pipeline.validation import TestValidator

class SBSTSUT(SUT):
    """A class for the SBST SUT which uses an input representation based on a
    fixed number of curvature points. All inputs are transformed to roads
    which begin at the middle of the bottom part of the map and point initially
    directly upwards."""

    default_parameters = {"curvature_range": 0.07,
                          "step_length": 15,
                          "map_size": 200,
                          "max_speed": 70}

    def __init__(self, parameters=None):
        """"""

        """
        Due to some strange choices in the competition code observe the
        following about paths:
          - You should set beamng_home to point to the directory where the
            simulator was unpacked.
          - The level files (directory levels) are hardcoded to be at
            os.path.join(os.environ["USERPROFILE"], "Documents/BeamNG.research/levels")
          - While the beamng_user parameter of BeamNGBrewer can be anything, it
            makes sense to set it to be the parent directory of the above as it
            is used anyway.
          - The levels_template folder (from the competition GitHub) should be
            in the directory where the code is run from, i.e., it is set to be
            os.path.join(os.getcwd(), "levels_template")
        """

        super().__init__(parameters)

        if "curvature_points" not in self.parameters:
            raise Exception("Number of curvature points not defined.")
        if self.curvature_points <= 0:
            raise ValueError("The number of curvature points must be positive.")
        if self.curvature_range <= 0:
            raise ValueError("The curvature range must be positive.")

        self.input_type = "vector"
        self.idim = self.curvature_points
        range = [-self.curvature_range, self.curvature_range]
        self.input_range = [range]*self.idim

        self.output_type = "signal"
        self.odim = 4
        self.outputs = ["bolp", "distance_left", "distance_right", "steering_angle"]
        # The road width is fixed to 8 in _interpolate of code_pipeline/tests_generation.py
        # TODO: What is the correct range for steering angle?
        self.output_range = [[0, 1], [-4, 4], [-4, 4], [-180, 180]]

        if self.map_size <= 0:
            raise ValueError("The map size must be positive.")
        if self.max_speed <= 0:
            raise ValueError("The maximum speed should be positive.")

        # This variable is essentially where (some) files created during the
        # simulation are placed and it is freely selectable. Due to some
        # choices in the SBST CPS competition code, we hard code it as follows
        # (see the explanation above).
        self.beamng_user = os.path.join(os.environ["USERPROFILE"], "Documents", "BeamNG.research")
        self.oob_tolerance = 0.95  # This is used by the SBST code, but the value does not matter.
        self.max_speed_in_ms = self.max_speed * 0.277778

        # Check for activation key.
        if not os.path.exists(os.path.join(self.beamng_user, "tech.key")):
            raise Exception(
                f"The activation key 'tech.key' must be in the directory {self.beamng_user}."
            )

        # Check for DAVE-2 model if requested.
        if "dave2_model" in self.parameters and self.dave2_model is not None:
            if not os.path.exists(self.dave2_model):
                raise Exception(f"The DAVE-2 model file '{self.dave2_model}' does not exist.")
            from tensorflow.python.keras.models import load_model
            self.load_model = load_model
            self.dave2 = True
        else:
            self.dave2 = False

        # For validating the executed roads.
        self.validator = TestValidator(map_size=self.map_size)

        # Disable log messages from third party code.
        logging.StreamHandler(stream=None)

        # The code below is from the SBST CPS competition.
        # Available at https://github.com/se2p/tool-competition-av
        # TODO This is specific to the TestSubject, we should encapsulate this better
        self.risk_value = 0.7
        # Runtime Monitor about relative movement of the car
        self.last_observation = None
        # Not sure how to set this... How far can a car move in 250 ms at 5Km/h
        self.min_delta_position = 1.0

        # These are set in test execution.
        self.brewer = None
        self.vehicle = None

    def _is_the_car_moving(self, last_state):
        """
        Check if the car moved in the past 10 seconds
        """

        # Has the position changed
        if self.last_observation is None:
            self.last_observation = last_state
            return True

        if (
            Point(
                self.last_observation.pos[0], self.last_observation.pos[1]
            ).distance(Point(last_state.pos[0], last_state.pos[1]))
            <= self.min_delta_position
        ):
            # How much time has passed since the last observation?
            return last_state.timer - self.last_observation.timer <= 10.0
        self.last_observation = last_state
        return True

    def end_iteration(self):
        try:
            if self.brewer:
                self.brewer.beamng.stop_scenario()
        except Exception as ex:
            traceback.print_exception(type(ex), ex, ex.__traceback__)

    def _execute_test_beamng(self, test):
        """Execute a single test on BeamNG.tech and return its input and output
        signals. The input signals is are the interpolated road points as
        series of X and Y coordinates. The output signal is the BOLP (body out
        of lane percentage) and signed distances to the edges of the lane at
        the given time steps. We expect the input to be a sequence of
        plane points."""

        # This code is mainly from https://github.com/se2p/tool-competition-av/code_pipeline/beamng_executor.py

        if self.brewer is None:
            self.brewer = BeamNGBrewer(beamng_home=self.beamng_home, beamng_user=self.beamng_user)
            self.vehicle = self.brewer.setup_vehicle()

        the_test = RoadTestFactory.create_road_test(test)

        # Check if the test is really valid.
        valid, msg = self.validator.validate_test(the_test)
        if not valid:
            # print("Invalid test, not run on SUT.")
            return SUTOutput(None, None, None, "invalid")

        # For the execution we need the interpolated points
        nodes = the_test.interpolated_points

        brewer = self.brewer
        brewer.setup_road_nodes(nodes)
        beamng = brewer.beamng
        waypoint_goal = BeamNGWaypoint("waypoint_goal", get_node_coords(nodes[-1]))

        # Notice that maps and LevelsFolder are global variables from
        # self_driving.beamng_tig_maps.
        beamng_levels = LevelsFolder(os.path.join(self.beamng_user, "0.24", "levels"))
        maps.beamng_levels = beamng_levels
        maps.beamng_map = maps.beamng_levels.get_map("tig")
        # maps.print_paths()

        maps.install_map_if_needed()
        maps.beamng_map.generated().write_items(brewer.decal_road.to_json() + "\n" + waypoint_goal.to_json())

        additional_sensors = BeamNGCarCameras().cameras_array if self.dave2 else None
        vehicle_state_reader = VehicleStateReader(self.vehicle, beamng, additional_sensors=additional_sensors)
        brewer.vehicle_start_pose = brewer.road_points.vehicle_start_pose()

        steps = brewer.params.beamng_steps
        simulation_id = time.strftime("%Y-%m-%d--%H-%M-%S", time.localtime())
        name = "beamng_executor/sim_$(id)".replace("$(id)", simulation_id)
        sim_data_collector = SimulationDataCollector(
            self.vehicle,
            beamng,
            brewer.decal_road,
            brewer.params,
            vehicle_state_reader=vehicle_state_reader,
            simulation_name=name,
        )

        # TODO: Hacky - Not sure what's the best way to set this...
        sim_data_collector.oob_monitor.tolerance = self.oob_tolerance

        sim_data_collector.get_simulation_data().start()
        try:
            # start = timeit.default_timer()
            brewer.bring_up()
            if self.dave2:
                if not hasattr(self, "model"):
                    self.model = self.load_model(self.dave2_model)
                predict = NvidiaPrediction(self.model, self.max_speed)
            # iterations_count = int(self.test_time_budget/250)
            # idx = 0

            if not self.dave2:
                brewer.vehicle.ai_set_aggression(self.risk_value)
                # Sets the target speed for the AI in m/s, limit means this is the maximum value (not the reference one)
                brewer.vehicle.ai_set_speed(self.max_speed_in_ms, mode="limit")
                brewer.vehicle.ai_drive_in_lane(True)
                brewer.vehicle.ai_set_waypoint(waypoint_goal.name)

            while True:
                # idx += 1
                # assert idx < iterations_count, "Timeout Simulation " + str(sim_data_collector.name)

                sim_data_collector.collect_current_data(oob_bb=True)
                last_state = sim_data_collector.states[-1]
                # Target point reached
                if (points_distance(last_state.pos, waypoint_goal.position) < 8.0):
                    break

                assert self._is_the_car_moving(
                    last_state
                ), f"Car is not moving fast enough {str(sim_data_collector.name)}"

                assert (
                    not last_state.is_oob
                ), f"Car drove out of the lane {str(sim_data_collector.name)}"

                if self.dave2:
                    img = vehicle_state_reader.sensors['cam_center']['colour'].convert('RGB')
                    # TODO
                    steering_angle, throttle = predict.predict(img, last_state)
                    self.vehicle.control(throttle=throttle, steering=steering_angle, brake=0)

                beamng.step(steps)

            sim_data_collector.get_simulation_data().end(success=True)
        except AssertionError as aex:
            sim_data_collector.save()
            # An assertion that trigger is still a successful test execution, otherwise it will count as ERROR
            sim_data_collector.get_simulation_data().end(
                success=True, exception=aex
            )
            # traceback.print_exception(type(aex), aex, aex.__traceback__)
        except Exception as ex:
            sim_data_collector.save()
            sim_data_collector.get_simulation_data().end(
                success=False, exception=ex
            )
            traceback.print_exception(type(ex), ex, ex.__traceback__)
        finally:
            sim_data_collector.save()
            try:
                sim_data_collector.take_car_picture_if_needed()
            except:
                pass

            self.end_iteration()

        # Build a time series for the distances, OOB percentages, and steering
        # angles based on simulation states.
        states = sim_data_collector.get_simulation_data().states
        timestamps = np.zeros(len(states))
        signals = np.zeros(shape=(4, len(states)))
        for i, state in enumerate(states):
            timestamps[i] = state.timer
            signals[0, i] = state.oob_percentage
            signals[1, i] = state.oob_distance_left
            signals[2, i] = state.oob_distance_right
            signals[3, i] = state.steering

        # Prepare the final input form as well.
        input_signals = np.zeros(shape=(2, len(nodes)))
        for i, point in enumerate(nodes):
            input_signals[0, i] = point[0]
            input_signals[1, i] = point[1]

        return input_signals, SUTOutput(signals, timestamps, {"simulation_time": timestamps[-1]}, None)

    def _execute_test(self, test):
        denormalized = self.descale(test.inputs.reshape(1, -1), self.input_range).reshape(-1)
        input_signals, output = self._execute_test_beamng(test_to_road_points(denormalized, self.step_length, self.map_size))
        test.input_denormalized = input_signals
        test.input_timestamps = np.arange(input_signals.shape[1])

        return output

    def validity(self, test):
        denormalized = self.descale(test.reshape(1, -1), self.input_range).reshape(-1)
        return sbst_validate_test(test_to_road_points(denormalized, self.step_length, self.map_size), self.map_size)

class SBSTSUT_validator(SUT):
    """Class for the SUT of considering an SBST test valid or not which uses input
    representation based on a fixed number of curvature points."""

    default_parameters = {"curvature_range": 0.07,
                          "step_length": 15,
                          "map_size": 200}

    def __init__(self, parameters):
        super().__init__(parameters)

        if "curvature_points" not in self.parameters:
            raise Exception("Number of curvature points not defined.")
        if self.curvature_points <= 0:
            raise ValueError("The number of curvature points must be positive.")
        if self.curvature_range <= 0:
            raise ValueError("The curvature range must be positive.")

        self.input_type = "vector"
        self.idim = self.curvature_points
        range = [-self.curvature_range, self.curvature_range]
        self.input_range = [range]*self.idim

        self.output_type = "vector"
        self.odim = 1
        self.outputs = ["valid"]
        self.output_range = [[0, 1]]

        if self.map_size <= 0:
            raise ValueError("The map size must be positive.")

    def _execute_test(self, test):
        denormalized = self.descale(test.inputs.reshape(1, -1), self.input_range).reshape(-1)
        valid = sbst_validate_test(test_to_road_points(denormalized, self.step_length, self.map_size), self.map_size)
        test.input_denormalized = denormalized
        return SUTOutput(np.array([valid]), None, None, None)
