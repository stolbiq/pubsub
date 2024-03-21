import datetime
import socketio
from time import time

def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime(
        "%H:%M%:%S"
    )

user_name = input("\nHi :) What is your chat name? \n")


sio = socketio.Client()
sio.connect("http://localhost:8000")

sio.emit("start", {"user_name": user_name})

@sio.on("response")
def response(data):
    message = data
    print(f"{message['topic']} => published: {timestamp_to_datetime(message['publish_time'])} received: {timestamp_to_datetime(time())} => {message['content']}")

@sio.on("disconnect")
def handle_disconnect():
    print(f"Session is disconnected because this user is already connected")


sio.wait()
