from enum import IntEnum as Enum
import time
import threading
from debughelper import DebugPrinter
from disconnect_checker.user import User
from disconnect_checker.conversation import Conversation
import random
import json

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
    PARTNER_DISCONNECT_UNPAID = 4 # The user's partner disconnected before any communication occurred

class ConnectionErrors(Enum):
    NO_PARTNER_FOUND = -1
    CONNECTION_TIMEOUT = -2

class Message:
    def __init__(self):
        self.sender_id = -1
        self.timestamp = -1
        self.filename = "unknown"

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp

    def set_filename(self, name):
        self.filename = name

    def set_sender(self, id):
        self.sender_id = id

class DisconnectChecker:
    def __init__(self):
        self.users = dict()
        self.conversations = dict()
        self.last_timeout_check = int(time.time()) # Ensures we only check for timeouts periodically instead of constantly
        self.pairing_timeout_length = 120
        self.timeout_length = 120
        self.timeout_check_freq = 60
        self.conv_start_timeout = 20
        self.pairing_count = 0
        self.user_table_lock = threading.Lock()
        self.printer = None
                
        with open('static/filtered_train.json') as item_file:
            self.items = json.load(item_file)

    def add_debug_printer(self, printer: DebugPrinter):
        self.printer = printer

    def set_pairing_count(self, pairing_count: int):
        self.pairing_count = pairing_count

    # Add the user to the table of currently active users
    def initialize_user(self, uid: int):
        self.printer.print("Now initializing user with id " + str(uid))
        self.user_table_lock.acquire()
        #self.printer.print("Acquired lock in initialize_user")
        self.users[uid] = User(uid, int(time.time()))
        self.user_table_lock.release()

    def create_pairing(self, uid: int):
        curr_user = self.users[uid]
        if curr_user.get_partner() != -1:
            # This user already has a partner/has had a partner in the past
            #self.printer.print("User has a partner already, user {}".format(curr_user.get_partner()))
            return curr_user.get_conv_id()
        elif (curr_user.time_since_last_ping(int(time.time())) > self.pairing_timeout_length):
            # This user has been waiting too long. Time to time out.
            self.printer.print("User timed out.")
            return ConnectionErrors.CONNECTION_TIMEOUT

        #self.printer.print("Acquiring lock in create_pairing")
        self.user_table_lock.acquire()
        #self.printer.print("Acquired lock in create_pairing")
        for user_key in self.users:
            user = self.users[user_key]
            if user is not curr_user and user.get_partner() == -1:
                new_conv = Conversation()
                conv_id = self.pairing_count
                new_conv.set_id(conv_id)
        
                item_id = conv_id % len(self.items) #Pseudo-randomization; not actually random, but rarely repeats
                new_conv.set_item(item_id)
                        
                buyer_coefficients = [0.6, 0.65, 0.7, 0.75]
                seller_coefficients = [0.8, 0.85, 0.9, 0.95]
                seller_coefficient = random.choice(seller_coefficients)
                buyer_coefficient = random.choice(buyer_coefficients)

                if random.random() > 0.5:
                    seller = uid
                    buyer = user.get_id()
                    curr_user_role = "Seller"
                    partner_role = "Buyer"
                    
                else:
                    seller = user.get_id()
                    buyer = uid
                    curr_user_role = "Buyer"
                    partner_role = "Seller"
                
                new_conv.set_seller(seller)
                new_conv.set_seller_coefficient(seller_coefficient)
                new_conv.set_buyer(buyer)
                new_conv.set_buyer_coefficient(buyer_coefficient)
                self.conversations[self.pairing_count] = new_conv
                
                # This is another unpaired user
                curr_user.add_partner(user.get_id())
                curr_user.add_conv_id(self.pairing_count)
                curr_user.add_role(curr_user_role)

                user.add_partner(uid)
                user.add_conv_id(self.pairing_count)
                user.add_role(partner_role)

                self.pairing_count += 1
                self.printer.print("Users {} and {} were paired!".format(str(curr_user.get_id()), str(user.get_id())))
                self.user_table_lock.release()
                return self.pairing_count - 1

        # No unpaired users currently exist
        #self.printer.print("So far, no partners available.")
        self.user_table_lock.release()
        return ConnectionErrors.NO_PARTNER_FOUND

    def get_item_info(self, uid: int):
        curr_user = self.users[uid]
        conv = self.conversations[curr_user.get_conv_id()]
        return conv.item_id, conv.buyer_coefficient, conv.seller_coefficient

    def get_user_conv_id(self, uid: int):
        return self.users[uid].get_conv_id()

    def get_user_role(self, uid:int):
        return self.users[uid].get_role()

    def get_user_partner(self, uid:int):
        return self.users[uid].get_partner()

    def user_start_conv(self, uid: int):
        curr_user = self.users[uid]
        if not curr_user.started_conversation():
            curr_user.start_conversation()

    def user_get_time_elapsed(self, uid: int):
        curr_user = self.users[uid]
        return curr_user.get_time_elapsed()

    def conv_set_item(self, uid: int, item_id: int):
        user = self.users[uid]
        conv = self.conversations[user.get_conv_id()]
        conv.set_item(item_id)

    def conv_set_offer(self, uid: int, offer_val: int):
        user = self.users[uid]
        conv = self.conversations[user.get_conv_id()]
        conv.set_offer(offer_val)

    def conv_set_offer_accepted(self, uid: int, accepted: bool):
        user = self.users[uid]
        conv = self.conversations[user.get_conv_id()]
        conv.set_accepted(accepted)
        conv.set_disconnect(False)

    def conv_add_message(self, uid: int, message: Message):
        user = self.users[uid]
        conv = self.conversations[user.get_conv_id()]
        conv.add_message(message)

    def get_user_conv(self, uid:int):
        user = self.users[uid]
        conv = self.conversations[user.get_conv_id()]
        return conv

    def conv_print(self, uid: int, printer):
        if uid in self.users:
            user = self.users[uid]
            conv = self.conversations[user.get_conv_id()]
            conv.print()
        else:
            printer.print("User missing:")
            printer.print(uid)
            printer.print(self.users)

    # Remove the user from the "current users" list once they complete the task
    def safe_delete_user(self, uid: int):
        self.printer.print("User " + str(uid) + " has completed the task! Congratulations!")
        #print("User " + str(uid) + " has completed the task! Congratulations!")
        curr_user = self.users[uid]
        pid = curr_user.get_partner()
        if (pid != -1 and pid != -2):
            #print("Handling the case where a partner existed")
            partner = self.users[pid]
            partner.remove_partner(True) # The partner's partner succeeded!

            # Note that, to reach this point, this user must have a complete conversation.
            # We want to print that conversation, then remove it from the list.
            conv_id = curr_user.get_conv_id()
            conv = self.conversations[conv_id]
            conv.print()
            self.conversations.pop(conv_id)
            
        # Since the partner's reference to this user was removed,
        # It should be safe to take them out of the users table.
        self.remove_user(uid)

    # Remove the user if they have timed out and have likely disconnected. They have not completed the task.
    def unsafe_delete_user(self, uid: int):
        self.printer.print("User " + str(uid) + " has timed out.")
        curr_user = self.users[uid]
        pid = curr_user.get_partner()
        if (pid != -1 and pid != -2):
            partner = self.users[pid]
            partner.remove_partner(False) # The partner's partner failed.
            # Note that a conversation must have been started, and is no longer relevant.
            # Remove the conversation. 
            conv_id = curr_user.get_conv_id()
            conv = self.conversations[conv_id]
            conv.print()
            self.conversations.pop(conv_id)
        curr_user.disconnect()
        # Since the current user is disconnected, and the partner's reference to this user was removed,
        # It should be safe to take them out of the users table.
        # TODO: Add error handling for disconnected users that reconnect, then remove disconnected users from the table
        self.remove_user(uid)

    # update the current user's latest updated time.
    def ping_user(self, uid: int):
        #self.printer.print("User " + str(uid) + " has pinged the server.")

        if uid in self.users:
            curr_user = self.users[uid]
            curr_time = int(time.time())
            curr_user.ping(curr_time)
            if (curr_time >= self.last_timeout_check + self.timeout_check_freq):
                self.last_timeout_check = curr_time
                self.check_for_disconnects()

            if curr_user.check_connection_failure():
                #self.printer.print("The user's partner has failed. Re-pair this user.")
                if curr_user.started_conversation():
                    return PingErrors.PARTNER_DISCONNECT
                else:
                    return PingErrors.PARTNER_DISCONNECT_UNPAID # The conversation hasn't started yet, so they aren't paid for anything.

            return PingErrors.NORMAL

        #self.printer.print("The user has previously timed out.")
        return PingErrors.USER_DISCONNECT

    def print_users(self):
        curr_time = int(time.time())
        #self.printer.print("Acquiring lock in print_users")
        self.user_table_lock.acquire()
        #self.printer.print("Acquired lock in print_users")
        for key in self.users:
            self.printer.print("User " + str(self.users[key].get_id()) + " last pinged " + str(self.users[key].time_since_last_ping(curr_time)) + " seconds ago.")
        self.user_table_lock.release()

    def user_is_active(self, uid:int):
        return True if uid in self.users else False

    # Checks the users table for users who have timed out.
    def check_for_disconnects(self):
        #self.printer.print("Checking for disconnected users")
        curr_time = int(time.time())
        to_remove = []
        #self.printer.print("Acquiring lock in check_for_disconnects")
        self.user_table_lock.acquire() # When looping through users, make sure nobody edits users
        #self.printer.print("Acquired lock in check_for_disconnects")
        for key in self.users:
            user = self.users[key]
            #self.printer.print("User " + str(user.get_id()) + " last pinged " + str(user.time_since_last_ping(curr_time)) + " seconds ago.")
            if (user.time_since_last_ping(curr_time) > self.timeout_length):
                # The user hasn't responded for 5 minutes or longer.
                #self.printer.print("User " + str(user.get_id()) + " timed out.")
                to_remove.append(key)
                # We'll delete these later, when deleting elements won't mess up the dictionary we're looping through
        self.user_table_lock.release()
        for key in to_remove:
            self.unsafe_delete_user(key)

    # Remove a disconnected user from the user table.
    def remove_user(self, uid: int):
        #self.printer.print("Removing a user from the users table")
        # This removes a user if they exist. If they've already been removed, do nothing.
        if uid in self.users:
            self.user_table_lock.acquire()
            self.users.pop(uid)
            self.user_table_lock.release()

