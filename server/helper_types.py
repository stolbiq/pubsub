from collections import defaultdict
from time import time


class Message:
    """
    Represents a message object.

    Attributes:
    - publish_time (float): The time at which the message was published. Default is the current time.
    - content (str): The content of the message. Default is an empty string.
    - pending_users (set): A set containing the names of users who have not yet received the message. Default is an empty set.
    """

    def __init__(self, publish_time=time(), content="", pending_users=set()):
        """
        Initialize a Message object.
        """
        self.publish_time = publish_time
        self.content = content
        self.pending_users = pending_users

    def remove_user(self, user_name):
        """
        Remove a user from the list of pending users.

        Args:
        - user_name (str): The name of the user to be removed from the list of pending users.
        """
        if user_name in self.pending_users:
            self.pending_users.remove(user_name)

    def jsonify(self):
        """
        Convert the Message object to a JSON-compatible dictionary.

        Returns:
        - dict: A dictionary representing the Message object in JSON format.
        """
        return {"publish_time": self.publish_time, "content": self.content}


class PendingMessages:
    """
    Represents a collection of pending messages.

    Attributes:
    - messages (defaultdict): A dictionary containing lists of messages for each topic.
    - ttl (int): Time-to-live for messages, specifying how long messages are retained in the pending messages list.
    """

    def __init__(self, ttl=10, messages=defaultdict(list[Message])):
        """
        Initialize a PendingMessages object.

        Args:
        - ttl (int): Time-to-live for messages. Default is 10 seconds.
        - messages (defaultdict): A dictionary containing lists of messages for each topic. Default is an empty defaultdict.
        """
        self.messages = messages
        self.ttl = ttl

    def __str__(self):
        """
        Return a string representation of the PendingMessages object.

        Returns:
        - str: A string representation of the PendingMessages object.
        """
        representation = ""
        for topic in self.messages:
            representation += f"Topic: {topic} \n"
            for msg in self.messages[topic]:
                representation += f"{msg.content} \n"
        return representation

    def get_topic_size(self, topic):
        """
        Get the size of the message list for a given topic.

        Args:
        - topic (str): The topic for which to get the size of the message list.

        Returns:
        - int: The size of the message list for the given topic.
        """
        return len(self.messages[topic])

    def add_new_message(self, topic, message):
        """
        Add a new message to the message list for a given topic.

        Args:
        - topic (str): The topic to which the message belongs.
        - message (Message): The message object to add to the list.
        """
        self.messages[topic].append(message)

    def remove_old_messages(self):
        """
        Remove old messages from the message lists based on the time-to-live (TTL) value.
        """
        now = time()
        for topic in self.messages:
            while True:
                # since the messages appended to the list in the order of their arrival,
                # the first is the oldest
                if (self.get_topic_size(topic) == 0) or (
                    self.messages[topic][0].publish_time >= (now - self.ttl)
                ):
                    break
                self.messages[topic].pop(0)

    def remove_fully_transmetted_messages(self, topic):
        """
        Remove messages that have been fully transmitted to all subscribed users based on the emptyness of Message.pending_users.

        Args:
        - topic (str): The topic from which to remove fully transmitted messages.
        """
        clear_topic_indexes = []
        for idx, msg in enumerate(self.messages[topic]):
            if len(msg.pending_users) == 0:
                clear_topic_indexes.append(idx)
        for idx in sorted(clear_topic_indexes, reverse=True):
            self.messages[topic].pop(idx)

    def find_start_index(self, disconnected_time, topic):
        """
        Find the index of the first message to send after a given disconnected time for a given topic.

        Args:
        - disconnected_time (float): The time at which the user was disconnected.
        - topic (str): The topic for which to find the start index.

        Returns:
        - int or None: The index of the first message after the disconnected time, or None if no such message is found.
        """
        start_index = None
        for idx, msg in enumerate(self.messages[topic]):
            if msg.publish_time >= disconnected_time:
                start_index = idx
                break
        return start_index

    def get_message(self, topic, message_index):
        """
        Get a message from the message list for a given topic at a specified index.

        Args:
        - topic (str): The topic from which to retrieve the message.
        - message_index (int): The index of the message to retrieve.

        Returns:
        - Message or None: The message object at the specified index, or None if the index is out of range.
        """
        if message_index >= 0 and message_index < self.get_topic_size(topic):
            return self.messages[topic][message_index]
        else:
            return None

    def remove_user_from_message(self, topic, message_index, user_name):
        """
        Remove a user from the pending users list of a message at a specified index for a given topic.

        Args:
        - topic (str): The topic to which the message belongs.
        - message_index (int): The index of the message in the message list.
        - user_name (str): The name of the user to remove from the pending users list.
        """
        self.messages[topic][message_index].remove_user(user_name)

    def remove_user_from_topic(self, topic, user_name):
        """
        Remove a user from the pending users lists of all messages for a given topic.

        Args:
        - topic (str): The topic from which to remove the user.
        - user_name (str): The name of the user to remove.
        """
        for msg in self.messages[topic]:
            if user_name in msg.pending_users:
                msg.remove_user(user_name)


