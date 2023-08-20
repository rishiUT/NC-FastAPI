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
import random
import time
import sys


# Global Debugging Variables
checker = UserManager()
printer = DebugPrinter()

checker.add_debug_printer(printer)

sys.stderr = printer.output_file

# Database Variables
DATABASE_URL = "postgresql://rishi:Password1@localHost:5432/nc"
database = databases.Database(DATABASE_URL)
database_lock = threading.Lock()

metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("partnerid", sqlalchemy.Integer),
    sqlalchemy.Column("nonmturkid", sqlalchemy.Integer),
    sqlalchemy.Column("mturkid", sqlalchemy.String),
    sqlalchemy.Column("partnermturkid", sqlalchemy.String),
    sqlalchemy.Column("conversationid", sqlalchemy.Integer),
    sqlalchemy.Column("role", sqlalchemy.Integer),
    sqlalchemy.Column("itemid", sqlalchemy.Integer),
    sqlalchemy.Column("listingprice", sqlalchemy.Integer),
    sqlalchemy.Column("goal", sqlalchemy.Integer),
    sqlalchemy.Column("partnergoal", sqlalchemy.Integer),
    sqlalchemy.Column("nummessages", sqlalchemy.Integer),
    sqlalchemy.Column("negotiationlength", sqlalchemy.Integer),
    sqlalchemy.Column("avgmessagelength", sqlalchemy.Float),
    sqlalchemy.Column("offer", sqlalchemy.Integer),
    sqlalchemy.Column("offeraccepted", sqlalchemy.Boolean),
    sqlalchemy.Column("score", sqlalchemy.Float),
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
    nonmturkid: int
    mturkid: str
    partnermturkid: str
    conversationid: int
    role: int
    itemid: int
    listingprice: int
    goal: int
    partnergoal: int
    nummessages: int
    negotiationlength: int
    avgmessagelength: float
    offer: int
    offeraccepted: bool
    score: float
    convactive: bool
    convdisconnected: bool


# Task Descriptions to use when creating task page (possibly deprecated? Check in the webpage)
TASK_DESCRIPTIONS = ["Your goal for this task is to sell this item for as close to the listing price as possible. You will negotiate with your assigned buyer using recorded messages. Once the buyer chooses to make an offer, you may either accept or reject the offer.\nTo record a message, press and hold the button with the microphone symbol. You can listen to the message to make sure it sounds right, then click the “send” button to send it. You can also click any sent or received message to listen to them again.Each negotiation should be finished within 5 minutes. There is a timer at the top of the screen which tells you how much time has elapsed.\nFor more detailed instructions, click the \"Negotiation Instructions\" link at the top of the screen.\nHave fun, and good luck with your negotiation!",
                     "Your goal for this task is to convince the seller to sell you the item for as close to your goal price as possible. You will negotiate with the seller using recorded messages. At any point, you may make an offer of any price; however, once the seller accepts or rejects your offer, the negotiation is over. \nTo record a message, press and hold the button with the microphone symbol. You can listen to the message to make sure it sounds right, then click the 'send' button to send it. You can also click any sent or received message to listen to them again. \nHave fun, and good luck with your negotiation!"]

# Items for use in craigslist negotiations
with open('static/filtered_train.json') as item_file:
    items = json.load(item_file)


# Getting the server started
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
    global next_unique_id 
    next_unique_id = await get_next_unique_id()
    checker.set_pairing_count(num_prev_pairings)
    
# Closing the server when it needs to shut down
@app.on_event("shutdown")
async def shutdown_event():
    await database.disconnect()

# If there's an error, call this function 
# to print to the error logging file and redirect the user accordingly
async def error_handling(function_name: str, error, uid, assignmentId):
    if assignmentId:
        if uid:
            printer.print_error(function_name, repr(error), uid, assignmentId)
        else:
            printer.print_error(function_name, repr(error), assignmentId)
    else:
        if uid:
            printer.print_error( function_name, repr(error), uid)
        else:
            printer.print_error( function_name, repr(error))

    record_url = '/error/5'
    response = RedirectResponse(url=record_url)
    return response

