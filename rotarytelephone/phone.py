import websocket
import serial
import binascii
from time import sleep
from gpiozero import Button

# https://www.dfrobot.com/product-1121.html
# Manual: https://github.com/Arduinolibrary/DFPlayer_Mini_mp3/raw/master/DFPlayer%20Mini%20Manual.pdf

# Serial bytes,  checksums omitted since this is not rocket surgery.
snd_stop = '7eff060E000000ef' # 0E == pause audio
snd_dialtone = '7eff0603000001ef' # 0001

# Wired to the handset speaker of the phone
dfplayer = serial.Serial (port="/dev/serial0", baudrate=9600) 

# PI Zerp inputs from the phone
hook = Button(pin=18)
dialing = Button(pin=23)
pulse = Button(pin=24)
pulse_count = 0

# Plays a sound by sending 03 command 
def play(snd):
    dfplayer.write(binascii.a2b_hex(snd))

# Pauses audio
def stop_play():
    dfplayer.write(binascii.a2b_hex(snd_stop))
    

# stop audio and notify serve that the handset is back on the hook
def on_hook():
    print("<<onhook")
    stop_play()
    ws.send("onhook")

# play dialtone (0001.mp3) when handset picked up off the hook
def off_hook():
    print("<<offhook")
    play(snd_dialtone)
    ws.send("offhook")

# triggered when the rotary dial is in motion
def on_dialing():
    print("<<dialing")
    stop_play()
    ws.send("dialing")
    
# triggered for each pulse on the rotary dial
def on_pulse():
    global pulse_count
    pulse_count+=1

# triggered when rotary dial is completed a number
def off_dialing():
    global pulse_count
    print("<<"+str(pulse_count))

    # easter egg to exit the forever loop.
    # crank the dial several times to cause more than 12 pulses
    if(pulse_count>12):
        exit()

    # didn't even reach 1 on the dial, didn't count
    if(pulse_count==0):
        return

    # 10 pulses == a zero.    
    if(pulse_count==10):
        pulse_count = 0
        
    # notify server of the digit dialed
    ws.send(str(pulse_count))
    # reset for the next turn
    pulse_count = 0    


# Server handles actions
def on_message(ws,msg):
    print(">>"+msg)

    # examples:
    # stop
    # play 0002
    # play 0004
    # volume 0008

    payload = msg.split()
    if(payload[0]=="stop"):
        stop_play()
    elif(payload[0]=="play"):
        dfplayer.write(binascii.a2b_hex('7eff060300'+payload[1]+'ef'))
    elif(payload[0]=="volume"):
        dfplayer.write(binascii.a2b_hex('7eff060600'+payload[1]+'ef'))
    


# connection to nodered server
ws = websocket.WebSocketApp("ws://10.10.10.10:1880/ws/telephone",on_message=on_message)
# event handlers from PI inputs
hook.when_pressed = on_hook
hook.when_released = off_hook
pulse.when_pressed = on_pulse
dialing.when_pressed = on_dialing
dialing.when_released = off_dialing

# on startup, stop any audio
stop_play()

# if the server closes the websocket connection (due to changes), reconnect
# dial more than 12 to really exit, or kill -9 <pid>
while True:
        ws.run_forever()
