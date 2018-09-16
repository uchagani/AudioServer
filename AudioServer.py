#!/usr/bin/env python2
# -*- coding:utf-8 -*-

### **************************************************************************** ###
# 
# Project: Audio Server for Snips System
# Created Date: Friday, September 14th 2018, 8:54:27 pm
# Author: Greg
# -----
# Last Modified: Sun Sep 16 2018
# Modified By: Greg
# -----
# Copyright (c) 2018 Greg
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN
# AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 
### **************************************************************************** ###






import argparse
import platform
import struct
import time
import threading
import paho.mqtt.client as mqtt
import pyaudio
import wave
from io import BytesIO
import soundfile as sf
import json

 
        

class AudioServer(threading.Thread):
    """
    It creates an input audio stream from a microphone,
    This is the non-blocking version that uses the callback function of PyAudio.
    """

    def __init__(
            self,
            input_device_index=None,
            device_name=None,
            mqtt_address=None,
            mqtt_port=1883,
            frame_size=256):

        """
        Constructor.
        """

        super(AudioServer, self).__init__()
        self.device_name = device_name
        self.sample_rate = 16000
        self.frame_length = frame_size
        self._input_device_index = input_device_index
        self.MQTT_ADDRESS = mqtt_address
        self.MQTT_PORT = mqtt_port
        self.play_thread = threading.Thread()
        self.asr_thread = threading.Thread()
        self.playing = False
        self.buff = []
        #self.buffout = []

    def run(self):
        """
        Creates an input audio stream
        """

        def on_connect(client, userdata, flags, rc):
            mqtt_client.subscribe('hermes/audioServer/{}/playBytes/#'.format(self.device_name))
            mqtt_client.subscribe('hermes/asr/startListening')
            mqtt_client.subscribe('hermes/asr/textCaptured')
            mqtt_client.subscribe('hermes/asr/stopListening')

        def on_message(client, userdata, msg):
            if msg.topic.startswith("hermes/audioServer/{}/playBytes".format(self.device_name)):  
                self.playing = True
                rID = msg.topic.rsplit('/', 1)[-1]  
                self.play_thread = threading.Thread(target=play,args=(msg.payload,rID))
                self.play_thread.do_run = True
                self.play_thread.start()
            elif msg.topic == 'hermes/asr/startListening':
                d = json.loads(msg.payload)
                if d['siteId'] == self.device_name:
                    self.asr_thread = threading.Thread(target=stream_for_asr,args=(d,))
                    self.asr_thread.do_run = True
                    self.asr_thread.start()
            elif msg.topic == 'hermes/asr/textCaptured':
                d = json.loads(msg.payload)
                if d['siteId'] == self.device_name:
                    self.asr_thread.do_run = False
            elif msg.topic == 'hermes/asr/stopListening':
                d = json.loads(msg.payload)
                if d['siteId'] == self.device_name:
                    self.asr_thread.do_run = False

        def stream_for_asr(payload):
            """
            to prevent the need to pause after the wake word
            """
            #output = wave.open('/Users/greg/testing.wav', 'wb')
            #output.setnchannels(1)
            #output.setsampwidth(2)
            #output.setframerate(16000)

            start_count = 2
            t = threading.currentThread()

            while t.do_run == True:
                try:
                    item = self.buff[start_count] 
                    #output.writeframes(self.buffout[start_count] )
                except IndexError:
                    #print("index error")
                    if start_count > 100:
                        break
              
                mqtt_client.publish('hermes/audioServer/{}/audioFrame'.format(self.device_name),payload=item)
                start_count += 1
                time.sleep( 0.03 )
            self.buff = []
            #self.buffout = []
            #output.close()
            

        def play(data,requestId):
            """
            snips has sent a wave file to play
            """

            try:
                b = BytesIO(data)
                wf = wave.open(b, 'rb')
                p = pyaudio.PyAudio()
                chunks = 50

                # open stream
                stream = p.open(format = p.get_format_from_width(wf.getsampwidth()),
                            channels = wf.getnchannels(),
                            rate = wf.getframerate(),
                            output = True)

                # read data
                data = wf.readframes(chunks)

                # play stream
                t = threading.currentThread()
                while data != '':
                    if t.do_run == True:
                        stream.write(data)
                        data = wf.readframes(chunks)
                    else:
                        break
        
                stream.stop_stream()
                stream.close()
                p.terminate()
            except Exception as e:
                print(e)
            finally:
                self.playing = False
                message = {'id':requestId, 'siteId':self.device_name,'sessionId':None}
                mqtt_client.publish('hermes/audioServer/{}/playFinished'.format(self.device_name),json.dumps(message))

            
		
        def _audio_callback(in_data, frame_count, time_info, status):
            """
            pyaudio mic data
            """

            if frame_count >= self.frame_length:
         
                #pcm = struct.unpack_from("h" * self.frame_length, in_data)

                fio = BytesIO()
                wf = wave.open(fio, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(in_data)
                wf.close

                content = fio.getvalue()
            
                b = bytearray()
                b.extend(content)
                if len(self.buff)>10 and self.asr_thread.isAlive() == False:
                    self.buff.pop(0)
                    #self.buffout.pop(0)

                if self.playing == False:
                    self.buff.append(b)
                    #self.buffout.append(in_data)
           
                if self.playing == False and self.asr_thread.isAlive() == False:
                    mqtt_client.publish('hermes/audioServer/{}/audioFrame'.format(self.device_name),payload=b)
     
            return None, pyaudio.paContinue

        pa = None
        audio_stream = None
        mqtt_client = mqtt.Client()
        

        try:
            pa = pyaudio.PyAudio()
            
            audio_stream = pa.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=self._input_device_index,
			    stream_callback=_audio_callback)

            audio_stream.start_stream()

            print("Started with following settings:")
            if self._input_device_index:
                print("Input device: %d (check with --show_audio_devices_info)" % self._input_device_index)
            else:
                print("Input device: default (check with --show_audio_devices_info)")
            print("Waiting ...\n")

            mqtt_client.on_connect = on_connect
            mqtt_client.on_message = on_message
            mqtt_client.connect(self.MQTT_ADDRESS, self.MQTT_PORT)
            mqtt_client.loop_forever()

        except KeyboardInterrupt:
            print('stopping ...')
        finally:
            self.asr_thread = None
            self.play_thread = None
            if pa is not None:
                pa.terminate()
            


    _AUDIO_DEVICE_INFO_KEYS = ['index', 'name', 'defaultSampleRate', 'maxInputChannels']

    @classmethod
    def show_audio_devices_info(cls):
        """ 
        Provides information regarding different audio devices available. 
        """

        pa = pyaudio.PyAudio()

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            print(', '.join("'%s': '%s'" % (k, str(info[k])) for k in cls._AUDIO_DEVICE_INFO_KEYS))

        pa.terminate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=True)

    parser.add_argument('--input_audio_device_index', help='index of input audio device', type=int, default=None)
    parser.add_argument('--device_name', help='unique device name', type=str, default='default')
    parser.add_argument('--frame_size', help='frame size (default: 256 samples)', type=int, default=512)
    parser.add_argument('--mqtt_address', help='MQTT Server Address (default: localhost)', type=str, default='localhost')
    parser.add_argument('--mqtt_port', help='MQTT Port (default: 1883)', type=int, default=1883)
    parser.add_argument('--show_audio_devices_info', help='outputs a list of input audio devices')

    args = parser.parse_args()

    if args.show_audio_devices_info:
        AudioServer.show_audio_devices_info()
    else:
        AudioServer(
            input_device_index=args.input_audio_device_index,
            device_name=args.device_name,
            frame_size=args.frame_size,
            mqtt_address=args.mqtt_address,
            mqtt_port=args.mqtt_port
        ).run()