# Show the homepage (with the task description) to the user
@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
async def home(request: Request, response: Response, assignmentId: str="None", hitId: str="None", turkSubmitTo: str="None", workerId: str="None"):
    function_name = "Home"
    try:
        printer.print(function_name, "Accessed Homepage", mturk_id=workerId)
        uid = request.cookies.get('id')
        checked_in = request.cookies.get('checkedin')
        show_consent_form = False if checked_in == "True" else True
        response.set_cookie(key='checkedin', value=True, secure=True, samesite='none')
        
        response.set_cookie(key='mturkId', value=workerId, secure=True, samesite='none')
        response.set_cookie(key='assignmentId', value=assignmentId, secure=True, samesite='none')
        response.set_cookie(key='hitId', value=hitId, secure=True, samesite='none')
        response.set_cookie(key='turkSubmitTo', value=turkSubmitTo, secure=True, samesite='none')
            
        if uid:
            # They should not have a uid when accessing the homepage
            response.delete_cookie('id')

        if assignmentId == "ASSIGNMENT_ID_NOT_AVAILABLE":
            # This is a mechanical turk user, but they are viewing a preview and haven't accepted the task.
            template = env.get_template("home2.html")
            return template.render(title="Home")
        elif assignmentId == "None":
            # This is not an mturk user
            template = env.get_template("home3.html")
            return template.render(title="Home", show=show_consent_form)
        else:
            # This is an mturk user
            template = env.get_template("home.html")
            return template.render(title="Home")
    except Exception as error: 
        return await error_handling(function_name, error, uid, assignmentId)

# Send the user a page with a button to put them in the pairing system, when they're ready
# If they are currently paired with another user, skip this page and send them to the negotiation instead
@app.get('/pair', response_class=HTMLResponse)
async def pair(request: Request, response: Response):
    function_name = "pair"
    printer.print(function_name, "Accessed Pairing Page")
    try:
        assignmentId = request.cookies.get('assignmentId')
        hitId = request.cookies.get('hitId')
        turkSubmitTo = request.cookies.get('turkSubmitTo')
        mturkId = request.cookies.get('mturkId')
        
        uid = request.cookies.get('id')
        if uid:
            # The user should not be reaching this page with an active uid.
            response.delete_cookie('id')

        if assignmentId != "None":
            # This is an mturk user
            printer.print(function_name, "This is an mturk user", mturk_id=assignmentId)
            uid = await check_if_mturk_active(mturkId)
            printer.print(function_name, "looked for an ID", uid=uid, mturk_id=assignmentId)
            if not uid:
                printer.print(function_name, "No ID found", mturk_id=assignmentId)

                # This user does not have an active conversation. Let's give them a new user ID.
                database_lock.acquire()
                query = users.insert().values(role=-1, partnerid=-1, nonmturkid=-1, mturkid=mturkId, partnermturkid="Invalid", conversationid=-1,
                                                itemid=-1, listingprice=-1, goal=-1, partnergoal=-1, nummessages=0, negotiationlength=0,
                                                avgmessagelength=-1, offer=-1, offeraccepted=False, score=0, convactive=False, 
                                                convdisconnected=True)
                last_record_id = await database.execute(query)
                printer.print(function_name, "Added user to database", mturk_id=assignmentId)
                database_lock.release()

                uid = last_record_id
                response.set_cookie(key='id', value=uid, secure=True, samesite='none')
                checker.initialize_user(uid)
                int_uid = uid
            else:
                printer.print(function_name, "Previous ID found", uid=uid, mturk_id=assignmentId)

                # This is an mturk user who is already in a conversation. We shouldn't send them to the pairing page.
                response.set_cookie(key='id', value=uid, secure=True, samesite='none')
                # Redirect to skip pairing and pair with the old partner
                record_url = '/record'
                response = RedirectResponse(url=record_url)
                return response
        else:
            # This is not an mturk user.
            to_print = "not an Mturk user"
            printer.print(function_name, to_print)
            unique_id = request.cookies.get('uniqueid')
            if not unique_id:
                printer.print(function_name, "Creating unique id for non-mturk user")
                global next_unique_id
                unique_id = next_unique_id
                next_unique_id += 1
                response.set_cookie(key='uniqueid', value=unique_id, secure=True, samesite='none')
            else:
                unique_id = int(unique_id)
            printer.print(function_name, "Creating database element")
            database_lock.acquire()
            query = users.insert().values(role=-1, partnerid=-1, nonmturkid=unique_id, mturkid="Invalid", partnermturkid="Invalid", conversationid=-1,
                                            itemid=-1, listingprice=-1, goal=-1, partnergoal=-1, nummessages=0, negotiationlength=0,
                                            avgmessagelength=-1, offer=-1, offeraccepted=False, score=0, convactive=False, 
                                            convdisconnected=True)
            last_record_id = await database.execute(query)
            database_lock.release()
            uid = last_record_id
            printer.print(function_name, "Created database element", uid)
            response.set_cookie(key='id', value=uid, secure=True, samesite='none')
            checker.initialize_user(uid)
            int_uid = int(uid)

        username = "User " + str(uid)
        template = env.get_template("pairing.html")
        return template.render(title="Please Wait...", username=username, id=int_uid)
    except Exception as error: 
        return await error_handling(function_name, error, uid, assignmentId)

