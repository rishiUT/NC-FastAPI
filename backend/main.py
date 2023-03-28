import asyncio
from telnetlib import NOP
from fastapi import FastAPI, Response, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape
import sqlalchemy
import databases
from connectionmanager import ConnectionManager
import json
import datetime
from disconnect import DisconnectChecker as UserManager, ConnectionErrors, PingErrors, Message
import threading
from debughelper import DebugPrinter
from cgi import test
import os
import glob
import math
from pydub import AudioSegment

#DATABASE_URL = "sqlite:///./dbfolder/users.db"
DATABASE_URL = "postgresql://rishi:Password1@localHost:5432/nc7"
database = databases.Database(DATABASE_URL)
database_lock = threading.Lock()

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

TASK_DESCRIPTIONS = ["Your goal for this task is to sell this item for as close to the listing price as possible. You will negotiate with your assigned buyer using recorded messages. Once the buyer chooses to make an offer, you may either accept or reject the offer.\nTo record a message, press and hold the button with the microphone symbol. You can listen to the message to make sure it sounds right, then click the “send” button to send it. You can also click any sent or received message to listen to them again.Each negotiation should be finished within 5 minutes. There is a timer at the top of the screen which tells you how much time has elapsed.\nFor more detailed instructions, click the \"Negotiation Instructions\" link at the top of the screen.\nHave fun, and good luck with your negotiation!",
                     "Your goal for this task is to convince the seller to sell you the item for as close to your goal price as possible. You will negotiate with the seller using recorded messages. At any point, you may make an offer of any price; however, once the seller accepts or rejects your offer, the negotiation is over. \nTo record a message, press and hold the button with the microphone symbol. You can listen to the message to make sure it sounds right, then click the 'send' button to send it. You can also click any sent or received message to listen to them again. \nHave fun, and good luck with your negotiation!"]

checker = UserManager()
printer = DebugPrinter()

debug_file = open("debug_log_3.txt", 'a')

printer.set_output_file(debug_file)
# printer.print("Starting Server")
checker.add_debug_printer(printer)

import sys
sys.stderr = debug_file

with open('static/filtered_train.json') as item_file:
    items = json.load(item_file)

app = FastAPI(title='Test')
app.mount("/static", StaticFiles(directory="static"), name="static")
env = Environment(
    loader=PackageLoader("ncserver"),
    autoescape=select_autoescape()
)


@app.on_event("startup")
async def startup():
    await database.connect()
    num_prev_pairings = await get_max_conv_id()
    num_prev_pairings += 1 # Because we use zero-based indexing
    checker.set_pairing_count(num_prev_pairings)
    

@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()

@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
async def home(request: Request, response: Response, assignmentId: str="None", hitId: str="None", turkSubmitTo: str="None", workerId: str="None"):
    uid = request.cookies.get('id')
    checked_in = request.cookies.get('checkedin')
    show_consent_form = False if checked_in == "True" else True
    response.set_cookie(key='checkedin', value=True, secure=True, samesite='none')
    if assignmentId != "None":
        response.set_cookie(key='mturkId', value=workerId, secure=True, samesite='none')
        response.set_cookie(key='assignmentId', value=assignmentId, secure=True, samesite='none')
        response.set_cookie(key='hitId', value=hitId, secure=True, samesite='none')
        response.set_cookie(key='turkSubmitTo', value=turkSubmitTo, secure=True, samesite='none')
        
    if uid:    
        response.delete_cookie('id')

    if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
        template = env.get_template("home2.html")
        return template.render(title="Home")
    elif assignmentId == "None":
        template = env.get_template("home3.html")
        print(show_consent_form)
        return template.render(title="Home", show=show_consent_form)
    else:
        template = env.get_template("home.html")
        return template.render(title="Home")


