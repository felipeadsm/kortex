#! /usr/bin/env python3

###
# KINOVA (R) KORTEX (TM)
#
# Copyright (c) 2021 Kinova inc. All rights reserved.
#
# This software may be modified and distributed
# under the terms of the BSD 3-Clause license.
#
# Refer to the LICENSE file for details.
#
###

import threading

from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient

from api_python.examples import utilities

from kortex_api.autogen.messages import Base_pb2

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 100


# Create closure to set an event after an END or an ABORT
def check_for_end_or_abort(error):
    """Return a closure checking for END or ABORT notifications

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
    """

    def check(notification, e=error):
        print("EVENT : " + Base_pb2.ActionEvent.Name(notification.action_event))
        if notification.action_event == Base_pb2.ACTION_END or notification.action_event == Base_pb2.ACTION_ABORT:
            e.set()

    return check


def example_move_to_home_position(base):
    # Make sure the arm is in Single Level Servoing mode
    base_servo_mode = Base_pb2.ServoingModeInformation()
    base_servo_mode.servoing_mode = Base_pb2.SINGLE_LEVEL_SERVOING
    base.SetServoingMode(base_servo_mode)

    # Move arm to ready position
    print("Moving the arm to a safe position")
    action_type = Base_pb2.RequestedActionType()
    action_type.action_type = Base_pb2.REACH_JOINT_ANGLES
    action_list = base.ReadAllActions(action_type)
    action_handle = None
    for action in action_list.action_list:
        if action.name == "Home":
            action_handle = action.handle

    if action_handle is None:
        print("Can't reach safe position. Exiting")
        return False

    e = threading.Event()
    notification_handle = base.OnNotificationActionTopic(
        check_for_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    base.ExecuteActionFromReference(action_handle)
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if finished:
        print("Safe position reached")
    else:
        print("Timeout on action notification wait")
    return finished


def populateAngularPose(jointPose, durationFactor):
    waypoint = Base_pb2.AngularWaypoint()
    waypoint.angles.extend(jointPose)
    waypoint.duration = durationFactor * 5.0

    return waypoint


def go_to_trajectory(base, joints_list):
    base_servo_mode = Base_pb2.ServoingModeInformation()
    base_servo_mode.servoing_mode = Base_pb2.SINGLE_LEVEL_SERVOING
    base.SetServoingMode(base_servo_mode)

    joint_poses = joints_list

    waypoints = Base_pb2.WaypointList()
    waypoints.duration = 0.0
    waypoints.use_optimal_blending = False

    index = 0
    for joint_pose in joint_poses:
        waypoint = waypoints.waypoints.add()
        waypoint.name = "waypoint_" + str(index)
        durationFactor = 1
        # Joints/motors 5 and 7 are slower and need more time
        if index == 4 or index == 6:
            durationFactor = 6  # Min 30 seconds

        waypoint.angular_waypoint.CopyFrom(populateAngularPose(joint_pose, durationFactor))
        index = index + 1

        # Verify validity of waypoints
    result = base.ValidateWaypointList(waypoints);
    if len(result.trajectory_error_report.trajectory_error_elements) == 0:

        e = threading.Event()
        notification_handle = base.OnNotificationActionTopic(
            check_for_end_or_abort(e),
            Base_pb2.NotificationOptions()
        )

        print("Reaching angular pose trajectory...")

        base.ExecuteWaypointTrajectory(waypoints)

        print("Waiting for trajectory to finish ...")
        finished = e.wait(TIMEOUT_DURATION)
        base.Unsubscribe(notification_handle)

        if finished:
            print("Angular movement completed")
        else:
            print("Timeout on action notification wait")
        return finished
    else:
        print("Error found in trajectory")
        print(result.trajectory_error_report)
        return finished


def main():
    # Parse arguments
    args = utilities.parseConnectionArguments()

    # Create connection to the device and get the router
    with utilities.DeviceConnection.createTcpConnection(args) as router:
        # Create required services
        base = BaseClient(router)

        # Example core
        success = True

        success &= example_move_to_home_position(base)
        success &= go_to_trajectory(base)

        return 0 if success else 1


if __name__ == "__main__":
    exit(main())