async def check_if_mturk_active(mturkid: str):
    # Check if the user is in the database with the given mturk id and convactive=True
    # If both of these are true, check the disconnect checker to see if they should have disconnected
    # If the result is PingErrors.NORMAL, return the id
    try:
        ua = users.alias("alias")
        query = sqlalchemy.select([ua.c.id]).where(ua.c.mturkid==mturkid).where(ua.c.convactive==True)
        uid = await database.fetch_all(query)
        printer.print("Check if mturk active", message="Fetched uids for current mturk user", mturk_id=mturkid)
        if uid:
            for id in uid:
                id = int(id[0])
                if checker.user_is_active(id):
                    pid = checker.get_user_partner(id)
                    if pid != -1:
                        printer.print("Check if mturk active", message="Found currently active mturk user", mturk_id=mturkid)
                        return id
                else:
                    # This user needs to have their database updated to show they aren't active
                    printer.print("Check if mturk active", message="Found inactive mturk user", mturk_id=mturkid)
                    await remove_user(id, False)
        return None
    except Exception as error:
        printer.print_error( "check_if_mturk_active", repr(error), mturk_id=mturkid)
        raise
    
# If no partner is found within a certain amount of time, users are redirected to this page
@app.get('/no_partner', response_class=HTMLResponse)
async def no_partner_found(request: Request, response: Response):
    try:
        function_name = "no_partner_found"
        printer.print(function_name, "No Partner Found")
        assignmentId = request.cookies.get('assignmentId')
        uid = request.cookies.get('id')
        if uid:    
            response.delete_cookie('id')
            int_uid = int(uid)
            await remove_user(int_uid, False)
            printer.print_user_friendly("User " + str(uid) + " could not find a partner.")

        username = "User " + str(uid)
        template = env.get_template("unpaired.html")
        return template.render(title="Sorry!", content="Thank you for your patience, " + username + ". Unfortunately, we couldn't find a partner for you. Please try again later.")
    except Exception as error:
        return await error_handling(function_name, error, uid, assignmentId)
    
# Users are sent here if they successfully complete the task.
@app.get('/finish', response_class=HTMLResponse)
async def self_reset(request: Request, response: Response):
    function_name = "Finish"
    try:
        uid = request.cookies.get('id')
        assignmentId = request.cookies.get('assignmentId')
        hitId = request.cookies.get('hitId')
        turkSubmitTo = request.cookies.get('turkSubmitTo')

        if uid:
            printer.print(function_name, "Entering the finish function", uid=int(uid), mturk_id=assignmentId)   
            response.delete_cookie('id')
        else:
            # This should not happen
            printer.print(function_name, "Reached the end without a user ID")
            record_url = '/error/5'
            response = RedirectResponse(url=record_url)
            return response
        int_uid = int(uid)

        # Initialize all variables to show the bonus for a non-mturk user
        bonus_percentage = await calc_bonus(int_uid)
        printer.print(function_name, "Bonus = " + str(bonus_percentage), uid=uid, mturk_id=assignmentId)
        bonus_string = f'{bonus_percentage:.2f}'
        partner_bonus = 3 - bonus_percentage if bonus_percentage > 0 else 0
        partner_bonus_string = f'{partner_bonus:.2f}'

        text = "Thanks for your participation! Your score was " + str(int(bonus_percentage * 100))  + "."
        text += " Your partner's score was " + str(int(partner_bonus * 100)) + "."
        text += " If you would like to participate again, please click the button below to return to the task start page."

        printer.print_user_friendly("User " + str(uid) + " completed the assignment! They earned a bonus of $" + str(bonus_percentage) + ".")

        if assignmentId != "None":
            # This is an mturk user, so adjust the variables to account for the fact that they're getting money.
            printer.print(function_name, "Creating page for mturk user", uid=int(uid), mturk_id=assignmentId)  
            response.delete_cookie('assignmentId')
            response.delete_cookie('hitId')
            response.delete_cookie('turkSubmitTo')

            url = turkSubmitTo
            url += "/mturk/externalSubmit?assignmentId="
            url += assignmentId
            url += "&bonus="
            url += str(bonus_percentage)

            text = "Thanks for your participation! Your bonus was $" + bonus_string + "."
            text += " Your partner's score was " + partner_bonus_string + "."
            text += " To submit your results to mechanical turk, click the button below."
            
            await remove_user(int_uid, True)
            printer.print(function_name, "Putting together the mturk task completion page", uid=uid, mturk_id=assignmentId)
            template = env.get_template("mturk_submit.html")
            return template.render(title="Thank You!", content=text, url=url)
        await remove_user(int_uid, True)
        template = env.get_template("restart.html")
        return template.render(title="Thank You!", 
                                content=text)
    except Exception as error: 
        return await error_handling(function_name, error, uid, assignmentId)    
    