class Subscriptions:
    """
    A class to manage subscriptions between users and topics.

    Attributes:
    - user_to_topic_subscriptions (defaultdict): A dictionary where keys are user names
            and values are sets of topics subscribed to by the user.
    - topic_to_user_subscriptions (defaultdict): A dictionary where keys are topics
            and values are sets of user names subscribed to the topic.
    """

    def __init__(self):
        """
        Initializes a Subscriptions object with empty dictionaries for user-topic and
        topic-user subscriptions.
        """
        self.user_to_topic_subscriptions = defaultdict(set)  # dict[user_name] = [topic]
        self.topic_to_user_subscriptions = defaultdict(set)  # dict[topic] = [user_name]

    def get_topics(self, user_name):
        """
        Retrieves the topics subscribed to by a given user.

        Args:
        - user_name (str): The name of the user.

        Returns:
        - set: A set of topics subscribed to by the user.
        """
        return self.user_to_topic_subscriptions[user_name]

    def get_users(self, topic):
        """
        Retrieves the users subscribed to a given topic.

        Args:
        - topic (str): The topic.

        Returns:
        - set: A set of user names subscribed to the topic.
        """
        return self.topic_to_user_subscriptions[topic]

    def add_user(self, user_name, topic):
        """
        Adds a user to the subscriptions for a specific topic.

        Args:
        - user_name (str): The name of the user.
        - topic (str): The topic to subscribe to.
        """
        self.user_to_topic_subscriptions[user_name].add(topic)
        self.topic_to_user_subscriptions[topic].add(user_name)

    def remove_user(self, user_name, topic):
        """
        Removes a user from the subscriptions for a specific topic.

        Args:
        - user_name (str): The name of the user.
        - topic (str): The topic to unsubscribe from.
        """
        if (
            user_name in self.user_to_topic_subscriptions
            and topic in self.topic_to_user_subscriptions
        ):
            self.user_to_topic_subscriptions[user_name].remove(topic)
            self.topic_to_user_subscriptions[topic].remove(user_name)


class Sessions:
    """
    A class to manage user sessions.

    Attributes:
        - user_sid_to_name_sessions (defaultdict): A dictionary where keys are user session IDs
            and values are user names.
        - user_name_to_sid_sessions (defaultdict): A dictionary where keys are user names
            and values are user session IDs.
    """

    def __init__(self):
        """
        Initializes a Sessions object with empty dictionaries for user session mappings.
        """
        self.user_sid_to_name_sessions = defaultdict(str)  # dict[user_sid] = user_name
        self.user_name_to_sid_sessions = defaultdict(str)  # dict[user_name] = user_sid

    def get_user_name(self, user_sid):
        """
        Retrieves the user name associated with a given user session ID.

        Args:
        - user_sid (str): The user session ID.

        Returns:
        - str: The user name associated with the user session ID, or None if not found.
        """
        if user_sid in self.user_sid_to_name_sessions:
            return self.user_sid_to_name_sessions[user_sid]
        return None

    def get_user_sid(self, user_name):
        """
        Retrieves the user session ID associated with a given user name.

        Args:
        - user_name (str): The user name.

        Returns:
        - str: The user session ID associated with the user name, or None if not found.
        """
        if self.is_user_connected(user_name):
            return self.user_name_to_sid_sessions[user_name]
        return None

    def add_user(self, user_name, user_sid):
        """
        Adds a user session mapping for the given user name and user session ID.

        Args:
        - user_name (str): The user name.
        - user_sid (str): The user session ID.
        """
        self.user_sid_to_name_sessions[user_sid] = user_name
        self.user_name_to_sid_sessions[user_name] = user_sid

    def remove_user_by_sid(self, user_sid):
        """
        Removes a user session mapping by the given user session ID.

        Args:
        - user_sid (str): The user session ID.
        """
        if user_sid in self.user_sid_to_name_sessions:
            user_name = self.user_sid_to_name_sessions[user_sid]
            if user_name in self.user_name_to_sid_sessions:
                del self.user_sid_to_name_sessions[user_sid]
                del self.user_name_to_sid_sessions[user_name]

    def get_all_connected_user_names(self):
        """
        Retrieves the set of all connected user names.

        Returns:
        - set: A set containing all connected user names.
        """
        return set(self.user_name_to_sid_sessions.keys())

    def is_user_connected(self, user_name):
        """
        Checks if a user with the given user name is currently connected.

        Args:
        - user_name (str): The user name.

        Returns:
        - bool: True if the user is connected, False otherwise.
        """
        return user_name in self.user_name_to_sid_sessions
