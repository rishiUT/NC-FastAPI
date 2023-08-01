# The Dialogue Audio Recording Environment (DARE)
## Project Overview
## Hardware and Software Requirements
### Linux Machine

This project was developed on an Ubuntu machine. To use many of the commands and tutorials in this guide, you will also need access to a linux machine; most coding resources online assume you are using a linux machine and provide linux terminal commands. If you use non-linux hardware, this project may not run as expected.

You can download Ubuntu [here](https://ubuntu.com/download).

## Software Requirements
### Python and Anaconda

Many of the libraries used in this project require Python. Use the latest version of Python 3 – Python 2 is not compatible. Additionally, installing Anaconda allows for the creation of virtual environments, which is helpful for preventing installation conflicts for multiple python projects; this project also comes with a YAML file that allows Anaconda to easily install all required packages with a single command. (Details to follow in the “Installation” section.)

You can download the latest installation of python [here](https://www.python.org/downloads/), and the latest version of Anaconda [here](https://www.anaconda.com/download/).

### PostgreSQL

This project requires the use of a postgresql database to store user information. To have access to the data obtained, you will need to create an account to manage the databases. The process to install postgresql and create an account and database are detailed [here](https://www.postgresql.org/docs/current/installation.html)

### Amazon Web Services

This project can be used alongside Amazon Mechanical Turk for crowdsourcing purposes. To use Mechanical Turk, you will require an account with Amazon Web Services. Details on the process to create accounts and link them with Mechanical Turk can be found [here](https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMechanicalTurkGettingStartedGuide/SetUp.html).

For more information on setting up credentials on your machine (which is helpful when using the Amazon Mechanical Turk API), read [this page](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).

### Nginx and Systemd

You can use Nginx to load-balance a server hosted on your linux machine. A beginner's guide to Nginx can be found [here](https://nginx.org/en/docs/beginners_guide.html). 

To set up the server for viewing by the public, make sure you've performed all the necessary setup for an nginx server, then create a [systemd service](https://linuxhandbook.com/create-systemd-services/) on the linux machine. Services are background processes that are constantly running; if you create a service that constantly hosts your server and listens to a specific port, this instance of the server will be constantly available for public use. The negotiation-chat.service file in this repository is an example of a service file which can be used to control such a service.

## Setting Up

The first step is to download the project repository from GitHub. When you do so, make sure you download the project into a folder you have edit permissions for, as the system will need to be able to write new files into the folder using your user’s permissions.

Open a terminal with the project folder as the current working directory. Use the command `conda env create -f environment.yml` to create an anaconda virtual environment with all the libraries necessary to run this project.

The installation instructions for postgresql should contain information on creating an account and a database. To use the database in this project, go to the “main.py” file in the github repository and change the DATABASE_URL variable to have the following format: `postgresql://username:password@localHost:5432/database_name`. 

I’ve personally found that using short database names makes it easy to create new databases when you want to collect fresh data, for example after making edits to the server code.

Installing FFMpeg is very straightforward on Ubuntu; you can simply run `sudo apt install ffmpeg`.

## Repository Overview

This repository contains several code files and subfolders. Some of the most commonly used files and folders include:

### "Conversations" folder

Each time two users connect to the server and participate in a dialogue, a brief record of their conversation will be stored in a file in this folder. The file will contain their IDs, the save locations of the messages they sent, and whether it resulted in a successful offer. The code that creates the records can be found in the print function in conversation.py. This code can be edited to print additional information to the record, or to change the structure.

### "Recordings" and "Downgraded Recordings"

When users send messages, the raw audio of each message is saved in the recordings folder. The audio is then converted into the .mp3 format and saved in the Downgraded Recordings folder.

### "Logs" and "Timelines"

As long as the server is active, it will log status and error messages to a log file, which is stored in the Logs folder. This file will contain any print statement encountered during the runtime of the code, in addition to any error message that would ordinarily be printed to console; you can add more print statements using the print and print_error functions in debughelper.py (if printing in main.py, use the printer object, which is imported from debughelper.py). Note that these functions also require the name of the function the print function was called from, and the user ID of the user the server is serving. As a result, each line in the log file will contain the caller function and the user ID, which can be used to debug specific issues.

The server will also store a more human-readable timeline of events in the Timelines folder; this is useful for checking if users have been connecting with each other and completing dialogues, and for identifying when errors have occurred. To add more prints to the timeline, use the print_user_friendly function in debughelper.py and the printer object.

### Mturk Scripts

This folder contains scripts and files necessary for Amazon Mechanical Turk integration. (See [Amazon Mechanical Turk Integration](#amazon-mechanical-turk-integration))

### Templates and Static

The templates folder contains HTML template files used to create the HTML pages sent to users of the system. The Static folder contains Javascript files used to control webpages, as well as other static files users may require (such as images).

### Main.py

This contains the bulk of the code used in running the server, including all HTML page creation. When controlling what a user sees when they access a specific page on the website, this is the file to edit.

### Disconnect.py and the disconnect_checker folder

These files contain much of the logic for storing user information and identifying when a user has disconnected. When editing what is stored about users, conversations, and negotiations, these are the files to check.

### DebugHelper.py

This file contains printing logic for logging and timeline maintenance.

### ConnectionManager.py

This file contains the code for the websocket connection manager, which is used for websocket connections involving communications between two users (i.e. dialogues).

## Design

For more information on the design choices involved in the creation of DARE, see the "Design Thesis.pdf" document included in the repository. This thesis explains the design choices made and provides information on the tools and technologies used.

## Amazon Mechanical Turk Integration

This repository can be used with Amazon Mechanical Turk for crowdsourcing spoken dialogue data. To quickly create, remove, and approve mturk tasks, you can use the python scripts in the mturk_scripts folder.

To create tasks, you can run CreateHitNC.py. By default, this releases tasks on the mechanical turk sandbox, which is useful for testing purposes; to create official tasks to be completed by turkers, you should open the python file and set the "create_hits_in_live" variable to "True". Additionally, you can change the number of HITs released by changing the value of the "max_respondents" variable.

Once you have released HITs, the unique IDs assigned to each active HIT is stored in a .txt file in the mturk_scripts folder. If the tasks were released in the sandbox, they will be in the active_hits_sandbox.txt file, and otherwise they will be in the active_hits_live.txt file. Do not edit these IDs until you have either approved or rejected any submissions for each HIT.

To check the status of HITs in the active_hits files, you can run RetrieveAndApproveHitSample.py. This will print the status of each HIT, and data about each HIT submission, to the console. Additionally, you can comment in code blocks to immediately expire all active hits, approve all submitted hits, or both. 

## Debugging Tips

When debugging the server, it's better to run FastAPI test servers using uvicorn than to constantly reload the hosted server on nginx. To run a test server from the command line, navigate to the "backend" folder, then run the command `uvicorn main:app --port <port number>`. This creates a server you can access locally through the browser of your linux machine.

If you would like to run a test negotiation on the test server and are having difficulty partnering with yourself, you can either open a different browser or open a new inprivate tab in the same browser. This allows you to run multiple instances of the site with separate cookie caches, which allows you to emulate multiple users. 

I typically emulate a full negotiation with up to four users whenever I make changes, to ensure there are no connection issues or issues with the pairing system. This includes having all four users pair up, sending four messages per negotiation, sending an offer with each negotiation, and accepting one offer while declining the other. Once each user has made it to the "Negotiation completed" page, I consider the test a success.

Once you've tested the server locally, you can test it on the nginx server by refreshing the server. You can use the command `sudo systemctl restart nginx.service` to do so.

Note that, if you've changed the types of data stored in the database, or have added new variables for the database, you will need to create a new database using postgresql. You may also want to create a new database if you are collecting user data through crowdsourcing, to make it easier to avoid mixing data from different data collection events. 

## Next Steps

User testing has shown some issues with the negotiation task. These issues, and potential solutions to them, are as follows:

### Preliminary Task

Mechanical Turk users do not appear to know how to use the negotiation interface, possibly because they have not read the instructions. A solution to that could be to create a preliminary task to test them on the interface before they are allowed to take the task that pairs them with another user.

This preliminary task can be made by making a new page for the website that is almost the same as the negotiation page. However, it would be built as a tutorial; the description would tell the user how to send an audio message, and when a message is sent, it will send a recording to the user for them to practice listening to. Other tutorial tasks can be added to ensure the user knows how to follow instructions; for example, at some point the user could be required to send an offer for a certain amount, or told to accept or decline an incoming offer, etc.

The code that would need to be copied to make the negotiation interface (and edited, to work as a tutorial) would be audioscript.js and the chat_ws_endpoint function in main.py.

### Tutorial

Since users don't appear to know how to use the interface, it may be helpful to add pop-up messages to work as a tutorial. These can highlight a button while informing the user how to use them (for example, telling the user to click and hold the record button to record messages).

### Bugs

When users send audio, the recording element still contains the last audio sent. Users will need to re-record to send another audio clip, but it breaks immersion to have the audio clip in the recording element. This can be removed programmatically in the audioscript.js file, in the part of the file dedicated to sending messages.

Users are currently able to send offers with negative values, as long as those offers are whole numbers. The value-checking function in audioscript.js should be edited to prevent that from occurring. 

When a user records and sends a message that is a fraction of a second long, this can occasionally fail to register as an actual message on the receiver's end, but prevent the sender from sending another message. This is currently solvable by having the sender refresh their page. It's unclear how to fix this, but since it only occurs when a user is attempting to game the system, it may be worth leaving as-is to discourage such behavior.