@app.get('/pair', response_class=HTMLResponse)
async def start(request: Request, response: Response):
    assignmentId = request.cookies.get('assignmentId')
    hitId = request.cookies.get('hitId')
    turkSubmitTo = request.cookies.get('turkSubmitTo')
    mturkId = request.cookies.get('mturkId')

    printer.print("Printing mturk data:")
    printer.print(assignmentId)
    printer.print(hitId)
    printer.print(turkSubmitTo)
    printer.print(mturkId)
    printer.print("End mturk data")
    
    uid = request.cookies.get('id')
    if uid:
        # The user should not be reaching this page with an active uid.
        response.delete_cookie('id')

    if assignmentId:
        # This is an mturk user
        uid = await check_if_mturk_active(mturkId)
        if not uid:
            # This user does not have an active conversation. Let's give them a new user ID.
            database_lock.acquire()
            query = users.insert().values(role=-1, partnerid=-1, mturkid=mturkId, partnermturkid="Invalid", conversationid=-1,
                                            itemid=-1, goal=-1, offer=-1, offeraccepted=False, convactive=False, 
                                            convdisconnected=True)
            last_record_id = await database.execute(query)
            # printer.print("Releasing lock")
            database_lock.release()

            uid = last_record_id
            response.set_cookie(key='id', value=uid, secure=True, samesite='none')
            checker.initialize_user(uid)
            int_uid = uid
        else:
            # This is an mturk user who is already in a conversation. We shouldn't send them to the pairing page.
            response.set_cookie(key='id', value=uid, secure=True, samesite='none')
            # Redirect to skip pairing and pair with the old partner
            record_url = '/record'
            response = RedirectResponse(url=record_url)
            return response
    else:
        # This is not an mturk user.
        print("Creating database element for non mturk user")
        database_lock.acquire()
        query = users.insert().values(role=-1, partnerid=-1, mturkid="Invalid", partnermturkid="Invalid", conversationid=-1,
                                        itemid=-1, goal=-1, offer=-1, offeraccepted=False, convactive=False, 
                                        convdisconnected=True)
        last_record_id = await database.execute(query)
        database_lock.release()
        print("database element created")
        uid = last_record_id
        response.set_cookie(key='id', value=uid, secure=True, samesite='none')
        checker.initialize_user(uid)
        int_uid = int(uid)

    username = "User " + str(uid)
    template = env.get_template("pairing.html")
    return template.render(title="Please Wait...", username=username, id=int_uid)

async def check_if_mturk_active(mturkid: str):
    # Check if the user is in the database with the given mturk id and convactive=True
    # If both of these are true, check the disconnect checker to see if they should have disconnected
    # If the result is PingErrors.NORMAL, return the id
    ua = users.alias("alias")
    query = sqlalchemy.select([ua.c.id]).where(ua.c.mturkid==mturkid).where(ua.c.convactive==True)
    uid = await database.fetch_all(query)
    printer.print(uid)
    if uid:
        for id in uid:
            printer.print(id)
            id = int(id[0])
            printer.print(id)
            if checker.user_is_active(id):
                pid = checker.get_user_partner(id)
                printer.print("The partner was...")
                printer.print(pid)
                if pid != -1:
                    return id
            else:
                # This user needs to have their database updated to show they aren't active
                await remove_user(id)
    return None
    
@app.get('/no_partner', response_class=HTMLResponse)
async def no_partner_found(request: Request, response: Response):
    uid = request.cookies.get('id')
    if uid:    
        response.delete_cookie('id')
        int_uid = int(uid)
        await remove_user(int_uid)

    username = "User " + str(uid)
    template = env.get_template("unpaired.html")
    return template.render(title="Sorry!", content="Thank you for your patience, " + username + ". Unfortunately, we couldn't find a partner for you. Please try again later.")

