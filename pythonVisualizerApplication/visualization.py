
from tkinter import *

import matplotlib
import matplotlib.lines

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk,
)

'''
class: VisualizationHandler

Plots lines of the data from sensor data collection and processing in real time
Displays averages of 10-value chunks

Inputs:
    window_input: tkinter object (top level window) 
    in_q: multiprocessing.Queue to receive sensor data after the data collection and processing to visualize
Attributes:
    window: [store input window_input]
    in_q: [store input in_q]
    avg_str: tkinter StringVar to store text to show
    textFrame: tkinter Frame to hold several widgets, but in this case the text string is placed here, helps expand in case want more Labels in it
    avg_label: tkinter Label to hold text with formatting options
    fig: Matplotlib Figure to hold graphs
    ax: 2d array to hold subplots related info
    canvas: tkinter object to embed matplotlib figure
    dict_line_coords_indices: store the row and col of the graph for the specific combination of sensor and filtering types
    dict_line_coords: store the line to be plotted on each graph for the specific combination of sensor and filtering types
    sensor_val_arrays : dictionary to store array of sensor values for each sensor and filter type
'''
class VisualizationHandler:

    def __init__(self, window_input, in_q):

        self.window = window_input
        self.in_q = in_q
        
        self.sensor_val_arrays = { "T" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{"y": np.array([0])} },
                                "H": { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{"y": np.array([0])} },
                                "D" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{ "y": np.array([0])} },
                                "P" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{ "y": np.array([0])} } }
        
        # display average values 
        self.avg_str = StringVar()
        self.avg_str.set("Chunk 10 Avgs - Avg Temp (C): -"  
                        + "    Avg Humidity (%): -"
                        + "    Avg Dist (cm): -"
                        + "    Avg Illuminance (lux): -" )
        
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
        self.ax = self.fig.subplots(4, 4)
        # pad with extra values ranges to show on the subplot or else confused with edge of subplot
        for k in range(0,4):
            # temperature: -40 to 80 degrees celsuis
            self.ax[0,k].set_xlim(0, 10)
            self.ax[0,k].set_ylim(-45, 85)
        self.ax[0,2].set_xlim(0, 10)
        self.ax[0,2].set_ylim(-125, 125)
        for k in range(0,4):
            # humidity: 0 to 100 %
            self.ax[1,k].set_xlim(0, 10)
            self.ax[1,k].set_ylim(-5, 105)
        self.ax[1,2].set_xlim(0, 10)
        self.ax[1,2].set_ylim(-105, 105)
        for k in range(0,4):
            # distance: 2 to 400 cm
            self.ax[2,k].set_xlim(0, 10)
            self.ax[2,k].set_ylim( 0 , 402 )
        self.ax[2,2].set_xlim(0, 10)
        self.ax[2,2].set_ylim(-405, 405)
        for k in range(0,4):
            # photoresistance: 0.1 to 100k lux
            self.ax[3,k].set_xlim(0, 10)
            self.ax[3,k].set_ylim( -5 , 100005 )
        self.ax[3,2].set_xlim(0, 10)
        self.ax[3,2].set_ylim(-100005, 100005)

        # label the rows and columns
        cols = ['{}'.format(col) for col in ["Original" , "Low Pass Filter" , "Custom Filter (Difference)" , "10 Values Chunk Average" ]]
        rows = ['{}'.format(row) for row in ['Temperature (C)', 'Humidity (%)', 'Distance (cm)', 'Photoresistor (Lux)' ]]
        for ax, col in zip(self.ax[0,:], cols):
            ax.set_title(col)

        for ax, row in zip(self.ax[:,0], rows):
            ax.set_ylabel(row, rotation=90, size='medium')

        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side='bottom', fill='both', expand=1)
        self.canvas._tkcanvas.pack(side='top', fill='both', expand=1)
        
        # save line information to update visualization
        self.dict_line_coords = { "T" : { "o": matplotlib.lines.Line2D([0],[0]), "l": matplotlib.lines.Line2D([0],[0]) , "c": matplotlib.lines.Line2D([0],[0]) , "a": matplotlib.lines.Line2D([0],[0]) },
                                "H": { "o": matplotlib.lines.Line2D([0],[0]), "l": matplotlib.lines.Line2D([0],[0]) , "c": matplotlib.lines.Line2D([0],[0]), "a": matplotlib.lines.Line2D([0],[0]) },
                                "D" : { "o": matplotlib.lines.Line2D([0],[0]), "l": matplotlib.lines.Line2D([0],[0]) , "c": matplotlib.lines.Line2D([0],[0]), "a": matplotlib.lines.Line2D([0],[0])  },
                                "P" : { "o": matplotlib.lines.Line2D([0],[0]), "l": matplotlib.lines.Line2D([0],[0]) , "c": matplotlib.lines.Line2D([0],[0]), "a": matplotlib.lines.Line2D([0],[0])  } }
        
        # store how to access the specific subplot
        self.dict_line_coords_indices = { "T" : { "o": {"index_row": 0 , "index_col": 0}, "l": {"index_row": 0 , "index_col": 1} , "c": {"index_row": 0 , "index_col": 2}, "a": {"index_row": 0 , "index_col": 3} },
                                "H": { "o": {"index_row": 1 , "index_col": 0}, "l": {"index_row": 1 , "index_col": 1} , "c": {"index_row": 1 , "index_col": 2}, "a": {"index_row": 1 , "index_col": 3} },
                                "D" : { "o": {"index_row": 2 , "index_col": 0} , "l": {"index_row": 2 , "index_col": 1} , "c": {"index_row": 2 , "index_col": 2}, "a": {"index_row": 2 , "index_col": 3} },
                                "P" : { "o": {"index_row": 3 , "index_col": 0} , "l": {"index_row": 3 , "index_col": 1} , "c": {"index_row": 3 , "index_col": 2}, "a": {"index_row": 3 , "index_col": 3} } }
        
        # initially, plot (0,0) for all the lines in order to have line show up after first data point received since need at least two points for line to be drawn
        for cur_key_sensor_type in self.dict_line_coords_indices.keys():
            for cur_key_filter_type in self.dict_line_coords_indices[cur_key_sensor_type].keys():
                self.dict_line_coords[cur_key_sensor_type][cur_key_filter_type], = self.ax[ self.dict_line_coords_indices[cur_key_sensor_type][cur_key_filter_type]["index_row"] , self.dict_line_coords_indices[cur_key_sensor_type][cur_key_filter_type]["index_col"] ].plot([0], [0])

    '''
    Update the Subplots and Data Text Display based on the data received through a queue from the data collection and processing process
    
    Inputs: None
    Returns: None
    '''
    def updatePlot(self):

        try:
            # check if one batch of sensor data is at least read, processed, and available
            # this is non-blocking so will generate exception
            self.sensor_val_arrays = self.in_q.get_nowait()

            # update the array of x and y coordinate data to be drawn
            for cur_sensor_type in self.dict_line_coords.keys():
                for cur_filter_type in self.dict_line_coords[cur_sensor_type].keys():
                        # find position of the corresponding subplot
                        index_row = self.dict_line_coords_indices[cur_sensor_type][cur_filter_type]["index_row"]
                        index_col = self.dict_line_coords_indices[cur_sensor_type][cur_filter_type]["index_col"]
                        # x data is just starting from 0 to match the amount of y-values and is just to mark ticks on graph, not represent time or anything else
                        new_x_data = np.arange( len( self.sensor_val_arrays[cur_sensor_type][cur_filter_type]["y"] ) )
                        self.dict_line_coords[cur_sensor_type][cur_filter_type].set_xdata( new_x_data )
                        self.dict_line_coords[cur_sensor_type][cur_filter_type].set_ydata(self.sensor_val_arrays[cur_sensor_type][cur_filter_type]["y"])
                        self.ax[index_row,index_col].draw_artist( self.dict_line_coords[cur_sensor_type][cur_filter_type] )
            
            if len(self.sensor_val_arrays["P"]["a"]["y"]) > 0:
                # Update the text display with the last average if exists
                self.avg_str.set("Chunk 10 Avgs : Avg Temp (C): " + str(self.sensor_val_arrays["T"]["a"]["y"][-1]) 
                            + "    Avg Humidity (%): " + str(self.sensor_val_arrays["H"]["a"]["y"][-1])
                            + "    Avg Dist (cm): " + str(self.sensor_val_arrays["D"]["a"]["y"][-1])
                            + "    Avg Illuminance (lux): " + str(self.sensor_val_arrays["P"]["a"]["y"][-1]) )

            self.canvas.draw()

            # update every tenth of a second
            self.window.after(100,self.updatePlot)
        except:
            # triggered mainly since waiting for data from queue is non-blocking, so can just continue to next time update called
            self.window.after(100,self.updatePlot)