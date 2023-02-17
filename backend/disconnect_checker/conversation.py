class Conversation:
    def __init__(self):
        self.id = -1
        self.item_id = -1
        self.buyer_id = -1
        self.seller_id = -1
        self.messages = []
        self.offer_value = -1
        self.offer_accepted = False
        self.disconnected = True

    def set_id(self, id):
        self.id = id

    def set_item(self, id):
        self.item_id = id

    def set_buyer(self, id):
        self.buyer_id = id

    def set_seller(self, id):
        self.seller_id = id

    def add_message(self, message):
        self.messages.append(message)
    
    def set_offer(self, val):
        self.offer_value = val

    def set_accepted(self, offer_acceptance_bool):
        self.offer_accepted = offer_acceptance_bool

    def set_disconnect(self, disconnect_bool):
        self.disconnected = disconnect_bool

    def get_metadata(self, uid: int):
        md = dict()
        m_idx = 0
        for message in self.messages:
            message = dict()
            message["sender"] = "self" if message.sender_id == uid else "partner"
            message["timestamp"] = message.timestamp
            message["file_name"] = message.filename
            md[m_idx] = message
            m_idx += 1

        return md

    def print(self):
        # Print all data to a file. This should be a unique file.
        print("Printing conversation to a file")
        file_name = "conversations/conversation_"
        file_name += str(self.id)
        file_name += ".txt"
        with open(file_name, "w") as file1:
            to_print = "Conversation Data for Conversation "
            to_print += str(self.id)
            to_print += "\n"
            file1.write(to_print)
            to_print = "Negotiation over item "
            to_print += str(self.item_id)
            to_print += "\n"
            file1.write(to_print)
            to_print = "Buyer has id = "
            to_print += str(self.buyer_id)
            to_print += "\n"
            file1.write(to_print)
            to_print = "Seller has id = "
            to_print += str(self.seller_id)
            to_print += "\n"
            file1.write(to_print)
            for message in self.messages:
                to_print = "Message sent by "
                to_print += str(message.sender_id)
                to_print += " at time "
                to_print += str(message.timestamp)
                to_print += " saved in file "
                to_print += str(message.filename)
                to_print += "\n"
                file1.write(to_print)
            to_print = "Amount offered by buyer was "
            to_print += str(self.offer_value)
            to_print += "\n"
            file1.write(to_print)
            if self.offer_accepted:
                to_print = "The offer was accepted"
            else:
                to_print = "The offer was declined"
            to_print += "\n"
            file1.write(to_print)
            file1.close()

        
