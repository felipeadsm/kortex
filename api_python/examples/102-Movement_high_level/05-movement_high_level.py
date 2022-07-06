#! /usr/bin/env python3

# Exemplo desenvolvido com o intuito de treinar as funcionalidades da api

import sys
import os
import time
import threading

from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from kortex_api.autogen.client_stubs.BaseCyclicClientRpc import BaseCyclicClient

from kortex_api.autogen.messages import Base_pb2, BaseCyclic_pb2, Common_pb2

from api_python.examples import utilities

# Maximum allowed waiting time during actions (in seconds)
TIMEOUT_DURATION = 20

# Actuator speed (deg/s)
SPEED = 20.0


# Create closure to set an event after an END or an ABORT
def check_for_end_or_abort(e):
    """Return a closure checking for END or ABORT notifications

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
    """

    def check(notification, e=e):
        print("EVENT : " + Base_pb2.ActionEvent.Name(notification.action_event))
        if notification.action_event == Base_pb2.ACTION_END or notification.action_event == Base_pb2.ACTION_ABORT:
            e.set()

    return check


def check_for_sequence_end_or_abort(e):
    """Return a closure checking for END or ABORT notifications on a sequence

    Arguments:
    e -- event to signal when the action is completed
        (will be set when an END or ABORT occurs)
    """

    def check(notification, e=e):
        event_id = notification.event_identifier
        task_id = notification.task_index
        if event_id == Base_pb2.SEQUENCE_TASK_COMPLETED:
            print("Sequence task {} completed".format(task_id))
        elif event_id == Base_pb2.SEQUENCE_ABORTED:
            print("Sequence aborted with error {}:{}".format(notification.abort_details,
                                                             Base_pb2.SubErrorCodes.Name(notification.abort_details)))
            e.set()
        elif event_id == Base_pb2.SEQUENCE_COMPLETED:
            print("Sequence completed.")
            e.set()

    return check


def create_angular_action(actuator_count, joint_values):
    print("Creating angular action")
    action = Base_pb2.Action()
    action.name = "Example angular action"
    action.application_data = ""

    for joint_id in range(actuator_count):
        joint_angle = action.reach_joint_angles.joint_angles.joint_angles.add()
        joint_angle.value = joint_values[joint_id]

    return action


def move_to_position(base, position):
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
        if action.name == "Home" and position == "Home":
            action_handle = action.handle
        if action.name == "Retract" and position == "Retract":
            action_handle = action.handle
        if action.name == "Zero" and position == "Zero":
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


def create_sequence(base, actions, sequence_name):
    print("Creating Action for Sequence")

    actuator_count = base.GetActuatorCount().count

    print("Creating Sequence")
    sequence = Base_pb2.Sequence()
    sequence.name = sequence_name

    list_aux = []
    for action in actions:
        angular_action = create_angular_action(actuator_count, action)
        list_aux.append(angular_action)

    print("Appending Actions to Sequence")
    task_1 = sequence.tasks.add()
    task_1.group_identifier = 1
    task_1.action.CopyFrom(list_aux[0])

    task_2 = sequence.tasks.add()
    task_2.group_identifier = 1  # Sequence elements with same group_id are played at the same time
    task_2.action.CopyFrom(list_aux[1])

    task_3 = sequence.tasks.add()
    task_3.group_identifier = 1  # Sequence elements with same group_id are played at the same time
    task_3.action.CopyFrom(list_aux[2])

    task_4 = sequence.tasks.add()
    task_4.group_identifier = 1  # Sequence elements with same group_id are played at the same time
    task_4.action.CopyFrom(list_aux[3])


    e = threading.Event()
    notification_handle = base.OnNotificationSequenceInfoTopic(
        check_for_sequence_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    # print("Creating sequence on device and executing it")
    # handle_sequence = base.CreateSequence(sequence)

    print("Moving the arm to a safe position")
    sequence_list = base.ReadAllSequences()
    sequence_handle = None
    for sequence in sequence_list.sequence_list:
        if sequence.name == "vamola":
            sequence_handle = sequence.handle

    if sequence_handle is None:
        print("Can't reach safe position. Exiting")
        return False

    base.PlaySequence(sequence_handle)

    print("Waiting for movement to finish ...")
    finished = e.wait(TIMEOUT_DURATION)
    base.Unsubscribe(notification_handle)

    if not finished:
        print("Timeout on action notification wait")
    return finished


def example_send_joint_speeds(base):
    joint_speeds = Base_pb2.JointSpeeds()

    actuator_count = base.GetActuatorCount().count
    # The 7DOF robot will spin in the same direction for 10 seconds
    if actuator_count == 7:
        speeds = [SPEED, 0, -SPEED, 0, SPEED, 0, -SPEED]
        i = 0
        for speed in speeds:
            joint_speed = joint_speeds.joint_speeds.add()
            joint_speed.joint_identifier = i
            joint_speed.value = speed
            joint_speed.duration = 0
            i = i + 1
        print("Sending the joint speeds for 10 seconds...")
        base.SendJointSpeedsCommand(joint_speeds)
        time.sleep(10)
    # The 6 DOF robot will alternate between 4 spins, each for 2.5 seconds
    if actuator_count == 6:
        print("Sending the joint speeds for 10 seconds...")
        for times in range(4):
            del joint_speeds.joint_speeds[:]
            if times % 2:
                speeds = [-SPEED, 0.0, 0.0, SPEED, 0.0, 0.0]
            else:
                speeds = [SPEED, 0.0, 0.0, -SPEED, 0.0, 0.0]
            i = 0
            for speed in speeds:
                joint_speed = joint_speeds.joint_speeds.add()
                joint_speed.joint_identifier = i
                joint_speed.value = speed
                joint_speed.duration = 0
                i = i + 1

            base.SendJointSpeedsCommand(joint_speeds)
            time.sleep(2.5)

    print("Stopping the robot")
    base.Stop()

    return True


def main():
    # Import the utilities helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # Parse arguments
    args = utilities.parseConnectionArguments()

    # Create connection to the device and get the router
    with utilities.DeviceConnection.createTcpConnection(args) as router:
        # Create required services
        base = BaseClient(router)
        base_cyclic = BaseCyclicClient(router)

        # TODO: Decidir qual a saída de dados
        actions = [[0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
                   [25.0, 25.0, 25.0, 25.0, 25.0, 25.0], [50.0, 50.0, 50.0, 50.0, 50.0, 50.0]]

        # Example core
        success = True

        success &= move_to_position(base, position='Home')
        success &= move_to_position(base, position='Zero')

        # TODO: Tem que passar o objeto que contem os movimentos específicos
        success &= create_sequence(base, actions, sequence_name='tecla1')

        success &= move_to_position(base, position='Retract')

        # You can also refer to the 110-Waypoints examples if you want to execute
        # a trajectory defined by a series of waypoints in joint space or in Cartesian space

        return 0 if success else 1


if __name__ == "__main__":
    exit(main())