# Helper function to convert a non-monetary value to a dollar value
# Decimal value, make it two digits after the decimal point
def val_to_dollar_str(val):
    try:
        val *= 1.0
        result = str(val)
        if val % 10 == 0:
            result += "0"

        return result
    except Exception as error:
        printer.print_error( "val_to_dollar_str", repr(error))
        raise
    
# Calculate the bonus based on the goal price for both users, and the actual value agreed upon
# This function rounds to the nearest hundredth, saves the value to the database, etc.
async def calc_bonus(int_uid: int):
    try:
        query = users.select().where(users.c.id==int_uid)
        user = await database.fetch_all(query)
        user = user[0]

        query = users.select().where(users.c.id==int(user.partnerid))
        partner = await database.fetch_all(query)
        partner = partner[0]

        offer_accepted = user.offeraccepted
        bonus_percentage = 0
        if offer_accepted:
            bonus_percentage = 1
            goal = int(user.goal)
            partner_goal = int(partner.goal)
            offer = int(user.offer)
            if partner_goal < goal:
                # The user is the seller, so they had the larger goal. get_bonus returns their bonus.
                bonus_percentage += await get_bonus(partner_goal, offer, goal)
            else:
                # The user was the buyer, so get_bonus returns the inverse of their bonus.
                bonus_percentage += 1 - await get_bonus(goal, offer, partner_goal)

        # Round to the nearest 100th
        bonus_percentage = math.floor(bonus_percentage * 100)
        bonus_percentage /= 100

        database_lock.acquire()
        
        query = sqlalchemy.update(users)
        query = query.where(users.c.id == int_uid)
        query = query.values({"score": bonus_percentage})
        await database.execute(query)

        database_lock.release()

        return bonus_percentage
    except Exception as error:
        printer.print_error( "calc_bonus", repr(error), uid=str(int_uid))
        raise
    
# Helper function to actually calculate the bonus
async def get_bonus(smaller_goal, offer, larger_goal):
    try:
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
    except Exception as error:
        printer.print_error( "get_bonus", repr(error))
        raise


# @app.get('/resetusers', response_class=HTMLResponse)
# async def reset_users():
#     try:
#         query = users.delete()
#         await database.execute(query)
#         template = env.get_template("default.html")
#         return template.render(title="Database Cleared", 
#                                 content="The database is empty now.")
#     except Exception as error: 
#         return await error_handling(function_name, error, uid, assignmentId)
    
# Once a user is in a conversation, this function stores all that information to the database
async def add_user_conv_info(uid: int, pid: int, conv_id: int, role: int, item_id: int, item_price: int, goal: int):
    # Save all this information into the database
    try:
        database_lock.acquire()
        
        ua = users.alias("alias")
        query = sqlalchemy.select([ua.c.mturkid]).where(ua.c.id==pid)
        partner_mturk_id = await database.fetch_all(query)
        partner_mturk_id = partner_mturk_id[0][0]

        query = sqlalchemy.update(users)
        query = query.where(users.c.id == uid)
        query = query.values({"role": role, "partnerid": pid, "partnermturkid": partner_mturk_id, "conversationid": conv_id, "itemid": item_id, "listingprice": item_price, "goal": goal, "convactive": True})
        await database.execute(query)

        database_lock.release()
    except Exception as error:
        printer.print_error( "add_user_conv_info", repr(error))
        raise

