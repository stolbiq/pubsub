Welcome to publish-subscribe application using Flusk and WebSockets.

### Installation

Python version = Python 3.11.5

We recomment using a virtual environment to manage the dependencies:
```
python -m venv pubsub_env
```
Install the dependencies:
```
source pubsub_env/bin/activate
pip install -r requirements.txt
```

### Testing the application
Launch the server
```
python server/server.py
```
In a separate terminal launch the client
```
python client.py
```
You will be asked to type your chat name: that is your unique indentifier. If you disconnect and reconnect again under this identifier, the server will recognize you. If you try to connect using the same identifier while this name is already connected, you will be disconnected.

The server has some endpoints you can call. Please, check their docstring in `server/server.py`. To call these endpoints you can use such tools like Postman. We provide the Postman collection with /publish_messages, /subscribe and /unsubscribe endpoints that you can import into Postman and try out.

### The scenarios to be tested:
- Connecting under the same user name multiple times implies that the second gets disconnected.
- After subscribing to a topic, the user starts receiving the messages published after he was subscribed.
- The user can subscribe to multiple topics and he will receive the messages from all topics he is subscribed to.
- Also multiple users with different user names can be connected at the same time
- If a user gets disconnected and then reconnects again, he receives all the messages he is subscribed to if their time-to-live is less than the one defined by the server.
- If the user unsubscribes from a topic, he will no longer receive any messages from this topic. If meanwhile he was disconnected, he will also not receive the messages published to the topic while he was disconnected.


### TODO
The application was thouroghly tested under different scenarios. However, adding automated tests is highly recommended. 