@app.get('/finish', response_class=HTMLResponse)
async def self_reset(request: Request, response: Response):
    printer.print("Entering the finish function")
    uid = request.cookies.get('id')
    assignmentId = request.cookies.get('assignmentId')
    hitId = request.cookies.get('hitId')
    turkSubmitTo = request.cookies.get('turkSubmitTo')

    if uid:
        response.delete_cookie('id')
    else:
        # This should not happen
        record_url = '/error/11'
        response = RedirectResponse(url=record_url)
        return response
    int_uid = int(uid)

    bonus_percentage = await calc_bonus(int_uid)

    text = "Thanks for your participation! Your score was " + str(bonus_percentage * 100) + "."
    text += " If you would like to participate again, please click the button below to return to the task start page."

    if assignmentId:
        printer.print("Deleting mturk cokokies")
        response.delete_cookie('assignmentId')
        response.delete_cookie('hitId')
        response.delete_cookie('turkSubmitTo')

        printer.print("Creating mturk submit text")
        url = turkSubmitTo
        url += "/mturk/externalSubmit?assignmentId="
        url += assignmentId
        url += "&bonus="
        url += str(bonus_percentage)

        printer.print("Putting together the text")
        text = "Thanks for your participation! Your bonus was $" + val_to_dollar_str(bonus_percentage) + "."
        text += " To submit your results to mechanical turk, click the button below."
        
        await remove_user(int_uid)
        printer.print("Putting together the mturk task completion page")
        template = env.get_template("mturk_submit.html")
        return template.render(title="Thank You!", content=text, url=url)
    await remove_user(int_uid)
    template = env.get_template("restart.html")
    return template.render(title="Thank You!", 
                            content=text)

def val_to_dollar_str(val):
    val *= 1.0
    result = str(val)
    if val % 10 == 0:
        result += "0"

    return result

async def calc_bonus(int_uid: int):
    printer.print("Gathering user data")
    query = users.select().where(users.c.id==int_uid)
    user = await database.fetch_all(query)
    user = user[0]

    printer.print("Getting partner data")
    query = users.select().where(users.c.id==int(user.partnerid))
    partner = await database.fetch_all(query)
    partner = partner[0]

    printer.print("Calculating bonus")
    offer_accepted = user.offeraccepted
    bonus_percentage = 0
    if offer_accepted:
        bonus_percentage = 1
        goal = int(user.goal)
        partner_goal = int(partner.goal)
        offer = int(user.offer)
        if partner_goal < goal:
            printer.print("partner was the buyer")
            # The user is the seller, so they had the larger goal. get_bonus returns their bonus.
            bonus_percentage += await get_bonus(partner_goal, offer, goal)
        else:
            printer.print("partner was the seller")
            # The user was the buyer, so get_bonus returns the inverse of their bonus.
            bonus_percentage += 1 - await get_bonus(goal, offer, partner_goal)

    # Round to the nearest 100th
    bonus_percentage = math.floor(bonus_percentage * 100)
    bonus_percentage /= 100
    return bonus_percentage
    
async def get_bonus(smaller_goal, offer, larger_goal):
    # Returns the percentage of the bonus that should be given to the seller (who has the larger goal)
    diff = larger_goal - smaller_goal
    offer_in_range = offer - smaller_goal
    bonus_percentage = offer_in_range / diff
    # If this is greater than 1, the person with the larger goal got a better score than they were asked for.
    # If it is less than 0, the person with the smaller goal got a better score than they were asked for.
    if bonus_percentage < 0:
        # Perfect score!
        return 0
    elif bonus_percentage > 1:
        # The other person got the perfect score.
        return 1
    else:
        return bonus_percentage

@app.get('/resetusers', response_class=HTMLResponse)
async def reset_users():
    query = users.delete()
    await database.execute(query)
    template = env.get_template("default.html")
    return template.render(title="Database Cleared", 
                            content="The database is empty now.")

