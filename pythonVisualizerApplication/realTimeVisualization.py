

import matplotlib
import matplotlib.lines

matplotlib.use('TkAgg')
import multiprocessing
import tkinter
from tkinter import *

import paho.mqtt.client as paho

from uart_handler import UARTDataHandler
from visualization import VisualizationHandler

'''
Process that connects to MQTT server and is ready to receive data

Inputs: 
    in_q: multiprocessing.Queue to transfer data between (1) data handling and (2) visualization processes
'''
def data_processing_producer(in_q): 
    # credentials to connect to MQTT server
    broker_address = "broker.hivemq.com"
    port = 1883

    # handler has callback function
    dh = UARTDataHandler(in_q)

    client = paho.Client()
    client.connect( broker_address , port=port )
    # connect to the specific topic (like channel) to receive
    client.subscribe("receive_collection_script_topic")
    # set the callback function to handle when message received
    client.on_message = dh.on_message_receive

    # this process continues to stay connected and listen to MQTT server
    while True:
        if client.is_connected() is False:
            client.connect( broker_address , port=port )
            client.subscribe("receive_collection_script_topic")
            client.on_message = dh.on_message_receive
        client.loop()

'''
Main Process with GUI
'''
if __name__ == '__main__':

    # inter-process queue to transfer data between (1) data handling and (2) visualization processes
    q = multiprocessing.Queue()

    # data collection and handling process should also have access to the inter-process queue
    data_processor=multiprocessing.Process(None,data_processing_producer,args=(q,))
    data_processor.start()

    # tkiner main window
    window=tkinter.Tk()
    visualizer = VisualizationHandler(window , q)

    # call update, subsequent calls called from itself after a time interval
    visualizer.updatePlot()

    # GUI main loop, will iterate infinitely unless stop the application
    window.mainloop()

