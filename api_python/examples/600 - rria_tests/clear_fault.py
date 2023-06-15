import sys
import os
from api_python.examples import utilities

from kortex_api.autogen.client_stubs.BaseClientRpc import BaseClient
from kortex_api.autogen.messages import Base_pb2


def compute_kinematics(base):
    # Use Base_pb2 class
    algo = Base_pb2.GripperCommand()

    # Use BaseCliente class
    print(base.SendGripperCommand(algo))



def main():
    # Import the utilities helper module
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # Parse arguments
    args = utilities.parseConnectionArguments()

    # Create connection to the device and get the router
    with utilities.DeviceConnection.createTcpConnection(args) as router:
        # Create required services
        base = BaseClient(router)

        # Example core
        compute_kinematics(base)


if __name__ == "__main__":
    main()