async def print_user_in_database(uid: int):
    query = users.select().where(users.c.id==uid)
    info = await database.fetch_all(query)
    printer.print(uid)

    for user in info:
        printer.print(user)
        printer.print("id: " + str(user.id))
        printer.print("partnerid: " + str(user.partnerid))
        printer.print("mturkid: " + str(user.mturkid))
        printer.print("partnermturkid: " + str(user.partnermturkid))
        printer.print("conversationid: " + str(user.conversationid))
        printer.print("role: " + str(user.role))
        printer.print("itemid: " + str(user.itemid))
        printer.print("goal: " + str(user.goal))
        printer.print("offer: " + str(user.offer))
        printer.print("offeraccepted: " + str(user.offeraccepted))

async def add_user_conv_info(uid: int, pid: int, conv_id: int, role: int, item_id: int, item_price: int):
    # Save all this information into the database
    # printer.print("acquiring lock")
    database_lock.acquire()
    query = sqlalchemy.update(users)
    query = query.where(users.c.id == uid)
    query = query.values({"role": role, "partnerid": pid, "conversationid": conv_id, "itemid": item_id, "goal": item_price, "convactive": True})
    await database.execute(query)

    # await print_user_in_database(uid)

    # printer.print("Releasing lock")
    database_lock.release()

async def get_max_conv_id():
    # Get the conversation id from the database with the highest value
    query = users.select()
    user_list = await database.fetch_all(query)
    # Get all users by conversation id
    convIDs = [user.conversationid for user in user_list]

    maxID = 0
    for convID in convIDs:
        # For each conversation id, search users for two matching conversation ids
        convID = int(convID)
        if maxID < convID:
            maxID = convID
    
    return maxID

@app.get('/convuser/{uid}')
async def get_conversation(uid: int):
    conv = checker.get_user_conv(uid)
    metadata = json.dumps(conv.get_metadata(uid))
    return metadata
    
@app.get('/messagedata/{filename}')
async def get_conversation(uid: int):
    file = None
    return file

@app.get('/record', response_class=HTMLResponse)
async def record(request: Request):
    printer.print("Setting up chat page")
    uid = request.cookies.get('id')
    int_uid = int(uid)
    # printer.print("getting keepalive")
    keepalive = checker.ping_user(int_uid)

    if keepalive == PingErrors.NORMAL:
        # printer.print("keepalive = true")
        role_txt = checker.get_user_role(int_uid)
        conv_id = checker.get_user_conv_id(int_uid)
        partner_id = checker.get_user_partner(int_uid)

        is_buyer = (role_txt == "Buyer")

        item_id = conv_id % len(items) #Pseudo-randomization; not actually random, but rarely repeats
        checker.conv_set_item(int_uid, item_id)

        item_data = items[item_id]

        price_coefficient = 1
        if is_buyer:
            price_coefficient = 0.8
        item_price = item_data['Price'] * price_coefficient
        item_price = round(item_price)

        printer.print("adding info to the database")
        await add_user_conv_info(int_uid, partner_id, conv_id, is_buyer, item_id, item_price)

        item_description = item_data['Description'][0]

        image = None 
        # printer.print("getting image")
        if len(item_data['Images']):
            image = "/static/images/" + item_data['Images'][0]
        else:
            image = None
        if (is_buyer):
            template = env.get_template("audioinput_buyer.html")
        else:
            template = env.get_template("audioinput_seller.html")
        
        # printer.print("Connection page ready and sending")
        return template.render(title="Record Audio", role=role_txt, task_description=TASK_DESCRIPTIONS[is_buyer], goal_price=item_price,
        item_description=item_description, item_image=image, id=int_uid, conv_id=checker.get_user_conv_id(int_uid))
    else:
        # Redirect to handle a failed user
        int_error = keepalive.value
        error_url = '/error/' + str(int_error)
        response = RedirectResponse(url=error_url)
        return response

