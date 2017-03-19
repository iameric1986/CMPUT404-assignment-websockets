#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect, jsonify
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

# A class to abstract websocket clients as per in-class example
# Ref: https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# Author: Abram Hindle
class Client:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, v):
        self.queue.put_nowait(v)

    def get(self):
        return self.queue.get()

myWorld = World()        
clients = list()

# Queue message to all the clients
# Ref: https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# Author: Abram Hindle
def send_all(msg):
    for client in clients:
        client.put(msg)

# Send all objects as json
# Ref: https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# Author: Abram Hindle
def send_all_json(obj):
    send_all(json.dumps(obj))

def set_listener( entity, data ):
    ''' do something with the update ! '''
    update[entity] = data
    send_all_json(update)
    
myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect('/static/index.html')

# Read the message from the web socket as per in-class example
# We need to update the world instead of just sending the message back to all listeners
# Ref: https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# Author: Abram Hindle
def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg = ws.receive()
            print('WS RECV: %s' % msg)
            if (msg is not None):
                packet = json.loads(msg)
                # We are loading the message as json, so we can iterate over it
                for entity, data in packet.iteritems():
                    # Update the world and do something with the update
                    myWorld.set(entity, data) 
                    set_listener(entity, data)
            else:
                break
    except:
        ''' Done '''
    return None

# Add client sockets as per in-class example
# Ref: https://github.com/abramhindle/WebSocketsExamples/blob/master/broadcaster.py
# Author: Abram Hindle
@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    client = Client()
    clients.append(client)
    g = gevent.spawn(read_ws, read_ws, client)
    try:
        while True:
            msg = client.get()
            print('Got a message')
            ws.send(msg)
    except Exception as e:
        print('WS Error %s' %e)
    finally:
        clients.remove(client)
        gevent.kill(g)
    return None


def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

##########################
# All the following functions are following the same implementation I used in the previous assignment
##########################

# Parse the JSON object and update the World
# Ref: http://stackoverflow.com/questions/2733813/iterating-through-a-json-object
# Author: tzot
def data_parse(entity, data):
    for axis, coord in data.iteritems():
        myWorld.update(entity, axis, coord)
    return None

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    entity_data = flask_post_json()
    if (len(entity_data) == 0):
        print("No data")
        return None

    if (request.method == 'POST'): # Update the world if the request is a POST
        data_parse(entity, entity_data)
        return jsonify(myWorld.get(entity))

    # If the request method is not POST, we can assume it is PUT
    # Create a new entity in the world
    myWorld.set(entity, entity_data)
    return jsonify(myWorld.get(entity))

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    return jsonify(myWorld.world())

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return jsonify(myWorld.get(entity))


@app.route("/clear", methods=['POST','GET'])
def clear():
    '''Clear the world out!''' 
    myWorld.clear()
    return jsonify(myWorld.world())



if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
