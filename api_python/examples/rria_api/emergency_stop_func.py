from pynput import keyboard
import threading

from kortex_api.autogen.messages import Base_pb2

TIMEOUT_DURATION = 20
flag_error = False


def on_press(key, base):
    try:
        print(f'alphanumeric key {key.char} pressed')
    except AttributeError:
        if str(key) == 'Key.space':
            base.ApplyEmergencyStop()
            print('morreu aqui')


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


def emergency_stop_old(base):
    flag_button = False

    e = threading.Event()
    notification_handle = base.OnNotificationActionTopic(
        check_for_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    if flag_button:
        base.ApplyEmergencyStop()

        e.wait(TIMEOUT_DURATION)
        base.Unsubscribe(notification_handle)

        print("Emergency stop applied")
    else:
        e.wait(TIMEOUT_DURATION)
        base.Unsubscribe(notification_handle)

        print("Movement finished without emergency stop")
        return True


def emergency_stop(base):
    print('avaliando stop')
    e = threading.Event()
    notification_handle = base.OnNotificationActionTopic(
        check_for_end_or_abort(e),
        Base_pb2.NotificationOptions()
    )

    def on_press(key):
        try:
            print(f'alphanumeric key {key.char} pressed')
        except AttributeError:
            if str(key) == 'Key.space':
                base.ApplyEmergencyStop()
                base.Unsubscribe(notification_handle)
                print('morreu aqui')

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
