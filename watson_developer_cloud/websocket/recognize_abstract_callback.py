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

from abc import abstractmethod, ABCMeta

class RecognizeAbstractCallback:
  __metaclass__ = ABCMeta

  @abstractmethod
  def on_transcription(self, transcript):
    """
    Called when an interim result is received
    """
    pass

  @abstractmethod
  def on_connected(self):
    """
    Called when a WebSocket connection was made
    """
    pass

  @abstractmethod
  def on_error(self, error):
    """
    Called when there is an error in the Web Socket connection.
    """
    pass

  @abstractmethod
  def on_inactivity_timeout(self):
    """
    Called when there is an inactivity timeout.
    """
    pass

  @abstractmethod
  def on_listening(self):
    """
    Called when the service is listening for audio.
    """
    pass

  @abstractmethod
  def on_transcription_complete(self):
    """
    Called after the service returns the final result for the transcription.
    """
    pass

  def on_hypothesis(self, hypothesis):
    """
    Called when the service returns the final hypothesis
    """
    pass