from flask import Flask, jsonify, request
from flask_socketio import SocketIO, disconnect, emit
from collections import defaultdict
import logging
from time import time

from helper_types import PendingMessages, Sessions, Subscriptions, Message
from helper_tools import timestamp_to_datetime


app = Flask(__name__)
socketio = SocketIO(app)

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

# Time-to-live for messages, specifying how long messages are retained in the pending messages list.
TTL = 10

subscriptions = Subscriptions()
pending_messages = PendingMessages(ttl=TTL)
sessions = Sessions()

# A dictionary containing last disconnected time of a user.
last_disconnected_time = defaultdict(float) # dict[user_name] = disconnected_time

@socketio.on("start")
def handle_start(data):
    """
    Handle the 'start' event triggered when a client emits a start event.

    Parameters:
    - data (dict): A dictionary containing user_name.
    """
    user_sid = request.sid
    user_name = data["user_name"]

    # We support only one connected session per user_name. Checks if the user is already connected. If so, disconnects the user and returns.
    if sessions.is_user_connected(user_name):
        disconnect()
        return

    print(f"{timestamp_to_datetime(time())} User connected: {data['user_name']}")
    
    # Add the user to the list of currently connected users.
    sessions.add_user(user_name, user_sid)

    # Retrieve the topics the user is subscribed to.
    topics = subscriptions.get_topics(user_name)

    # Enter the user into the corresponding rooms for each topic.
    for topic in topics:
        socketio.server.enter_room(sid=user_sid, room=topic)

    # Retrieve the last disconnected time for the user (if available).
    disconnected_time = last_disconnected_time[user_name] if user_name in last_disconnected_time else 0

    # Removes old messages.
    pending_messages.remove_old_messages()

    for topic in topics:

        # Send the messages to the user starting from the last received message index.
        start_index = pending_messages.find_start_index(disconnected_time, topic)

        if start_index is not None: #
            for index in range(start_index, pending_messages.get_topic_size(topic)):
    
                msg = pending_messages.get_message(topic, index).jsonify()
                msg["topic"] = topic
                emit("response", msg, to=user_sid)

                # Removes the user from the list of pending users of the message after it has been sent.
                pending_messages.remove_user_from_message(topic, index, user_name)

            # Clean messages removing those that have been fully sent.
            pending_messages.remove_fully_transmetted_messages(topic)


@socketio.on("disconnect")
def handle_disconnect():
    """
    Handle the "disconnect" event triggered when a user disconnects.
    """
    user_sid = request.sid
    user_name = sessions.get_user_name(user_sid)

    # Updates the last disconnected time for the user.
    last_disconnected_time[user_name] = time()

    # Removes the user from the list of connected users.
    sessions.remove_user_by_sid(user_sid)
    print(f"{timestamp_to_datetime(time())} User disconnected: {user_name if user_name else user_sid}")


def _get_pending_users(topic):
    """
    Get the users who are subscribed to a given topic but are not currently connected.

    Parameters:
    - topic (str): The topic for which pending users are to be retrieved.

    Returns:
    - set: A set containing the names of users who are subscribed to the topic but are not currently connected.
    """
    all_subscribed = subscriptions.get_users(topic)
    all_connected = sessions.get_all_connected_user_names()
    pending_users = all_subscribed - all_connected
    return pending_users

@app.route("/publish_messages", methods=["POST"])
def publish_messages():
    """
    Publish multiple messages to their respective topics.

    Example of a payload:
    {
        "messages": [
            {   
                "topic": "food",
                "content": "Apples"
            },
            {   
                "topic": "food",
                "content": "Bananas"
            },
            {   
                "topic": "news",
                "content": "Paris"
            }
            
        ]
    }
    """
    data = request.json

    if "messages" not in data:
        return jsonify({"error": "Missing messages parameter"}), 400
        
    messages = data["messages"]

    if type(messages) != list:
        return jsonify({"error": "Object messages must be a list"}), 400
    
    publish_time = time()

    for msg in messages:
        if "topic" in msg and "content" in msg:  
            topic = msg["topic"]
            content = msg["content"]
            socketio.emit("response", {"publish_time": publish_time, "topic": topic, "content": content}, room=topic)
            pending_users = _get_pending_users(topic)

            # Add a message to pending_messages if there are some users that have not received it yet.
            if len(pending_users) != 0:
                pending_messages.add_new_message(topic, Message(publish_time, content, pending_users))
        else:
            log.error(f"Message {msg} does not have topic or content field")

    return jsonify({"message": "Messages published"}), 200


@app.route("/subscribe", methods=["POST"])
def subscribe():
    """
    Subscribe a client to one or more topics.

    Example of a payload:
    {
        "user_name": "bob",
        "topics": ["food", "news"]
    }
    """
    data = request.json
    if "topics" not in data or "user_name" not in data:
        return jsonify({"error": "Missing topics or user_name parameter"}), 400

    topics = data["topics"]
    user_name = data["user_name"]

    if type(topics) != list:
        return jsonify({"error": "Parameter topics must be a list"}), 400

    for topic in topics:

        # Add the user to subscriptions.
        subscriptions.add_user(user_name, topic)

        # If the user is connected, it should be added in the room.
        if sessions.is_user_connected(user_name):
            user_sid = sessions.get_user_sid(user_name)
            for topic in topics:
                socketio.server.enter_room(sid=user_sid, room=topic)

    return jsonify({"message": f"Client subscribed to topics: {topics}"}), 200


@app.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    """
    Unsubscribe a client from one or more topics.

    Example of a payload:
    {
        "user_name": "bob",
        "topics": ["food", "news"]
    }
    """
    data = request.json
    if "topics" not in data or "user_name" not in data:
        return jsonify({"error": "Missing topics or user_name parameter"}), 400

    topics = data["topics"]
    user_name = data["user_name"]

    if type(topics) != list:
        return jsonify({"error": "Parameter topics must be a list"}), 400

    for topic in topics:
        if topic in subscriptions.get_topics(user_name):

            # Remove the user from subscriptions and leave the topic room if he is connected.
            subscriptions.remove_user(user_name, topic)
            if sessions.is_user_connected(user_name):
                user_sid = sessions.get_user_sid(user_name)
                socketio.server.leave_room(sid=user_sid, room=topic)

            # Remove the user from the pending messages and clean the pending messages from those that were transmetted to all subscribed users.
            pending_messages.remove_user_from_topic(topic, user_name)
            pending_messages.remove_fully_transmetted_messages(topic)
        else:
            log.error(f'User {user_name} is not subscribed to topic {topic}')


    return jsonify({"message": f"Unsubscribed from the topic: {topics}"}), 200


if __name__ == "__main__":
    socketio.run(app, port=8000, debug=True)