@app.get('/error/{status}', response_class=HTMLResponse)
async def handle_ping_errors(status: PingErrors, request: Request, response: Response):
    uid = request.cookies.get('id')

    if uid:    
        response.delete_cookie('id')
        int_uid = int(uid)
        await remove_user(int_uid)

    

    assignmentId = request.cookies.get('assignmentId')
    turkSubmitTo = request.cookies.get('turkSubmitTo')
    if assignmentId == "None":
        template = env.get_template("restart.html")
    else:
        # This is an mturk user
        if (status == PingErrors.PARTNER_DISCONNECT):
            template = env.get_template("mturk_paid_disconnect.html")
            url = turkSubmitTo
            url += "/mturk/externalSubmit?assignmentId="
            url += assignmentId
            url += "&bonus=-1"
            return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. You will still be paid, but please try again later.", url=url)
        else:
            template = env.get_template("default.html")


    if (status == PingErrors.USER_DISCONNECT):
        return template.render(title="Timed Out", content="Sorry, it seems you timed out. Please try again later.")
    elif (status == PingErrors.PARTNER_DISCONNECT_UNPAID):
        return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. Please try again later.")
    elif (status == PingErrors.PARTNER_DISCONNECT):
        return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. Please try again later.")
    else:
        printer.print("There is an unexpected ping error")
        return template.render(title="Record Audio", content="Sorry, it seems something unexpected happened. Please try again later.")

manager = ConnectionManager()

