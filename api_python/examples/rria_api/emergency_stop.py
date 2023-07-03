import threading

from pynput import keyboard
from kortex_api.autogen.messages import Base_pb2

TIMEOUT_DURATION = 20


class EmergencyStop:
    def __init__(self, base):
        self.notification_handle = None
        self.flag_error = False
        self.base = base

    def on_press(self, key):
        try:
            print(f'alphanumeric key {key.char} pressed')
        except AttributeError:
            print(f'special key {key} pressed')
            self.base.ApplyEmergencyStop()
            self.base.Unsubscribe(self.notification_handle)

    @staticmethod
    def check_for_end_or_abort(event_to_signal):
        """Return a closure checking for END or ABORT notifications

        Arguments:
        event_to_signal -- event to signal when the action is completed
            (will be set when an END or ABORT occurs)
        """

        def check(notification, event=event_to_signal):
            print("EVENT : " + Base_pb2.ActionEvent.Name(notification.action_event))
            if notification.action_event == Base_pb2.ACTION_END or notification.action_event == Base_pb2.ACTION_ABORT:
                event.set()

        return check

    def emergency_stop(self):
        print('avaliando stop')
        e = threading.Event()
        self.notification_handle = self.base.OnNotificationActionTopic(
            self.check_for_end_or_abort(e),
            Base_pb2.NotificationOptions()
        )

        listener = keyboard.Listener(on_press=self.on_press)
        listener.start()
