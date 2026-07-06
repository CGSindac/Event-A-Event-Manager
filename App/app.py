from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from App.helpers import *

import re


# Main Flow
app = Flask(__name__)

# Configure Session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = 'filesystem'
Session(app)

@app.route('/')
def index():
    # DISPLAY ONGOING EVENTS
    if not session.get('user_id'):
        return redirect('/login')

    joined_events = getUserJoinedEvents(session["user_id"])
    created_events = getUserCreatedEvents(session["user_id"])

   

    return render_template('index.html', joined_events=joined_events, created_events=created_events)

@app.route('/find')
def find():
    if not session.get('user_id'):
        return redirect('/login')

    free_events = getUserNotJoinedEvents(session["user_id"])

    return render_template('find.html', events=free_events)
@app.route('/create', methods=["GET", "POST"])
def createEvent():
    if not session.get('user_id'):
        return redirect('/login')
    
    errors = {
        "name" : False,
        "desc" : False,
        "capacity" : False,
        "start" : False,
        "end" : False
    }

    if request.method == "POST":

        # TODO Validate entered values
        event_name = request.form.get('event_name')
        description = request.form.get('description')
        capacity = request.form.get('capacity')
        start = request.form.get('start')
        end = request.form.get('end')

        # Value Validation
        if not event_name.strip():
           errors["name"] = True

        if not description.strip():
            errors["desc"] = True

        try:
            capacity = int(capacity)
        except:
            errors["capacity"] = True

        if not start.strip():
            errors["start"] = True
        
        if not end.strip():
            errors["end"] = True

        for _ in errors:
            if errors[_] is True:
                return render_template('create.html', errors=errors)
                

        new_event = formatEvent(event_name, description, capacity, session["user_id"], start, end)

        addEvent(new_event)

        return redirect('/')

    return render_template('create.html')

@app.route('/update', methods=['POST'])
def update():
    # ERROR Handling
    errors = {
        "name" : False,
        "desc" : False,
        "capacity" : False,
        "start" : False,
        "end" : False,
        "status" : False
    }

    event_id = request.form.get('event_id')
    creator_id = request.form.get('creator_id')
    event_name = request.form.get('event_name')
    description = request.form.get('description')
    start = request.form.get('start')
    end = request.form.get('end')
    cap = request.form.get('capacity')
    status = request.form.get('status')

    # Value Validation
    try:
        creator_id = int(creator_id)
    except:
        return "INVALID CREATOR ID"

    if session["user_id"] != creator_id:
        errors["creator"] = True

    if not event_name.strip():
        errors['name'] = True

    if not description.strip():
        errors["desc"] = True

    try:
        cap = int(cap)
    except:
        errors["capacity"] = True
    
    if not start.strip() or len(re.findall("^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", start)) == 0: # Just check format with regular expression
        errors["start"] = True

    if not end.strip() or len(re.findall("^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", end)) == 0:
        errors["end"] = True

    if status not in STATUS:
        errors["status"] = True

    for _ in errors:
        if errors[_] is True:
            return render_template('manage.html', errors=errors)

    updated_event = formatEvent(event_name, description, cap, creator_id, start, end, status) + (event_id,)

    if not updateEvent(updated_event):
        return "ERROR"

    


    return redirect('/')

@app.route('/join', methods=['POST'])
def join():

    user_id = request.form.get('user_id')
    event_id = request.form.get('event_id')

    if not logUserEventJoin(user_id, event_id):
        print('User Already Joined')
        return redirect ('/')

    return redirect('/')

@app.route('/leave', methods=['POST'])
def leave():
    user_id = request.form.get('user_id')
    event_id = request.form.get('event_id')

    if not logUserLeave(user_id, event_id):
        return redirect('/', 304)
    
    return redirect('/')

@app.route('/kick', methods=['POST'])
def kick():

    event_id = request.form.get('id')
    creator_id = request.form.get('creator_id')
    user_id = request.form.get('user_id') # The one getting kicked 

    print("Session ID:", session["user_id"], type(session["user_id"]))
    print("Creator ID:", creator_id, type(creator_id))

    try:
        creator_id = int(creator_id)
    except:
        return "INVALID CREATOR ID"

    if not creator_id:
        return "ERROR - NO CREATOR ID"
    
    if not event_id.strip():
        return "ERROR - NO EVENT ID"
    
    if creator_id != session["user_id"]:
        return f"CREATOR ID : {creator_id} | SESSION ID : {session["user_id"]}"
    
    # Kick user from the event
    if not kickUserFromEvent(user_id, event_id):
        return "ERROR - NO MATCHING CASE"

    return redirect('/manage', code=307)

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # Check form fields
        if not username:
            return redirect('/register')
        if not password:
            return redirect('/register')
        if not confirmation:
            return redirect('/register')
        if password != confirmation:
            return redirect('/register')
        
        # Upload new user to database
        logged = logNewUser(username, password)

        if logged == False:
           return redirect('/register')
        
        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    
    session.clear() # Ensure no current sessions

    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        # Check form fields
        if not username:
            print('No Username')
            return redirect('/login')
        if not password:
            print('No Password')
            return redirect('/login')
        
        if not getUser(username):
            return redirect('/')

        userNameData, hash, id = getUser(username)

        if not check_password_hash(hash, password):
            print('Incorrect Username or Password')
            return redirect('/login')

        session["user_id"] = id

        return redirect('/')


    return render_template('login.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

@app.route('/manage', methods=['GET', 'POST'])
def manageEvent():

    if request.method == 'POST':
        if not session["user_id"]:
            return redirect('/')
        
        event_id = request.form.get('id')
        

        if not event_id:
            return redirect('/')
        
        event_data = getEvent(event_id)

        if session["user_id"] != event_data["creator_id"]:
            return redirect('/')

        participants = getEventParticipants(event_id)
        logs = getEventHistory(event_id)
        print(participants)
        return render_template("manage.html", event_data = event_data, participants=participants, statuses=STATUS, logs=logs)
    
    return request.form