@app.websocket("/audiowspaired/{uid}")
async def chat_ws_endpoint(websocket: WebSocket, uid:int):
    # printer.print("Websocket connected for chat page")
    ua = users.alias("alias")
    query = sqlalchemy.select([ua.c.conversationid]).where(ua.c.id==uid)
    convid = await database.fetch_all(query)
    convid = convid[0][0]

    query = sqlalchemy.select([ua.c.role]).where(ua.c.id==uid)
    is_buyer = await database.fetch_all(query)
    is_buyer = is_buyer[0][0]

    role_txt = "Buyer"
    if is_buyer == 0:
        role_txt = "Seller"

    int_uid = int(uid)

    await manager.connect(websocket, int_uid)
    int_pid = checker.get_user_partner(int_uid)
    if (int_pid == -1):
        printer.print("WARNING: No Partner Assigned.")

    # Don't start until both users have joined the conversation
    # If the partner hasn't activated their websocket within 10 seconds, go back to the pairing
    import time
    start_time = int(time.time())
    while not manager.partner_connected(int_pid) and (start_time + checker.conv_start_timeout) > int(time.time()):
        # The other user hasn't connected yet, but they still haven't timed out
        # Note that this timeout is usually shorter than the usual timeout
        # printer.print("The partner hasn't connected yet")
        await asyncio.sleep(2)

    if not manager.partner_connected(int_pid):
        printer.print("Partner did not connect in time.")
        error_code = PingErrors.PARTNER_DISCONNECT_UNPAID
        await manager.send_self_message(error_code.to_bytes(1, 'big'), int_uid)
    else:
        # Once users reach this point, they get paid for their effort.
        # If we want to change where this happens, we can.
        checker.user_start_conv(int_uid)
        time_elapsed = checker.user_get_time_elapsed(int_uid)
        if time_elapsed < 30:
            time_elapsed = 0
        # Send a message to the user allowing them to start recording.
        start_code = PingErrors.NORMAL
        await manager.send_self_message(start_code.to_bytes(1, 'big'), int_uid)
  
        # Send elapsed time
        time_elapsed_as_utf8 = str(time_elapsed).encode("utf-8")
        data_array = bytearray(time_elapsed_as_utf8)
        data_array.append(11)
        data = bytes(data_array)
        
        await manager.send_self_message(data, int_uid)

        conv = checker.get_user_conv(int_uid)
        for message in conv.messages:
            file_name = message.filename
            with open(file_name, "rb") as file1:
                data = file1.read()
                file1.close()
            self_is_sender = 1 if message.sender_id == int_uid else 0
            data_array = bytearray(data)
            data_array.append(self_is_sender)
            data_array.append(7)
            data = bytes(data_array)
            
            await manager.send_self_message(data, int_uid)

        if conv.offer_sent:
            offer_as_utf8 = str(conv.offer_value).encode("utf-8")
            data_array = bytearray(offer_as_utf8)
            data_array.append(8)
            data = bytes(data_array)
            
            await manager.send_self_message(data, int_uid)

        try:
            while True:
                data = await websocket.receive_bytes()
                keepalive = checker.ping_user(int_uid)
                if keepalive == PingErrors.NORMAL:
                    identifier = data[-1]
                    remaining_data = data[:-1] #Strip off last byte
                    # printer.print("The identifier is:")
                    # printer.print(identifier)
                    
                    if(identifier == 6):
                        # This is a voice message.

                        timestamp = datetime.datetime.now()
                        temp = "recordings/" + role_txt + "_" + str(int_uid) + "_" + str(timestamp) + ".mp3"
                        file_name = ""
                        for c in temp:
                            if c == ' ':
                                file_name += "_"
                            elif c == ':':
                                file_name += "-"
                            else:
                                file_name += c


                        printer.print(file_name)
                        with open(file_name, "wb") as file1:
                            file1.write(remaining_data)
                            file1.close()
                        
                        audio = AudioSegment.from_file(file_name)
                        audio = audio.set_frame_rate(16000)
                        audio = audio.set_channels(1)
                        audio = audio.set_sample_width(2)
                        # simple export
                        file_handle = audio.export("downgraded_" + file_name, format="mp3")

                        message = Message()
                        message.set_timestamp(timestamp)
                        message.set_filename(file_name)
                        message.set_sender(int_pid)
                        checker.conv_add_message(int_uid, message)

                        await manager.send_partner_message(data, int_pid)
                    elif (identifier == 51):
                        # This is an offer.
                        printer.print("This is an offer")
                        bytestring = remaining_data.decode("utf-8")
                        val = int(bytestring)

                        checker.conv_set_offer(int_uid, val)

                        # printer.print("acquiring lock")
                        database_lock.acquire()

                        query = sqlalchemy.update(users)
                        query = query.where(users.c.id == int_uid)
                        query = query.values({"offer": val})
                        await database.execute(query)

                        query = sqlalchemy.update(users)
                        query = query.where(users.c.id == int_pid)
                        query = query.values({"offer": val})
                        await database.execute(query)

                        # await print_user_in_database(int_uid)
                        # await print_user_in_database(int_pid)

                        # printer.print("Releasing lock")
                        database_lock.release()

                        await manager.send_partner_message(data, int_pid)
                    elif (identifier == 52):
                        # An offer was either accepted or declined.
                        printer.print("Response received")
                        bytestring = remaining_data.decode("utf-8")
                        val = int(bytestring)
                        response = bool(val)

                        checker.conv_set_offer_accepted(int_uid, response)
                        
                        # printer.print("acquiring lock")
                        database_lock.acquire()

                        query = sqlalchemy.update(users)
                        query = query.where(users.c.id == int_uid)
                        query = query.values({"offeraccepted": response, "convdisconnected":False})
                        await database.execute(query)

                        query = sqlalchemy.update(users)
                        query = query.where(users.c.id == int_pid)
                        query = query.values({"offeraccepted": response, "convdisconnected":False})
                        await database.execute(query)

                        # await print_user_in_database(int_uid)
                        # await print_user_in_database(int_pid)

                        # printer.print("Releasing lock")
                        database_lock.release()
                        checker.conv_print(int_uid, printer)
                        # checker.safe_delete_user(int_uid) # Could remove user here, but safer to do it in finish page
                        await manager.send_partner_message(data, int_pid)
                    elif (identifier == 0):
                        printer.print("Unexpected behavior!")
                    elif (identifier == 1):
                        # printer.print("Received a ping")
                        identifier = identifier # Basically a no-op, but using NOP requires importing classes
                    elif (identifier == 9 or identifier == 10):
                        # These are "partner is recording" messages
                        # Just forward them, no need to save them
                        await manager.send_partner_message(data, int_pid)

                    else :
                        printer.print("Unexpected identifier:")
                        printer.print(identifier)
                        await manager.send_partner_message(data, int_pid)
                else:
                    await manager.send_self_message(keepalive.to_bytes(1, 'big'), int_uid)

        except WebSocketDisconnect:
            manager.disconnect(int_uid)