# Get the largest conversation ID currently in the database, to determine what IDs to give new conversations
async def get_max_conv_id():
    try:
        query = users.select()
        user_list = await database.fetch_all(query)
        # Get all users by conversation id
        convIDs = [user.conversationid for user in user_list]

        maxID = 0
        for convID in convIDs:
            convID = int(convID)
            if maxID < convID:
                maxID = convID
        
        return maxID
    except Exception as error:
        printer.print_error( "get_max_conv_id", repr(error))
        raise

# Get the largest ID to determine what the next ID to assign to a user should be
async def get_next_unique_id():
    try:
        # Get the conversation id from the database with the highest value
        query = users.select()
        user_list = await database.fetch_all(query)
        # Get all users by conversation id
        ids = [user.nonmturkid for user in user_list]

        maxID = 0
        for id in ids:
            id = int(id)
            if maxID < id:
                maxID = id
        
        return maxID
    except Exception as error:
        printer.print_error( "get_next_unique_id", repr(error))
        raise

# Creates a webpage where users can record and send messages to a partner (the negotiation page)
@app.get('/record', response_class=HTMLResponse)
async def record(request: Request):
    try:
        function_name = "Record"
        uid = request.cookies.get('id')
        assignmentId = request.cookies.get('assignmentId')
        int_uid = int(uid)
        keepalive = checker.ping_user(int_uid)


        if keepalive == PingErrors.NORMAL:
            printer.print(function_name, "Situation Normal", uid=uid, mturk_id=assignmentId)
            role_txt = checker.get_user_role(int_uid)
            conv_id = checker.get_user_conv_id(int_uid)
            partner_id = checker.get_user_partner(int_uid)

            is_buyer = (role_txt == "Buyer")

            # Get item
            printer.print(function_name, "Getting item", uid=uid, mturk_id=assignmentId)
            item_id, buyer_coef, seller_coef = checker.get_item_info(int_uid)

            item_data = items[item_id]

            listing_price = item_data['Price'] * 2

            # Get price coefficient
            printer.print(function_name, "Calculating Item Coefficient", uid=uid, mturk_id=assignmentId)
            if is_buyer:
                price_coefficient = buyer_coef
            else:
                price_coefficient = seller_coef

            item_price = listing_price * price_coefficient
            item_price = round(item_price)

            printer.print(function_name, "adding info to the database", uid=uid, mturk_id=assignmentId)
            await add_user_conv_info(int_uid, partner_id, conv_id, is_buyer, item_id, listing_price, item_price)

            item_description = ""
            for line in item_data['Description']:
                item_description += line + "\n"

            image = None 
            if len(item_data['Images']):
                image = "/static/images/" + item_data['Images'][0]
            else:
                image = None
            if (is_buyer):
                template = env.get_template("audioinput_buyer.html")
            else:
                template = env.get_template("audioinput_seller.html")
            
            printer.print(function_name, "Connection page ready and sending", uid)
            return template.render(title="Record Audio", role=role_txt, task_description=TASK_DESCRIPTIONS[is_buyer], goal_price=item_price, listing_price=listing_price,
            item_description=item_description, item_image=image, id=int_uid, conv_id=checker.get_user_conv_id(int_uid))
        else:
            # Redirect to handle a failed user
            printer.print(function_name, "Keepalive error", uid=uid)
            int_error = keepalive.value
            error_url = '/error/' + str(int_error)
            response = RedirectResponse(url=error_url)
            return response
    except Exception as error: 
         return await error_handling(function_name, error, uid, assignmentId)

