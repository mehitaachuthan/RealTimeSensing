# RealTimeSensingProject

Clone the Git Repository

**Installation Instructions for the Simulation [instructions specific for vscode]**
1. Install the extension PlatformIO
2. In PIO Home tab > Library, install libraries: 'DHT sensor library for ESPx' and 'PubSubClient'
3. Get a license related to WokWi. The community license should be enough to run and test. (But the circuit diagram can not be modified with the community license.
   Use the wokwi online simulator to make changes to diagram.json and then copy over the code to that file in the project.)
5. Make addresses have single quotes in the wokwi.toml file and modify backslashes in path name according to system.
   Build once to get the address paths of the Binary file (.bin) and Linking file (.elf). Update the wokwi.toml file with the paths.
6. Clean and Build after each change (use the buttons on the top of vscode to Build and Clean). Then, click play button on the diagram.json file. Simulation should start.

**Installation Instructions for the Python Visualization Application**
1. Make a Python virtual environment.
2. Install the packages in requirements.txt
3. Run the 'realTimeVisualization.py' file
