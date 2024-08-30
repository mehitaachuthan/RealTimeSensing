# RealTimeSensingProject

**Report**
[Project Flow Report](https://github.com/mehitaachuthan/RealTimeSensing/blob/main/report.pdf)

**Video**
[![Efficiency Discussion Video]()](https://drive.google.com/file/d/1qhB-Yg8pUYaj6Wv23vKdgha5nKxJcYgW/view?usp=sharing)

Clone the Git Repository

**Installation Instructions for the Simulation [instructions specific for vscode]**
1. Install the extension PlatformIO
2. In PIO Home tab > Library, install libraries: 'DHT sensor library for ESPx' and 'PubSubClient'
3. Get a license related to WokWi. The community license should be enough to run and test. (But the circuit diagram can not be modified with the community license.
   Use the wokwi online simulator to make changes to diagram.json and then copy over the code to that file in the project.)
5. Make addresses have single quotes in the wokwi.toml file and modify backslashes in path name according to system.
   Build once to get the address paths of the Binary file (.bin) and Linking file (.elf). Update the wokwi.toml file with the paths.
6. Clean and Build after each change (use the buttons on the top of vscode to Build and Clean).

**Installation Instructions for the Python Visualization Application**
1. Make a Python virtual environment.
2. Install the packages in requirements.txt
3. Run the 'realTimeVisualization.py' file

**Installation and Setup Instructions for the MQTT Server**
1. Install Eclipse Mosquitto
2. Install node-red
3. Run node-red in powershell or terminal in place where mosquitto is installed (depending on system being used). Open http://127.0.0.1:1880/ in a browser.
4. Set up the connection between MQTT In and MQTT Out nodes.

![alt text](https://github.com/mehitaachuthan/RealTimeSensing/blob/main/img/mqtt_diagram.PNG?raw=true)

5. Set up the server.

![alt text](https://github.com/mehitaachuthan/RealTimeSensing/blob/main/img/mqtt_server_setup.PNG?raw=true)

6. Set up the topics for input and output.

![alt text](https://github.com/mehitaachuthan/RealTimeSensing/blob/main/img/mqtt_in_topic.PNG?raw=true)
![alt text](https://github.com/mehitaachuthan/RealTimeSensing/blob/main/img/mqtt_out_topic.PNG?raw=true)


**Note:** For the application to work: node-red, the simulation, and the python script need to all be running
Simulation: Click play button on the diagram.json file in a separate vscode window. Simulation should start. Before starting simulation, close the Wokwi Simulator tab and start from diagram.json to get right initial values.
MQTT: Run node-red in powershell or terminal in place where mosquitto is installed
Visualization Python Script: Run the 'realTimeVisualization.py' file in a separate vscode window.