# Create an error page to handle server errors and disconnects
@app.get('/error/{status}', response_class=HTMLResponse)
async def handle_ping_errors(status: PingErrors, request: Request, response: Response):
    uid = request.cookies.get('id')

    function_name = "Error"
    printer.print(function_name, "Encountered error with code " + str(status), uid=uid)

    if status == PingErrors.USER_DISCONNECT:
        printer.print_user_friendly("User " + str(uid) + " disconnected, and was unable to complete the task.")
    elif status == PingErrors.PARTNER_DISCONNECT:
        printer.print_user_friendly("User " + str(uid) + "'s partner disconnected, so they were unable to complete the task.")
    elif status == PingErrors.OTHER:
        printer.print_user_friendly("User " + str(uid) + "encountered an error in the software; looks like there's a bug that needs to be fixed.")
    else:
        printer.print_user_friendly("User " + str(uid) + "encountered an unexpected error.")

    if uid:    
        response.delete_cookie('id')
        int_uid = int(uid)
        await remove_user(int_uid, False)
    else:
        printer.print(function_name, "Encountered an error before pairing")

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
            await remove_user(int_uid, True)
            return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. You will still be paid, but please try again later.", url=url)
        else:
            text = "It seems there was an error. " 
            text += "Though there is no payment for incomplete tasks, we will provide a bonus for detailed information regarding the error you encountered. "
            text += "To receive the bonus, please fill in the following form to the best of your ability, then click submit on this page.\n"
            text += "https://forms.gle/HD2QQNUvEasjz5zX6"
        
            url = turkSubmitTo
            url += "/mturk/externalSubmit?assignmentId="
            url += assignmentId
            url += "&bonus=-1"
            
            await remove_user(int_uid, True)
            printer.print(function_name, "Putting together the mturk task error page", uid=uid, mturk_id=assignmentId)
            template = env.get_template("mturk_submit.html")
            return template.render(title="Something went wrong.", content=text, url=url)


    if (status == PingErrors.USER_DISCONNECT):
        return template.render(title="Timed Out", content="Sorry, it seems you timed out. Please try again later.")
    elif (status == PingErrors.PARTNER_DISCONNECT_UNPAID):
        return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. Please try again later.")
    elif (status == PingErrors.PARTNER_DISCONNECT):
        return template.render(title="Partner Disconnected", content="Sorry, it seems your partner disconnected. Please try again later.")
    else:
        printer.print_error( function_name, "There is an unexpected ping error")
        return template.render(title="Record Audio", content="Sorry, it seems something unexpected happened. Please try again later.")

manager = ConnectionManager()

# Create a websocket connection to handle messages sent between users
@app.websocket("/audiowspaired/{uid}")
async def chat_ws_endpoint(websocket: WebSocket, uid:int):
    try:
        function_name = "chat_websocket"
        printer.print(function_name, "Websocket connected for chat page", uid)
        total_audio_length = 0
        num_messages = 0
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
            printer.print(function_name, "WARNING: No Partner Assigned.", uid=uid)

        # Don't start until both users have joined the conversation
        # If the partner hasn't activated their websocket within 10 seconds, go back to the pairing
        start_time = int(time.time())
        while not manager.partner_connected(int_pid) and (start_time + checker.conv_start_timeout) > int(time.time()):
            # The other user hasn't connected yet, but they still haven't timed out
            # Note that this timeout is usually shorter than the usual timeout
            await asyncio.sleep(2)

        if not manager.partner_connected(int_pid):
            printer.print(function_name, "Partner did not connect in time.", uid)
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

                if self_is_sender:
                    num_messages += 1
                
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
                        printer.print(function_name, "Identifier = " + str(identifier), uid)
                        
                        if(identifier == 6):
                            # This is a voice message.

                            timestamp = datetime.datetime.now()
                            # These recordings aren't actually stored as mp3s, but keeping a consistent file ending prevents errors
                            # If someone wants to use the raw files in the future, just programmatically change all the file endings
                            temp = "recordings/" + role_txt + "_" + str(int_uid) + "_" + str(timestamp) + ".mp3"
                            file_name = ""
                            for c in temp:
                                if c == ' ':
                                    file_name += "_"
                                elif c == ':':
                                    file_name += "-"
                                else:
                                    file_name += c


                            printer.print(function_name, file_name, uid=uid)
                            with open(file_name, "wb") as file1:
                                file1.write(remaining_data)
                                file1.close()
                            
                            audio = AudioSegment.from_file(file_name)
                            length_in_sec = audio.duration_seconds
                            total_audio_length += length_in_sec
                            num_messages += 1

                            audio = audio.set_frame_rate(16000)
                            audio = audio.set_channels(1)
                            audio = audio.set_sample_width(2)

                            
                            temp = "recordings/" + role_txt + "_" + str(int_uid) + "_" + str(timestamp) + ".mp3"
                            file_name = ""
                            for c in temp:
                                if c == ' ':
                                    file_name += "_"
                                elif c == ':':
                                    file_name += "-"
                                else:
                                    file_name += c
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
                            bytestring = remaining_data.decode("utf-8")
                            val = int(bytestring)

                            checker.conv_set_offer(int_uid, val)

                            avg_message_length = total_audio_length / num_messages

                            database_lock.acquire()

                            query = sqlalchemy.update(users)
                            query = query.where(users.c.id == int_uid)
                            query = query.values({"offer": val, "nummessages": num_messages, "avgmessagelength": avg_message_length})
                            await database.execute(query)

                            query = sqlalchemy.update(users)
                            query = query.where(users.c.id == int_pid)
                            query = query.values({"offer": val})
                            await database.execute(query)

                            database_lock.release()

                            await manager.send_partner_message(data, int_pid)
                        elif (identifier == 52):
                            # An offer was either accepted or declined.
                            bytestring = remaining_data.decode("utf-8")
                            val = int(bytestring)
                            response = bool(val)

                            checker.conv_set_offer_accepted(int_uid, response)

                            avg_message_length = total_audio_length / num_messages
                            
                            database_lock.acquire()

                            query = sqlalchemy.update(users)
                            query = query.where(users.c.id == int_uid)
                            query = query.values({"offeraccepted": response, "convdisconnected":False, "nummessages": num_messages, "negotiationlength": conv.get_length(), "avgmessagelength": avg_message_length})
                            await database.execute(query)

                            query = sqlalchemy.update(users)
                            query = query.where(users.c.id == int_pid)
                            query = query.values({"offeraccepted": response, "convdisconnected":False, "negotiationlength": conv.get_length()})
                            await database.execute(query)

                            database_lock.release()
                            checker.conv_print(int_uid, printer)
                            # checker.safe_delete_user(int_uid) # Could remove user here, but safer to do it in finish page
                            await manager.send_partner_message(data, int_pid)
                        elif (identifier == 0):
                            printer.print(function_name, "Unexpected behavior!", uid=uid)
                        elif (identifier == 1):
                            # printer.print("Received a ping")
                            identifier = identifier # Basically a no-op, but using NOP requires importing classes
                        elif (identifier == 9 or identifier == 10):
                            # These are "partner is recording" messages
                            # Just forward them, no need to save them
                            await manager.send_partner_message(data, int_pid)

                        else :
                            printer.print(function_name, "Unexpected identifier", uid=uid)
                            await manager.send_partner_message(data, int_pid)
                    else:
                        await manager.send_self_message(keepalive.to_bytes(1, 'big'), int_uid)

            except WebSocketDisconnect:
                printer.print("audiowspaired", "The user disconnected the websocket connection.", uid)
                manager.disconnect(int_uid)
    except Exception as error:
        printer.print_error( "audiowspaired", repr(error))
        
