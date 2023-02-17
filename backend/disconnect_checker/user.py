from enum import IntEnum as Enum
import time
import threading
from debughelper import DebugPrinter

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

class User:
    def __init__(self, id, current_time):
        self.id = id
        self.last_ping = current_time
        self.partner_status = PartnerStatuses.UNPAIRED
        self.partner_id = -1
        self.status = Statuses.CONNECTING
        self.conv_id = -1
        self.role = "-"
        self.started_conv = False

    def add_partner(self, partner_id: int):
        self.partner_id = partner_id
        self.partner_status = PartnerStatuses.PAIRED
        self.status = Statuses.CONNECTED

    def get_partner(self):
        return self.partner_id

    def add_role(self, role):
        self.role = role

    def get_role(self):
        return self.role

    def remove_partner(self, success: bool):
        if success:
            self.partner_status = PartnerStatuses.CONNECTION_COMPLETE
            self.status = Statuses.CONNECTION_COMPLETE
        else:
            self.partner_status = PartnerStatuses.DISCONNECTED
            self.status = Statuses.CONNECTION_FAILED
        self.partner_id = -2
        self.conv_id = -2 # Delete any conversation as well, as it's no longer relevant.

    def get_id(self):
        return self.id

    def add_conv_id(self, conv_id: int):
        self.conv_id = conv_id

    def get_conv_id(self):
        return self.conv_id

    def ping(self, current_time):
        self.last_ping = current_time

    def time_since_last_ping(self, current_time):
        return current_time - self.last_ping

    def disconnect(self):
        self.status = Statuses.DISCONNECTED

    def check_connection_failure(self):
        return (self.status == Statuses.CONNECTION_FAILED)

    def check_status(self):
        return self.status
    
    def started_conversation(self):
        return self.started_conv

    def start_conversation(self):
        self.started_conv = True
