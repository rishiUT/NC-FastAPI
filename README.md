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

### Conversations folder

Each time two users connect to the server and participate in a dialogue, a brief record of their conversation will be stored in a file in this folder. The file will contain their IDs, the save locations of the messages they sent, and whether it resulted in a successful offer.

### Recordings and Downgraded Recordings

When users send messages, the raw audio of each message is saved in the recordings folder. The audio is then converted into the .mp3 format and saved in the Downgraded Recordings folder.

### Logs and Timelines

As long as the server is active, it will log status and error messages to a log file, which is stored in the Logs folder. It will also store a more human-readable timeline of events in the Timelines folder; this is useful for checking if users have been connecting with each other and completing dialogues, and for identifying when errors have occurred.

### Mturk Scripts

This folder contains scripts and files necessary for Amazon Mechanical Turk integration. There are more details below.

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