# Create a websocket connection to keep users updated on the search for a conversation partner
@app.websocket("/pairingws/{uid}")
async def pairing_ws(websocket: WebSocket, uid:int):
    function_name = "Pairing Websocket"
    printer.print(function_name, "Starting Pairing Websocket", uid=uid)
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
            printer.print(function_name, "Pairing Timed Out", uid=uid)
            val_to_send = 0 # Essentially a value of "false"
        else:
            printer.print(function_name, "Pairing Successful!", uid=uid)
            val_to_send = 1 # bool val = True

        await websocket.send_bytes(val_to_send.to_bytes(1, 'big'))

    except WebSocketDisconnect:
        printer.print(function_name, "The user disconnected the websocket connection", uid)
        # The user disconnected.
        # We could remove the user, but if they come back from a refresh we don't want them to be deleted.
        # checker.unsafe_delete_user(int_uid)
    except Exception as error:
        printer.print_error( function_name, repr(error), uid)

# Create a new user object for someone freshly connecting to the site
async def new_user_info():
    try:
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
    except Exception as error:
        printer.print_error( "new_user_info", repr(error))
        raise

# Remove a user who has completed a conversation or disconnected
# This ensures they won't get paired with anyone else once they leave
async def remove_user(uid: int, success=False):
    try:
        printer.print("Remove User", "Removing user, success = " + str(success), uid=uid)
        # Find their entry in the database and ensure "convactive" is set to false
        database_lock.acquire()
        query = sqlalchemy.update(users)
        query = query.where(users.c.id == uid)
        query = query.values({"convactive": False})
        await database.execute(query)
        database_lock.release()
        
        # If they haven't already been removed from the checker, do so now
        if checker.user_is_active(uid):
            checker.safe_delete_user(uid, success)
    except Exception as error:
        printer.print_error( "remove_user", repr(error))
        raise

# Pair users, and return whether the pairing process was successful
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

# Add something when the user tries to connect, and is waiting on a partner to connect. Maybe a scrolling wheel?