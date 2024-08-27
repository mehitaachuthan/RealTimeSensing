
from queue import Queue
from threading import Thread

import matplotlib.animation as animation
import matplotlib.lines
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import multiprocessing
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
import tkinter
from tkinter import *
import numpy as np
import paho.mqtt.client as paho

from paho import mqtt

class VisualizationHandler:

    def __init__(self, window_input, out_q):

        self.window = window_input
        self.out_q = out_q

        self.sensor_val_arrays = { "T" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "H": { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "D" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "P" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" } }
        
        self.avg_str = StringVar()
        self.avg_str.set("Chunk 10 Avgs - Avg Temp (C): " + self.sensor_val_arrays["T"]["a"] 
                        + "    Avg Humidity (%): " + self.sensor_val_arrays["H"]["a"]
                        + "    Avg Dist (cm): " + self.sensor_val_arrays["D"]["a"] 
                        + "    Avg Illuminance (lux): " + self.sensor_val_arrays["P"]["a"])
        
        self.textFrame = Frame(self.window, bg="white", height=10)
        self.textFrame.pack(side="top" , fill="x", expand=False)

        self.avg_label = Label(master=self.textFrame, 
                 textvariable=self.avg_str,     
                 bg="lightblue",                                                  
                 font=("Arial", 12, "bold"),    
                 fg="black",                         
                 justify='center',    
                 relief='raised',                
                 wraplength=1000     
                )
        self.avg_label.pack()

        self.fig = plt.figure(figsize=(18,10))
        self.ax = self.fig.subplots(4, 3)
        for k in range(0,2):
            # temperature: -40 to 80 degrees celsuis
            self.ax[0,k].set_xlim(1, 10)
            self.ax[0,k].set_ylim(-45, 85)
        self.ax[0,2].set_xlim(1, 10)
        self.ax[0,2].set_ylim(-125, 125)
        for k in range(0,2):
            # humidity: 0 to 100 %
            self.ax[1,k].set_xlim(1, 10)
            self.ax[1,k].set_ylim(-5, 105)
        self.ax[1,2].set_xlim(1, 10)
        self.ax[1,2].set_ylim(-105, 105)
        for k in range(0,2):
            # distance: 2 to 400 cm
            self.ax[2,k].set_xlim(1, 10)
            self.ax[2,k].set_ylim( 0 , 402 )
        self.ax[2,2].set_xlim(1, 10)
        self.ax[2,2].set_ylim(-405, 405)
        for k in range(0,2):
            # photoresistance: 0.1 to 100k lux
            self.ax[3,k].set_xlim(1, 10)
            self.ax[3,k].set_ylim( -5 , 100005 )
        self.ax[3,2].set_xlim(1, 10)
        self.ax[3,2].set_ylim(-100005, 100005)

        cols = ['{}'.format(col) for col in ["Original" , "Low Pass Filter" , "Custom Filter (Difference)" ]]
        rows = ['{}'.format(row) for row in ['Temperature (C)', 'Humidity (%)', 'Distance (cm)', 'Photoresistor (Lux)']]
        for ax, col in zip(self.ax[0,:], cols):
            ax.set_title(col)

        for ax, row in zip(self.ax[:,0], rows):
            ax.set_ylabel(row, rotation=90, size='medium')

        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='bottom', fill='both', expand=1)
        self.canvas._tkcanvas.pack(side='top', fill='both', expand=1)
        
        self.dict_line_coords = { "T" : { "o": matplotlib.lines.Line2D([],[]), "l": matplotlib.lines.Line2D([],[]) , "c": matplotlib.lines.Line2D([],[]) },
                                "H": { "o": matplotlib.lines.Line2D([],[]), "l": matplotlib.lines.Line2D([],[]) , "c": matplotlib.lines.Line2D([],[]) },
                                "D" : { "o": matplotlib.lines.Line2D([],[]), "l": matplotlib.lines.Line2D([],[]) , "c": matplotlib.lines.Line2D([],[])  },
                                "P" : { "o": matplotlib.lines.Line2D([],[]), "l": matplotlib.lines.Line2D([],[]) , "c": matplotlib.lines.Line2D([],[])  } }
        self.dict_line_coords_indices = { "T" : { "o": {"index_row": 0 , "index_col": 0}, "l": {"index_row": 0 , "index_col": 1} , "c": {"index_row": 0 , "index_col": 2} },
                                "H": { "o": {"index_row": 1 , "index_col": 0}, "l": {"index_row": 1 , "index_col": 1} , "c": {"index_row": 1 , "index_col": 2} },
                                "D" : { "o": {"index_row": 2 , "index_col": 0} , "l": {"index_row": 2 , "index_col": 1} , "c": {"index_row": 2 , "index_col": 2} },
                                "P" : { "o": {"index_row": 3 , "index_col": 0} , "l": {"index_row": 3 , "index_col": 1} , "c": {"index_row": 3 , "index_col": 2} } }
        
        for cur_key_sensor_type in self.dict_line_coords_indices.keys():
            for cur_key_filter_type in self.dict_line_coords_indices[cur_key_sensor_type].keys():
                self.dict_line_coords[cur_key_sensor_type][cur_key_filter_type], = self.ax[ self.dict_line_coords_indices[cur_key_sensor_type][cur_key_filter_type]["index_row"] , self.dict_line_coords_indices[cur_key_sensor_type][cur_key_filter_type]["index_col"] ].plot([], [])

    def updatePlot(self):

        try:
            self.sensor_val_arrays = self.out_q.get_nowait()

            print(self.sensor_val_arrays)

            for cur_sensor_type in self.dict_line_coords.keys():
                for cur_filter_type in self.dict_line_coords[cur_sensor_type].keys():
                    if type(self.sensor_val_arrays[cur_sensor_type][cur_filter_type]) is dict:
                        index_row = self.dict_line_coords_indices[cur_sensor_type][cur_filter_type]["index_row"]
                        index_col = self.dict_line_coords_indices[cur_sensor_type][cur_filter_type]["index_col"]
                        self.dict_line_coords[cur_sensor_type][cur_filter_type].set_xdata(self.sensor_val_arrays[cur_sensor_type][cur_filter_type]["x"])
                        self.dict_line_coords[cur_sensor_type][cur_filter_type].set_ydata(self.sensor_val_arrays[cur_sensor_type][cur_filter_type]["y"])
                        self.ax[index_row,index_col].draw_artist( self.dict_line_coords[cur_sensor_type][cur_filter_type] )
            
            self.avg_str.set("Chunk 10 Avgs - Avg Temp (C): " + self.sensor_val_arrays["T"]["a"] 
                        + "    Avg Humidity (%): " + self.sensor_val_arrays["H"]["a"]
                        + "    Avg Dist (cm): " + self.sensor_val_arrays["D"]["a"] 
                        + "    Avg Illuminance (lux): " + self.sensor_val_arrays["P"]["a"])

            self.canvas.draw()
            self.window.after(100,self.updatePlot)
        except:
            print("except")
            self.window.after(100,self.updatePlot)

class UARTDataHandler:

    def __init__(self , output_queue):
        self.current_sensor_type = ""
        self.current_filter_type = ""
        self.isAvgComing = False
        self.output_queue = output_queue
        self.sensor_val_arrays = { "T" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "H": { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "D" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" },
                                "P" : { "o": {"x" : np.array([]), "y": np.array([])}, "l": {"x" : np.array([]), "y": np.array([])} , "c": {"x" : np.array([]), "y": np.array([])} , "a":"0" } }
        self.max_num_points_shown = 10

    def isEvenParity(self, data_part , parity):
        total_sum = 0
        if parity.isdigit():
            parity = int(parity)
        else:
            return False
        for i in range(0 , len(data_part)):
            if data_part[i].isdigit():
                digit_value = int(data_part[i])
                total_sum += digit_value
        total_sum += parity
        if total_sum % 2 == 0:
            return True
        else:
            return False
    
    def processPoint(self , current_sensor_type , current_filter_type, float_data):
        
        if len(self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"]) == 0:
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"] , np.array(1) )
        elif len(self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"]) < self.max_num_points_shown:
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"] , np.array(self.sensor_val_arrays[current_sensor_type][current_filter_type]["x"][-1] + 1) )
        else:
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"][1:]
        self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] , np.array(float_data) )

    def on_message_receive(self, client , user_data , message_carrier ):

        topic_name = str(message_carrier.topic)
        packet = str(message_carrier.payload)

        # packet comes in format b'........' --> need to remove the b and ' '
        packet = packet[2:-1]

        if topic_name == "receive_collection_script_topic":
            # UART packet format: first is the start bit, then data bits, then second to last bit is parity bit, then last bit is stop bit
            # start bit: #
            # number to add to make sum of numbers in float value even
            # stop bit: &
            start_bit = packet[0]
            stop_bit = packet[-1]
            parity_bit = packet[-2]
            data_portion = packet[1:-2]

            if start_bit == "#" and stop_bit == "&":
                if self.isEvenParity(data_portion , parity_bit):
                    # this data packet is fine
                    try:
                        # check if it is a code
                        if len(data_portion) == 1 and (data_portion == "T" or data_portion == "H" or data_portion == "D" or data_portion == "P"):
                            self.current_sensor_type = data_portion
                            if self.isAvgComing:
                                self.isAvgComing = False
                        elif len(data_portion) == 1 and (data_portion == "l" or data_portion == "c" or data_portion == "o"):
                            self.current_filter_type = data_portion
                            if self.isAvgComing:
                                self.isAvgComing = False
                        elif len(data_portion) == 1 and data_portion == "a":
                            self.isAvgComing = True
                        elif len(data_portion) == 1 and data_portion == "X":
                            # end of a sequence
                            self.output_queue.put(self.sensor_val_arrays)
                            if self.isAvgComing:
                                self.isAvgComing = False
                        else:
                            float_data = float(data_portion)
                            #data_dict = { 'current_sensor_type' : self.current_sensor_type , 'current_filter_type' : self.current_filter_type , 'float_data' : float_data }

                            if self.isAvgComing:
                                self.isAvgComing = False
                                self.sensor_val_arrays[self.current_sensor_type]["a"] = str(float_data)
                            else:
                                self.processPoint( self.current_sensor_type , self.current_filter_type , float_data )
                    except:
                        # just skip
                        pass

def data_processing_producer(in_q): 
    broker_address = "broker.hivemq.com"
    port = 1883

    dh = UARTDataHandler(in_q)
    client = paho.Client()
    client.connect( broker_address , port=port )
    client.subscribe("receive_collection_script_topic")
    client.on_message = dh.on_message_receive

    while True:
        if client.is_connected() is False:
            client.connect( broker_address , port=port )
            client.subscribe("receive_collection_script_topic")
            client.on_message = dh.on_message_receive
        client.loop()

if __name__ == '__main__':

    q = multiprocessing.Queue()

    data_processor=multiprocessing.Process(None,data_processing_producer,args=(q,))
    #t2 = Thread(target = data_visualization_consumer, args =(q, )) 
    data_processor.start()
    #t2.start() 
    
    window=tkinter.Tk()
    visualizer = VisualizationHandler(window , q)

    visualizer.updatePlot()

    window.mainloop()

