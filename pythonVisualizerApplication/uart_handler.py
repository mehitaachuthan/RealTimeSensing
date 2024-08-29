
import numpy as np

'''
class: UARTDataHandler

Handles the data sent from the sensors simulation
Use principles similar to UART protocol

Input:
    output_queue : multiprocessing.Queue to transfer sensor data between data collection and visualizatino processes
Attributes:
    current_sensor_type : string to store the sensor type letter code
    current_filter_type : string to store the filter type letter code
    output_queue : store input output_queue
    sensor_val_arrays : dictionary to store array of sensor values for each sensor and filter type
    max_num_points_shown : max number of data points to store and show per sensor and filter
'''
class UARTDataHandler:

    def __init__(self , output_queue):
        self.current_sensor_type = ""
        self.current_filter_type = ""
        self.output_queue = output_queue

        # Sensor Types: "T" (temp), "H" (humidity), "D" (distance) , "P" (photoresistor)
        # Filter Types: "o" (original, unfiltered), "l" (low pass filter), "c" (custom filter (difference)), "a" (average of 10 values chunk)
        self.sensor_val_arrays = { "T" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{"y": np.array([0])} },
                                "H": { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{"y": np.array([0])} },
                                "D" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{ "y": np.array([0])} },
                                "P" : { "o": { "y": np.array([0])}, "l": { "y": np.array([0])} , "c": { "y": np.array([0])} , "a":{ "y": np.array([0])} } }
        
        # one more than n (10 in this case) since need at least two points per line so want to start from 0 so that first point is plotted
        self.max_num_points_shown = 11

    '''
    Check if the input string of digits has even parity
    Even parity implemented here is if the sum of the digits in the string is even
    The parity digit is "0" or "1" and makes the sum of the digits from the input string even

    Inputs: 
        data_part : input string expected to have digits
        parity : string bit expected to help check even parity
    
    Return:
        Boolean : whether even parity
    '''
    def isEvenParity(self, data_part , parity):

        total_sum = 0

        # make sure that the parity string is 1 digit
        if len( parity ) == 1 and parity.isdigit():
            parity = int(parity)
        else:
            return False
        for i in range(0 , len(data_part)):
            # sum up only digits, there could be decimal or negative sign so avoid those
            if data_part[i].isdigit():
                digit_value = int(data_part[i])
                total_sum += digit_value
        total_sum += parity
        if total_sum % 2 == 0:
            return True
        else:
            return False
    
    '''
    Save the data received into the correct array based on the type of sensor and type of filtering (data processing)
    Separate graphs for each combination of sensor and filtering type

    Inputs: None
    Returns: None
    '''
    def processPoint(self , current_sensor_type , current_filter_type, float_data):
        
        if len(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"]) == 0:
            # case where no elements in list, start from 0
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] , np.array(0) )
        elif len(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"]) < self.max_num_points_shown:
            # case where max num points not filled
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] , np.array(float_data) )
        else:
            # case where max num points filled so slide data to include new point and maintain max num points in array
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"][1:]
            self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] = np.append(self.sensor_val_arrays[current_sensor_type][current_filter_type]["y"] , np.array(float_data) )

    '''
    Handle when MQTT message received from the MQTT server used to connect to the simulation
    This is the receive side of UART. Each message is a single data packet.

    Inputs:
        [not used, from internal callback specification] client
        [not used, from internal callback specification] user_data
        message_carrier: MQTT topic for which message received and the payload info
    '''
    def on_message_receive(self, client , user_data , message_carrier ):

        topic_name = str(message_carrier.topic)
        packet = str(message_carrier.payload)

        # packet comes in format b'........' so need to remove the b and ' '
        packet = packet[2:-1]

        # MQTT topic (like specific channel of communication)
        if topic_name == "receive_collection_script_topic":
            # UART packet format: first is the start bit, then data bits, then second to last bit is parity bit, then last bit is stop bit
            # start bit: #
            # data_portion: coulbe a letter code or a number
            # parity: for checking
            # stop bit: &
            
            start_bit = packet[0]
            stop_bit = packet[-1]
            parity_bit = packet[-2]
            data_portion = packet[1:-2]

            if start_bit == "#" and stop_bit == "&":
                # error check with parity before processing data packet
                if self.isEvenParity(data_portion , parity_bit):
                    try:
                        if len(data_portion) == 1 and (data_portion == "T" or data_portion == "H" or data_portion == "D" or data_portion == "P"):
                            # sensors: temp (T), humidity (H), distance (D), photoresistor (P)
                            self.current_sensor_type = data_portion
                        elif len(data_portion) == 1 and (data_portion == "l" or data_portion == "c" or data_portion == "o" or data_portion == "a"):
                            # filtering: original unfiltered (o), low pass (l), custom filter difference (c), average (a)
                            self.current_filter_type = data_portion
                        elif len(data_portion) == 1 and data_portion == "X":
                            # data packet X means end of a sequence of data packets
                            # signifies end of a set of data collection and is used to signal the updating of visualization
                            self.output_queue.put(self.sensor_val_arrays)
                        else:
                            # case where data is a number
                            float_data = float(data_portion)
                            # should have sensor type and filtering type set before this
                            # no error message since want to continuously keep receiving data, ignore wrong sequence
                            if self.current_sensor_type != "" and self.current_filter_type != "":
                                self.processPoint( self.current_sensor_type , self.current_filter_type , float_data )
                    except:
                        # just skip, move on to the next data packet if not match format
                        pass
