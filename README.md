# AudioServer
replacement snips audio server

uses python 

proof of concept to rid the need to pause after saying the wake word
not to be used with the feedback sound when the wake word is detected (sound_feedback_enabled_default = true)

# Running

to get a list of all the mic devices to connect to
python AudioServer.py --show_audio_devices_info

once you have the mic index number from the list output above 
python AudioServer.py --input_audio_device_index 0 

usage: AudioServer.py [-h]
                      [--input_audio_device_index INPUT_AUDIO_DEVICE_INDEX]
                      [--device_name DEVICE_NAME] [--frame_size FRAME_SIZE]
                      [--mqtt_address MQTT_ADDRESS] [--mqtt_port MQTT_PORT]
                      [--show_audio_devices_info SHOW_AUDIO_DEVICES_INFO]

optional arguments:
  -h, --help            show this help message and exit
  --input_audio_device_index INPUT_AUDIO_DEVICE_INDEX
                        index of input audio device
  --device_name DEVICE_NAME
                        unique device name
  --frame_size FRAME_SIZE
                        frame size (default: 256 samples)
  --mqtt_address MQTT_ADDRESS
                        MQTT Server Address (default: localhost)
  --mqtt_port MQTT_PORT
                        MQTT Port (default: 1883)
  --show_audio_devices_info SHOW_AUDIO_DEVICES_INFO
                        outputs a list of input audio devices

