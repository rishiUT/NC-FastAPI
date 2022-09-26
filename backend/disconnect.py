from enum import Enum
import time
 
class PartnerStatuses(Enum):
    UNPAIRED = 1
    PAIRED = 2
    CONNECTION_COMPLETE = 3
    DISCONNECTED = 4

class Statuses(Enum):
    CONNECTING = 1
    CONNECTED = 2
    CONNECTION_COMPLETE = 3
    DISCONNECTED = 4
    CONNECTION_FAILED = 5


class User:
    def __init__(self, id, current_time):
        self.id = id
        self.last_ping = current_time
        self.partner_status = PartnerStatuses.UNPAIRED
        self.partner_id = -1
        self.status = Statuses.CONNECTING

    def add_partner(self, partner_id, current_time):
        self.partner_id = partner_id
        self.last_ping = current_time
        self.partner_status = PartnerStatuses.PAIRED
        self.status = Statuses.CONNECTED

    def ping(self, current_time):
        self.last_ping = current_time

    def remove_partner(self, success: bool):
        if success:
            self.partner_status = PartnerStatuses.CONNECTION_COMPLETE
            self.status = Statuses.CONNECTION_COMPLETE
        else:
            self.partner_status = PartnerStatuses.DISCONNECTED
            self.status = Statuses.CONNECTION_FAILED
        self.partner_id = -1

    def time_since_last_ping(self, current_time):
        return current_time - self.last_ping

class DisconnectChecker:
    def __init__(self):
        self.users = {}

    # Add the user to the table of currently active users
    def initialize_user(self, uid: int):
        print("Now initializing user with id " + str(uid))
        self.users[uid] = User(uid, int(time.time()))

    # Add a partner for this particular user. Make sure both users have the partner status "paired".
    def add_partner(self, uid: int, partner_id: int):
        print("Adding partner " + str(partner_id) + " to user " + str(uid))

    # Remove the user from the "current users" list once they complete the task
    def safe_delete_user(self, uid: int):
        print("User " + str(uid) + " has completed the task! Congratulations!")

    # Remove the user if they have timed out and have likely disconnected. They have not completed the task.
    def unsafe_delete_user(self, uid: int):
        print("User " + str(uid) + " has timed out.")

    # update the current user's latest updated time, then check for timeouts.
    def ping_user(self, uid: int):
        print("User " + str(uid) + " has pinged the server.")
