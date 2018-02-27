# coding: utf-8

# Copyright 2018 IBM All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import json

# WebSockets
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory, connectWS
from twisted.python import log
from twisted.internet import ssl, reactor


class RecognizeListener:
    def __init__(self, audio, options, recognize_callback, url, headers):
        self.audio = audio
        self.options = options
        self.callback = recognize_callback
        self.url = url
        self.headers = headers

        factory = self.WebSocketClientFactory(self.audio, self.options,
                                          self.callback, self.url, self.headers)
        factory.protocol = self.WebSocketClient

        if factory.isSecure:
            contextFactory = ssl.ClientContextFactory()
        else:
            contextFactory = None
        connectWS(factory, contextFactory)

        reactor.run()

    class WebSocketClient(WebSocketClientProtocol):
        def __init__(self, factory, audio, options, callback):
            self.factory = factory
            self.audio = audio
            self.options = options
            self.callback = callback
            self.isListening = False
            self.bytes_sent = 0
            self.ONE_KB = 1000  # in bytes
            self.TIMEOUT_PREFIX = "No speech detected for"
            self.CLOSE_SIGNAL = 1000
            self.TEN_MILLISECONDS = 0.01
            super(self.__class__, self).__init__()

        def build_start_message(self, options):
            options['action'] = 'start'
            return options

        def build_close_message(self):
            return json.dumps({'action': 'close'})

        # helper method that sends a chunk of audio if needed (as required what the specified pacing is)
        def send_audio(self, data):
            def send_chunk(chunk, final=False):
                self.bytes_sent += len(chunk)
                self.sendMessage(chunk, isBinary=True)
                if final:
                    self.sendMessage(b'', isBinary=True)

            if (self.bytes_sent + self.ONE_KB >= len(data)):
                if (len(data) > self.bytes_sent):
                    send_chunk(data[self.bytes_sent:len(data)], True)
                    return

            send_chunk(data[self.bytes_sent:self.bytes_sent + self.ONE_KB])
            self.factory.reactor.callLater(self.TEN_MILLISECONDS, self.send_audio, data=data)
            return

        def extract_transcripts(self, alternatives):
            transcripts = []
            for alternative in alternatives:
                transcript = {}
                if 'confidence' in alternative:
                    transcript['confidence'] = alternative['confidence']
                transcript['transcript'] = alternative['transcript']
                transcripts.append(transcript)
            return transcripts

        def onConnect(self, response):
            log.msg("onConnect, server connected: {}".format(response.peer))
            self.callback.on_connected()

        def onOpen(self):
            log.msg("onOpen, Websocket connection open")
            # send the initialization parameters
            init_data = self.build_start_message(self.options)
            self.sendMessage(json.dumps(init_data).encode('utf8'))

            # start sending audio right away (it will get buffered in the STT service)
            self.send_audio(self.audio.read())
            log.msg("onOpen ends")

        def onMessage(self, payload, isBinary):
            json_object = json.loads(payload.decode('utf8'))

            if 'error' in json_object:
                log.msg('Error : {}'.format(json_object['error']))
                # Only call on_error() if a real error occurred. The STT service sends
                # // {"error" : "No speech detected for 5s"} for valid timeouts, configured by
                # options.inactivity_timeout
                error = json_object['error']
                if error.startswith(self.TIMEOUT_PREFIX):
                    self.callback.on_inactivity_timeout()
                else:
                    self.callback.on_error()

            # if uninitialized, receive the initialization response from the server
            elif 'state' in json_object:
                if not self.isListening:
                    self.isListening = True
                else:
                    # close the connection
                    self.sendMessage(self.build_close_message())
                    self.callback.on_transcription_complete()
                    self.sendClose(self.CLOSE_SIGNAL)
                    self.sendClose(self.CLOSE_SIGNAL)

            # if in streaming
            elif 'results' in json_object or 'speaker_labels' in json_object:
                hypothesis = ''
                # empty hypothesis
                if len(json_object['results']) == 0:
                    print('empty hypothesis!')
                # regular hypothesis
                else:
                    hypothesis = json_object['results'][0]['alternatives'][0][
                        'transcript']
                    b_final = (json_object['results'][0]['final'] == True)
                    transcripts = self.extract_transcripts(
                        json_object['results'][0]['alternatives'])

                    if b_final:
                        self.callback.on_hypothesis(hypothesis)
                    else:
                        self.callback.on_transcription(transcripts)

        def onClose(self, wasClean, code, reason):
            log.msg("onClose, WebSocket connection closed: {0}".format(reason),
                    "code: ", code, "clean: ", wasClean, "reason: ", reason)
            self.factory.endReactor()

    class WebSocketClientFactory(WebSocketClientFactory):
        def __init__(self, audio, options, callback, url=None, headers=None):
            WebSocketClientFactory.__init__(self, url=url, headers=headers)
            self.audio = audio
            self.options = options
            self.callback = callback
            self.SIX_SECONDS = 6
            self.openHandshakeTimeout = self.SIX_SECONDS
            self.closeHandshakeTimeout = self.SIX_SECONDS

        def endReactor(self):
            reactor.stop()

        # this function gets called every time connectWS is called (once per WebSocket connection/session)
        def buildProtocol(self, addr):
            proto = RecognizeListener.WebSocketClient(
                self, self.audio, self.options, self.callback)
            return proto