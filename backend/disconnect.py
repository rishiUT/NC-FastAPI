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
    DISCONNECTED = 4 # This user disconnected
    CONNECTION_FAILED = 5 # The user's partner disconnected

class PingErrors(Enum):
    NORMAL = 1
    USER_DISCONNECT = 2 # This user disconnected
    PARTNER_DISCONNECT = 3 # The user's partner disconnected

class User:
    def __init__(self, id, current_time):
        self.id = id
        self.last_ping = current_time
        self.partner_status = PartnerStatuses.UNPAIRED
        self.partner_id = -1
        self.status = Statuses.CONNECTING

    def add_partner(self, partner_id):
        self.partner_id = partner_id
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

    def disconnect(self):
        self.status = Statuses.DISCONNECTED

    def get_partner(self):
        return self.partner_id

    def check_connection_failure(self):
        return (self.status == Statuses.CONNECTION_FAILED)

class DisconnectChecker:
    def __init__(self):
        self.users = {}
        self.last_timeout_check = int(time.time()) # Ensures we only check for timeouts periodically instead of constantly
        self.timeout_length = 300
        self.timeout_check_freq = 300

    # Add the user to the table of currently active users
    def initialize_user(self, uid: int):
        print("Now initializing user with id " + str(uid))
        self.users[uid] = User(uid, int(time.time()))

    # Add a partner for this particular user. Make sure both users have the partner status "paired".
    def add_partner(self, uid: int, partner_id: int):
        print("Adding partner " + str(partner_id) + " to user " + str(uid))
        curr_user = self.users[uid]
        curr_user.add_partner(partner_id)

    # Remove the user from the "current users" list once they complete the task
    def safe_delete_user(self, uid: int):
        print("User " + str(uid) + " has completed the task! Congratulations!")
        curr_user = self.users[uid]
        pid = curr_user.get_partner()
        if (pid != -1):
            partner = self.users[pid]
            partner.remove_partner(True) # The partner's partner succeeded!
        # Since the partner's reference to this user was removed,
        # It should be safe to take them out of the users table.
        self.remove_user(uid)

    # Remove the user if they have timed out and have likely disconnected. They have not completed the task.
    def unsafe_delete_user(self, uid: int):
        print("User " + str(uid) + " has timed out.")
        curr_user = self.users[uid]
        pid = curr_user.get_partner()
        if (pid != -1):
            partner = self.users[pid]
            partner.remove_partner(False) # The partner's partner failed.
        curr_user.disconnect()
        # Since the current user is disconnected, and the partner's reference to this user was removed,
        # It should be safe to take them out of the users table.
        # TODO: Add error handling for disconnected users that reconnect, then remove disconnected users from the table
        self.remove_user(uid)

    # update the current user's latest updated time.
    def ping_user(self, uid: int):
        print("User " + str(uid) + " has pinged the server.")
        print(uid)
        print(type(uid))
        for key in self.users.keys():
            print(key)
            print(type(key))
        print(self.users[uid])
        if uid in self.users:
            curr_user = self.users[uid]
            curr_time = int(time.time())
            curr_user.ping(curr_time)
            if (curr_time >= self.last_timeout_check + self.timeout_check_freq):
                self.last_timeout_check = curr_time
                self.check_for_disconnects()

            if curr_user.check_connection_failure():
                print("The user's partner has failed. Re-pair this user.")
                return PingErrors.PARTNER_DISCONNECT

            return 0

        print("The user has previously timed out. Re-pair this user.")
        return PingErrors.USER_DISCONNECT

    def print_users(self):
        curr_time = int(time.time())
        for key in self.users:
            print("User " + str(self.users[key].id) + " last pinged " + str(self.users[key].time_since_last_ping(curr_time)) + " seconds ago.")

    # Checks the users table for users who have timed out.
    def check_for_disconnects(self):
        print("Checking for disconnected users")
        curr_time = int(time.time())
        for key in self.users:
            user = self.users[key]
            print("User " + str(user.id) + " last pinged " + str(user.time_since_last_ping(curr_time)) + " seconds ago.")
            if (user.time_since_last_ping(curr_time) > self.timeout_length):
                # The user hasn't responded for 5 minutes or longer.
                print("User " + str(user.id) + " timed out.")
                self.unsafe_disconnect_user(user.id)

    # Remove a disconnected user from the user table.
    def remove_user(self, uid: int):
        print("Removing a user from the users table")
        self.users.pop(uid)
