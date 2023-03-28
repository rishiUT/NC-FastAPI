import sqlalchemy
import databases
from pydantic import BaseModel
import asyncio



DATABASE_URL = "postgresql://rishi:Password1@localHost:5432/nc7"
database = databases.Database(DATABASE_URL)


metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("partnerid", sqlalchemy.Integer),
    sqlalchemy.Column("mturkid", sqlalchemy.String),
    sqlalchemy.Column("partnermturkid", sqlalchemy.String),
    sqlalchemy.Column("conversationid", sqlalchemy.Integer),
    sqlalchemy.Column("role", sqlalchemy.Integer),
    sqlalchemy.Column("itemid", sqlalchemy.Integer),
    sqlalchemy.Column("goal", sqlalchemy.Integer),
    sqlalchemy.Column("offer", sqlalchemy.Integer),
    sqlalchemy.Column("offeraccepted", sqlalchemy.Boolean),
    sqlalchemy.Column("convactive", sqlalchemy.Boolean),
    sqlalchemy.Column("convdisconnected", sqlalchemy.Boolean) # False if the negotiation reached a conclusion, true otherwise
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={}
)
metadata.create_all(engine)

class User(BaseModel):
    id: int
    partnerid: int
    mturkid: str
    partnermturkid: str
    conversationid: int
    role: int
    itemid: int
    goal: int
    offer: int
    offeraccepted: bool
    convactive: bool
    convdisconnected: bool

async def create_list():
    await database.connect()
    query = users.select()
    user_list = await database.fetch_all(query)
    # Get all users by conversation id
    finished_users = []
    for user in user_list:
        disconnected = bool(user.convdisconnected)
        if not disconnected:
            finished_users.append(user)

    finished_conversations = [user.conversationid for user in finished_users]
    finished_conversations.sort()
    finished_conversations = list(dict.fromkeys(finished_conversations))

    for conversation in finished_conversations:
        id = conversation
        num_messages = 0
        message_length = 0
        seller_id = 0
        buyer_id = 0
        seller_goal = 0
        buyer_goal = 0
        offer = 0
        negotiation_success = None

        for user in finished_users:
            if user.conversationid == conversation:
                if user.role == 0:
                    # This is a seller
                    seller_id = user.id
                    seller_goal = user.goal
                    offer = user.offer
                    negotiation_success = user.offeraccepted
                
                if user.role == 1:
                    # This is a seller
                    buyer_id = user.id
                    buyer_goal = user.goal
                    offer = user.offer
                    negotiation_success = user.offeraccepted
        
        to_print = ""
        to_print += str(id) + "\t"
        to_print += str(num_messages) + "\t"
        to_print += str(message_length) + "\t"
        to_print += str(seller_id) + "\t"
        to_print += str(buyer_id) + "\t"
        to_print += str(seller_goal) + "\t"
        to_print += str(buyer_goal) + "\t"
        to_print += str(offer) + "\t"
        to_print += str(negotiation_success)

        print(to_print)




asyncio.run(create_list())