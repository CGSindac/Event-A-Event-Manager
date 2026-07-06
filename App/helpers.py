import sqlite3
from werkzeug.security import generate_password_hash
import re

STATUS = ('Open', 'Ongoing', 'Closed')
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

# Date Formatting
def formatDate(datetime): # Returns a formated date-time for easier readablity for users
    try:
        full_date = re.split('T', datetime)
        split_date = re.split('-',full_date[0])

        year = split_date[0]
        month_index = int(split_date[1])
        month = MONTHS[month_index-1]
        day = split_date[2]

        format = f"{full_date[1]} {day} {month} {year}"
        return format
    except:
        return "CANNOT GET DATE-TIME"

# Fetching event Data
def get_all_events() -> list:
    # Connect to Database
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    event_list = []

    # Get events
    events = cursor.execute("SELECT name, status, desc, start, end, id FROM events")
    for event in events.fetchall():
        name, status, desc, start, end, id = event

        

        event_list.append({"name" : name, "status" : status, "desc" : desc, "start" : start, "end" : end, "id" : id})

    conn.close()
    
    return event_list

def getUserJoinedEvents(user_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    events_list = []

    events = cursor.execute('SELECT name, desc, capacity, start, end, status, id FROM events JOIN event_participants ON events.id = event_participants.event_id WHERE event_participants.user_id = ?', (user_id,))

    for event in events.fetchall():
        name, desc, cap, start, end, status, id = event

        fStart = formatDate(start)
        fEnd = formatDate(end)

        attendees = cursor.execute('SELECT COUNT(user_id) FROM event_participants WHERE event_id = ? GROUP BY event_id', (id,))
        count = attendees.fetchone()

        events_list.append({"name" : name, "desc" : desc, "capacity" : cap, "start" : [start, fStart], "end" : [end, fEnd], "status" : status, "id" : id, "attendees" : count[0]})

    conn.close()

    return events_list

def getUserNotJoinedEvents(user_id) -> list: 
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    events_list = []

    events = cursor.execute('SELECT name, desc, capacity, start, end, status, id FROM events WHERE id NOT IN (SELECT id FROM events JOIN event_participants ON events.id = event_participants.event_id WHERE event_participants.user_id = ?) AND status <> "Closed" AND status <> "Ongoing"', (user_id,))

    for event in events.fetchall():
        name, desc, cap, start, end, status, id = event

        fStart = formatDate(start)
        fEnd = formatDate(end)

        attendees = cursor.execute('SELECT COUNT(user_id) FROM event_participants WHERE event_id = ? GROUP BY event_id', (id,))
        count = attendees.fetchone()

        if not count:
            count = (0,)

        if int(count[0]) >= int(cap):
            continue    

        events_list.append({"name" : name, "desc" : desc, "capacity" : cap, "start" : [start, fStart], "end" : [end, fEnd], "status" : status, "id" : id, "attendees" : count[0]})

    conn.close()

    return events_list

def getUserCreatedEvents(user_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    events_list = []

    events = cursor.execute('SELECT name, desc, capacity, start, end, status, id FROM events WHERE creator_id = ?', (user_id,))
        
    for event in events.fetchall():
        name, desc, cap, start, end, status, id = event

        fStart = formatDate(start)
        fEnd = formatDate(end)

        attendees = cursor.execute('SELECT COUNT(user_id) FROM event_participants WHERE event_id = ? GROUP BY event_id', (id,))
        count = attendees.fetchone()

        if not count:
           count = (0,)

        events_list.append({"name" : name, "desc" : desc, "capacity" : cap, "start" : [start, fStart], "end" : [end, fEnd], "status" : status, "id" : id, "attendees" : count[0]})


    conn.close()

    return events_list

def getEvent(id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    event = cursor.execute('SELECT events.id, username, name, desc, capacity, start, end, status, creator_id FROM events JOIN users ON events.creator_id = users.id WHERE events.id = ?', (id,))
    event_id, creator, name, desc, cap, start, end, status, creator_id = event.fetchone()

    fStart = formatDate(start)
    fEnd = formatDate(end)

    conn.close()
    return {"id" : event_id, "creator_id" : creator_id, "creator" : creator, "name" : name, "desc" : desc, "capacity" : cap, "start" : [start, fStart], "end" : [end, fEnd], "status" : status}

def getEventParticipants(event_id):
    conn = sqlite3.connect('database.db', check_same_thread = False)
    cursor = conn.cursor()

    participant_list = []
    count = 0

    try:
        participants = cursor.execute('SELECT username, id FROM users JOIN event_participants ON users.id = event_participants.user_id WHERE event_participants.event_id = ?', (event_id,))
    except:
        conn.close()
        return False
    
    for participant in participants.fetchall():
        username, id = participant
        participant_list.append({"username" : username, "id" : id})
        count += 1

    conn.close()

    return  {"count" : count, "participants" : participant_list}

def formatEvent(name, description, capacity, user_id, start="N/A", end="N/A",  status="Open") -> tuple: # creates an event tuple

    if not start.strip():
        start = "N/A"

    if not end.strip():
        end = "N/A"

    if not status.strip() or status.strip() not in STATUS:
        status="Open"

    return (
        name,
        description,
        capacity,
        start,
        end,
        status,
        user_id
    )

def addEvent(event): # Takes in an event dictionary then inserts into TABLE events in database 
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    returnVal = True

    if event == None:
        return False
    
    cursor.execute("INSERT INTO events(name, desc, capacity, start, end, status, creator_id) VALUES (?, ?, ?, ?, ?, ?, ?)", event)
    conn.commit()

    (event_name, *_, creator_id) = event

    print("Event:", event_name)
    print("Creator ID:", creator_id)

    try:
        new_event = cursor.execute('SELECT id, creator_id FROM events WHERE name = ? AND creator_id = ?', (event_name, creator_id))
        event_id, user_id = new_event.fetchone()

        cursor.execute('INSERT INTO event_logs (event_id, user_id, action) VALUES (?, ?, ?)', (event_id, user_id, "Created"))
        conn.commit()
    except:
        returnVal = False
    
    conn.close()

    return returnVal

def updateEvent(event): # Takes in formatted Event
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    returnVal = True

    (*_, creator_id, event_id) = event
    print(creator_id, event_id)

    try:
        cursor.execute('UPDATE events SET name = ?, desc = ?, capacity = ?, start = ?, end = ?, status = ? WHERE creator_id = ? AND id = ?', event)
        conn.commit()
    except:
        returnVal = False

    try:
        cursor.execute('INSERT INTO event_logs (user_id, event_id, action) VALUES (?, ?, ?)', (creator_id, event_id, "Updated"))
        conn.commit()
    except:
        print("CANNOT LOG")
        returnVal = False    
    
    cursor.close
    return returnVal

def getEventHistory(id):
    returnVal = True

    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    event_logs = []

    logs = cursor.execute('SELECT event_id, users.username, user_id, action, timestamp FROM event_logs JOIN users ON event_logs.user_id = users.id WHERE event_id = ?', (id,))
    
    for log in logs.fetchall():
        event_id, username, user_id, action, timestamp = log
        event_logs.append({"event_id" : event_id, "username" : username, "user_id" : user_id, "action" : action, "timestamp" : timestamp})
        
    return event_logs

def logUserEventJoin(user_id, event_id):
    returnVal = True

    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO event_participants (event_id, user_id) VALUES (?, ?)', (event_id, user_id))
        cursor.execute('INSERT INTO event_logs (event_id, user_id, action) VALUES (?, ?, ?)', (event_id, user_id, "Joined"))
        conn.commit()
    except:
        returnVal = False

    conn.close()

    return returnVal

def kickUserFromEvent(user_id, event_id):

    returnVal = True
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM event_participants WHERE user_id = ? AND event_id = ?', (user_id, event_id))
        cursor.execute('INSERT INTO event_logs (event_id, user_id, action) VALUES (?, ?, ?)', (event_id, user_id, "Kicked"))
        conn.commit()
    except:
        returnVal = False

    conn.close()


    return returnVal

def logUserLeave(user_id, event_id):

    returnVal = True
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM event_participants WHERE user_id = ? AND event_id = ?', (user_id, event_id))
        cursor.execute('INSERT INTO event_logs (event_id, user_id, action) VALUES (?, ?, ?)', (event_id, user_id, "Left"))
        conn.commit()
    except:
        returnVal = False

    conn.close()


    return returnVal

# User handling
def logNewUser(username, password) -> bool:
    returnVal = True
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()

    if not username or not password:
        return False
    
    passwordHash = generate_password_hash(password)
    
    newUser = (username, passwordHash)
    # Upload to database

    try:
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", newUser)
    except:
        returnVal = False

    conn.commit()
    conn.close()

    return returnVal

def getUser(username) -> tuple:
    conn =sqlite3.connect("database.db", check_same_thread=False)
    cursor = conn.cursor()

    data = None

    try:
        userData = cursor.execute("SELECT username, hash, id FROM users WHERE username = ?", (username,))
        data = userData.fetchone()
    except:
        data = False
    
   
    conn.close()

    return data

if __name__ == "__main__":
    get_all_events()