@app.websocket("/pairingws/{uid}")
async def pairing_ws(websocket: WebSocket, uid:int):
    int_uid = int(uid)
    try:
        await websocket.accept()

        async def read_from_socket(websocket: WebSocket):
            async for data in websocket.iter_bytes():
                ping_result = checker.ping_user(int_uid)
                if ping_result == PingErrors.USER_DISCONNECT:
                    val_to_send = 0
                    await websocket.send_bytes(val_to_send.to_bytes(1, 'big'))

        asyncio.create_task(read_from_socket(websocket))

        paired = checker.create_pairing(int_uid)
        val_to_send = 2 # When we terminate, this will be a boolean; until then, send an error code
        while paired == ConnectionErrors.NO_PARTNER_FOUND:
            await websocket.send_bytes(val_to_send.to_bytes(1, 'big'))
            paired = checker.create_pairing(int_uid)
            await asyncio.sleep(2)
            
        if paired == ConnectionErrors.CONNECTION_TIMEOUT:
            val_to_send = 0 # Essentially a value of "false"
        else:
            val_to_send = 1 # bool val = True

        await websocket.send_bytes(val_to_send.to_bytes(1, 'big'))

    except WebSocketDisconnect:
        printer.print("The user disconnected")
        # The user disconnected.
        # We could remove the user, but if they come back from a refresh we don't want them to be deleted.
        # checker.unsafe_delete_user(int_uid)

async def new_user_info():
    #No need to create a new id, because the db creates them automatically   
    query = users.select()
    user_list = await database.fetch_all(query)
    # Get all users by conversation id
    convIDs = [user.conversationid for user in user_list]

    maxID = 0
    for convID in convIDs:
        # For each conversation id, search users for two matching conversation ids
        convID = int(convID)
        numIDs = 0
        if maxID < convID:
            maxID = convID
        for otherID in convIDs:
            otherID = int(otherID)
            if otherID == convID:
                numIDs = numIDs + 1
        if numIDs < 2:
            # If you find one without a match, return it along with the "buyer" id
            return (1, convID)

    # If they all have a match, return the next conversation id (largest + 1) along with the "seller" id
    return (0, maxID + 1)

async def remove_user(uid: int):
    print("in remove user")
    # Find their entry in the database and ensure "convactive" is set to false
    database_lock.acquire()
    query = sqlalchemy.update(users)
    query = query.where(users.c.id == uid)
    query = query.values({"convactive": False})
    await database.execute(query)
    database_lock.release()
    
    # If they haven't already been removed from the checker, do so now
    if checker.user_is_active(uid):
        checker.safe_delete_user(uid)

async def add_pairing_checker(uid: int) -> bool:
    new_conv_id = checker.create_pairing(uid)
    if new_conv_id == -1:
        # No pairing could be found
        return False
    else:
        # A pairing was found! We aren't doing much with the convid, though
        return True

# TODO:
# Change the button image from a play button to a pause button while the audio plays, then change back when it stops
# add error handling at each user ping: handle user disconnects, partner disconnects
# Add separate "acknowledge completed task" message handlers for buyers and sellers (don't forward messages to finished buyers)

# Add something when the user tries to connect, and is waiting on a partner to connect. Maybe a scrolling wheel?

# There has to be a special case for disconnects once the entire interaction is complete
# Once the interaction reaches a certain point, users should be able to leave without 
# losing their payment or having their partner reassigned