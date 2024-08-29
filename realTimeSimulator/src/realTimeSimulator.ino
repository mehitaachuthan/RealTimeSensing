
#include "WiFi.h"
#include "PubSubClient.h"
#include "DHTesp.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"


// task handle for a task that sends data to MQTT server so that MQTT server can send to python visualization application
TaskHandle_t loopCheckTaskHandle = NULL;
// task handle for a task that reads from the sensors at fixed time intervals
TaskHandle_t readSensorsTaskHandle = NULL;

// store wifi connection info
String stMac;
char mac[50];
String ip;
char clientId[50];

// to help transmit/receive MQTT messages
WiFiClient espClient;
PubSubClient client(espClient);

// info to connect to MQTT server
const char* mqttServer = "broker.hivemq.com";
int port = 1883;

/*
Sensor Connections:

Temperature and Humidity - DHT Sensor: D32

Ultrasound Echo Pin : D25
Ultrasound Trigger Pin: D26

Photoresistor Sensor Pin: D35

*/
const int ULTRASOUND_ECHO_PIN = 25;
const int ULTRASOUND_TRIGGER_PIN = 26;

const int DHT_PIN = 32;
DHTesp dhtSensor;

const int PHOTORESISTOR_PIN = 35;
const float GAMMA = 0.7;
const float RL10 = 50;

// Chunk size for number of values to be considered for calculating average
const int MAX_LIST_SIZE = 10;

/*
For each sensor, store:
1. list of values (help calculate average)
2. index of position in list to add next value
3. previous value before the most recent read value in list (this is used in the filtering calculation)
4. previous low pass filter calculated value before the current last read
(used for filtering calculation)
After list filled, it is cleared and new batch is stored so helps to store the previous edge.
Also helps avoid recalculation with storage of previous values.
*/
float temperature_list[MAX_LIST_SIZE];
int temperature_list_index = 0;
float temperature_prev_edge_input_value = 0.0;
float temperature_prev_low_pass = 0.0;

float humidity_list[MAX_LIST_SIZE];
int humidity_list_index = 0;
float humidity_prev_edge_input_value = 0.0;
float humidity_prev_low_pass = 0.0;

float distance_list[MAX_LIST_SIZE];
int distance_list_index = 0;
float distance_prev_edge_input_value = 0.0;
float distance_prev_low_pass = 0.0;

float photoresistor_list[MAX_LIST_SIZE];
int photoresistor_list_index = 0;
float photoresistor_prev_edge_input_value = 0.0;
float photoresistor_prev_low_pass = 0.0;

/*
Setup serial output, set up sensor pins, initialize list, and setup wifi and MQTT connections.

Inputs: none
Returns: none
*/
void setup() {

  Serial.begin(115200);

  dhtSensor.setup(DHT_PIN, DHTesp::DHT22);

  // Ultrasound uses a pin to trigger the sending of ultrasonic waves and measures time to receive the echo
  // in the echo pin
  pinMode(ULTRASOUND_TRIGGER_PIN , OUTPUT);
  pinMode( ULTRASOUND_ECHO_PIN , INPUT );

  pinMode(PHOTORESISTOR_PIN , INPUT);

  for(int i = 0; i < MAX_LIST_SIZE; i++){
    temperature_list[i] = 0;
    humidity_list[i] = 0;
    distance_list[i] = 0;
    photoresistor_list[i] = 0;
  }

  // setup WiFi
  Serial.println("Initializing WiFi...");
  WiFi.mode(WIFI_STA);  
  Serial.println("Connecting to WiFi ");
  WiFi.begin("Wokwi-GUEST", "");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  ip = WiFi.localIP().toString();
  Serial.println(ip);
  Serial.println(WiFi.macAddress());
  stMac = WiFi.macAddress();
  stMac.replace(":", "_");
  Serial.println(stMac);

  // set up connection to MQTT server and the callback function
  client.setServer(mqttServer, port);

}

/*
Function to handle reconnection. Make sure connected before transmit/receive data.

Inputs: none
Returns: none
*/
void mqttReconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    long r = random(1000);
    sprintf(clientId, "clientId-%ld", r);
    if (client.connect(clientId)) {
      Serial.print(clientId);
      Serial.println(" connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

/*
Calculate parity: sum up digits in the data_part string, and decide
whether parity should be string of 0 or 1 based on which one added to sum
gives even number

Inputs:
    data_part: string that has the data for which parity needs to be calculated
Returns: 
    const char * : this is the string with the parity bit (0 or 1)
*/
const char* makeEvenParity( String data_part){
  int total_sum = 0;
  int digit_value = 0;

  for(int i = 0; i < data_part.length(); i++){
    // string may have characters other than digits like negative sign or decimal or letters so need to focus only on digits
      if (isDigit(data_part[i])){
          digit_value = int(data_part[i]);
          total_sum += digit_value;
      }
  }

  if (total_sum % 2 == 0){
      return "0";
  } else{
      return "1";
  }
}

/*
Compute the Low Pass Filtered value. Only look at the last added value to the list (last read value).
This is a generic function so can be used with diff sets of vars for diff sensors.
Send data packet, which has Start Bit, Data Portion, Parity Bit, and Stop Bit in order.
Send data packet about the filter type (l for low pass) and then data packet for the actual number.
Start Bit - #
Stop Bit - &
Data Packet format based on UART protocol

Inputs:
    cur_list: a sensor's list of values collected from reading
    cur_list_index: a sensor's next position to add value to list, this is used to find last added value
    store_prev_low_pass: second to last read value's low pass filter calculation
Returns: None
*/
void lowPassFilter(float* cur_list, int cur_list_index, float* store_prev_low_pass){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  float low_pass_processed_value = 0.0;

  // in the equation for low pass calculation, this is a parameter
  // alpha close to 1 means less or no filtering, close to 0 means more filtering
  float alpha = 0.5;
  float prev_low_pass_val = (*store_prev_low_pass);

  // send data packet that says it is a low pass filter type
  client.publish("transmit_sensors_collect_topic" , "#l0&" );
  
  low_pass_processed_value = alpha * cur_list[cur_list_index - 1];
  low_pass_processed_value += (1 - alpha)*prev_low_pass_val;

  // send actual low pass calculated value
  data_part = String( low_pass_processed_value , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );
  client.publish("transmit_sensors_collect_topic" , value_string );
  
  // store this low pass computation result as the previous low pass value for the next calculation
  (*store_prev_low_pass) = low_pass_processed_value;
}

/*
Compute the difference between the last read value and the second to last read value.
Only process and send data packet for last read value.
This is a generic function so can be used with diff sets of vars for diff sensors.
Data packet has Start Bit, Data Portion, Parity Bit, and Stop Bit in order.
Send data packet about the filter type (c for custom) and then data packet for the actual number.
Start Bit - #
Stop Bit - &
Data Packet format based on UART protocol

Inputs:
    cur_list: a sensor's list of values collected from reading
    cur_list_index: a sensor's next position to add value, this is used to find last added value
    store_prev_input: second to last read value
Returns: None
*/
void customFilter(float* cur_list, int cur_list_index, float* store_prev_input){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  float custom_processed_value = 0.0;
  // beta parameter is scaling of the difference result
  float beta = 1.0;
  int prev_input = 0;

  // send data packet that says it is a custom filter type
  client.publish("transmit_sensors_collect_topic" , "#c0&" );
  
  // use the previous value in the array if the current value has values before it or else use the stored previous value
  if((cur_list_index-1) > 0){
    custom_processed_value = beta * ( cur_list[cur_list_index - 1] - cur_list[cur_list_index-2] );
  } else {
    custom_processed_value = beta * ( cur_list[cur_list_index - 1] - (*store_prev_input) );
  }

  // send the actual custom filter difference number
  data_part = String( custom_processed_value , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );
  client.publish("transmit_sensors_collect_topic" , value_string );
}

/*
Compute the average of the full list. This function only will be called when list is full.
This is a generic function so can be used with diff var for diff sensors.
Send single data packet for average. 
Data packet has Start Bit, Data Portion, Parity Bit, and Stop Bit in order.
Send data packet about the filter type (a for average) and then data packet for the actual number.
Start Bit - #
Stop Bit - &
Data Packet format based on UART protocol

Inputs:
    cur_list: a sensor's list of values collected from reading
Returns: None
*/
void averageOperation(float* cur_list){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";
  float avg_val = 0.0;

  for(int i = 0; i < MAX_LIST_SIZE; i++){
    avg_val += cur_list[i];
  }
  avg_val /= MAX_LIST_SIZE;

  data_part = String( avg_val , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );

  // send data packet that says it is an average filter type
  client.publish("transmit_sensors_collect_topic" , "#a0&" );
  // send the data packet with the average number
  client.publish("transmit_sensors_collect_topic" , value_string );
}

/*
Send single data packet for the last read value of a sensor. Filter data by using the other functions.
This is a generic function so can be used with diff sets of vars for diff sensors.
Data packet has Start Bit, Data Portion, Parity Bit, and Stop Bit in order.
Send data packet about the filter type (o for original or unfiltered) and then data packet for the actual number.
Start Bit - #
Stop Bit - &
Data Packet format based on UART protocol

Inputs:
    cur_list: a sensor's list of values collected from reading
    cur_list_index: a sensor's next position to add value, this is used to find last added value
    store_prev_input: second to last value read
    store_prev_low_pass: second to last read value's low pass filter calculation
Returns: None
*/
void processChunkList(float* cur_list, int cur_list_index, float* store_prev_input, float* store_prev_low_pass){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  // send data packet that says it is the original or unfiltered type
  client.publish("transmit_sensors_collect_topic" , "#o0&" );

  // send the most recent value read
  data_part = String(cur_list[cur_list_index - 1] , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );
  client.publish("transmit_sensors_collect_topic" , value_string );
  
  // low pass filter
  lowPassFilter(cur_list, cur_list_index , store_prev_low_pass );
  // custom filter (difference)
  customFilter(cur_list, cur_list_index , store_prev_input );
  if(cur_list_index == MAX_LIST_SIZE){
    // only send the average after the chunk filled
    averageOperation(cur_list );
  }

  // store the most recent value read as the second to last read value for the calculations related to the next value to be processed
  (*store_prev_input) = cur_list[cur_list_index - 1];
}

/*
Clear data and reset the position holder for the next value to add to front of list
This is a generic function so can be used with diff sets of vars for diff sensors.

Inputs:
    cur_list: a sensor's list of values collected from reading
    cur_list_index: a sensor's next position to add value
Returns: None
*/
void flushList(float* cur_list, int* cur_list_index){
  // clear values
  for(int i = 0; i < MAX_LIST_SIZE; i++){
    cur_list[i] = 0;
  }
  
  // reset position to add
  (*cur_list_index) = 0;
  
}

/*
Add value read from a sensor to that sensor's list.
This is a generic function so can be used with diff sets of vars for diff sensors.

Inputs:
    cur_list: a sensor's list of values collected from reading
    cur_list_index: a sensor's next position to add value
    new_value: value to be added to list
Returns: None
*/
void addValueToList( float* cur_list , int* cur_list_index, float new_value ){
  
  // add if there is space
  // fullness is checked and flushing done at every iteration of the read sensors task so just skip or move on if not able to add currently 
  if( (*cur_list_index) < MAX_LIST_SIZE){
    cur_list[(*cur_list_index)] = new_value;
    (*cur_list_index) = (*cur_list_index) + 1;
  }
}

/*
Read temperature and humidity from DHT sensor

Inputs: None
Returns: None
*/
void readTemperatureAndHumidityFromSensor(){
  
  TempAndHumidity  data = dhtSensor.getTempAndHumidity();
  // celsius
  float temp = float(data.temperature);
  // percentage
  float humidity = float(data.humidity); 

  addValueToList( temperature_list , &temperature_list_index , temp );
  addValueToList( humidity_list , &humidity_list_index , humidity);

}

/*
Read time from Ultrasound sensor and calculate distance in cm

Inputs: None
Returns: None
*/
void readUltrasoundSensor(){

  // get the sensor ready to trigger
  digitalWrite(ULTRASOUND_TRIGGER_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(ULTRASOUND_TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  // initiate trigger pin to send ultrasonic waves
  digitalWrite(ULTRASOUND_TRIGGER_PIN, LOW);
  // read the time to get the echo back from the echo pin
  int duration = pulseIn(ULTRASOUND_ECHO_PIN, HIGH);
  // calculate distance
  float cm_distance = duration / 58; // cm

  addValueToList( distance_list , &distance_list_index , cm_distance);
  
}

/*
Read Photoresistor sensor value and caclulate illuminance value in lux

Inputs: None
Returns: None
*/
void readPhotoresistorSensor(){

  int analogValue = analogRead( PHOTORESISTOR_PIN );
  // convert analog value to voltage amount (max 5 V)
  float voltage = (analogValue / 4096.) * 5;
  float resistance = (2000 * voltage) / (1 - (voltage / 5) );
  // calculate illuminance (lux)
  float lux = pow((RL10 * 1e3 * pow(10, GAMMA)) / resistance, (1 / GAMMA));

  addValueToList( photoresistor_list , &photoresistor_list_index , lux );

}

/*
RTOS task that reads from each of the sensors once every second.
After reading all the sensors once, the task to send the data to the MQTT server
is notified and this task waits for it to be notified by the other task after that
task completes its actions. The lists are reset if become full.

Inputs: 
    pvParameter: task parameters
Returns: None
*/
void readSensors_task(void *pvParameter){

  TickType_t passed_ticks_count = 0;
  while(1){
    // get the task start tick count to calculate time to rewaken task after a fixed interval
    passed_ticks_count = xTaskGetTickCount();

    // from each sensor read a value and store in its list
    readTemperatureAndHumidityFromSensor();
    readUltrasoundSensor();
    readPhotoresistorSensor();

    // send signal to task that sends data to MQTT server
    xTaskNotifyGive( loopCheckTaskHandle );
    // block until notified by other task to continue
    ulTaskNotifyTake( pdTRUE, portMAX_DELAY );

    if(photoresistor_list_index >= MAX_LIST_SIZE){

      // clear all lists because all must have reached max since all updated together
      flushList(temperature_list , &temperature_list_index);
      flushList(humidity_list , &humidity_list_index);
      flushList(distance_list , &distance_list_index);
      flushList(photoresistor_list , &photoresistor_list_index);
    }

    // delay for a second
    xTaskDelayUntil(&passed_ticks_count , 1000U / portTICK_PERIOD_MS );
  }

  vTaskDelete( NULL );
}

/*
RTOS task that sends the data to an MQTT server to be sent to a visualization python application.
This task waits/blocks until notified from the task reading the sensors that all the sensors have been read once. 
Then this task sends the code related to the sensor type, and then send the unfiltered and filtered data
values. A done code 'X' is sent meaning that the bunch is finished. Finally, reading sensor task is notified
to read the sensors, since this task processing is done.

Inputs: 
    pvParameter: task parameters
Returns: None
*/
void loopCheckTask(void *pvParameters)
{

  while(1) {
    // block until reading of sensors once is done
    ulTaskNotifyTake( pdTRUE, portMAX_DELAY );

    // make sure that MQTT server connected
    if (!client.connected()) {
      mqttReconnect();
    }
    client.loop();

    /*
      Communication Protocol:
        For each sensor:
        a. Send the Sensor Type
        b. Send the Filter Type
        c. Send the data value
        ...[repeat for other sensors]
        Send the end of sequence code X
      * Note: each message is in the form of a data packet with a start bit, data portion, parity bit, and stop bit
    */

    // for each sensor: send the sensor type, then send the unfiltered and processed values
    client.publish("transmit_sensors_collect_topic" , "#T0&" );
    processChunkList( temperature_list , temperature_list_index, &temperature_prev_edge_input_value , &temperature_prev_low_pass );
    client.publish("transmit_sensors_collect_topic" , "#H0&" );
    processChunkList( humidity_list , humidity_list_index , &humidity_prev_edge_input_value , &humidity_prev_low_pass  );
    client.publish("transmit_sensors_collect_topic" , "#D0&" );
    processChunkList( distance_list , distance_list_index , &distance_prev_edge_input_value , &distance_prev_low_pass );
    client.publish("transmit_sensors_collect_topic" , "#P0&" );
    processChunkList( photoresistor_list , photoresistor_list_index , &photoresistor_prev_edge_input_value , &photoresistor_prev_low_pass );
    // send the code that says that the set of sensors data is done temporarily so that the visualizing application can temporarily stop expecting 
    // more data and update the visulization or plot
    client.publish("transmit_sensors_collect_topic" , "#X0&" );

    // notify the read sensors task to resume
    xTaskNotifyGive( readSensorsTaskHandle );
      
  }
}

/*
The main function. Does setup and initialization related to hardware.
Creates necessary RTOS tasks.

Inputs: 
    pvParameter: task parameters
Returns: None
*/
extern "C" void app_main()
{
  initArduino();

  setup();

  xTaskCreate(loopCheckTask, "loopTask", CONFIG_ARDUINO_LOOP_STACK_SIZE, NULL, 1 | portPRIVILEGE_BIT, &loopCheckTaskHandle);
  
  xTaskCreate(
    &readSensors_task,
    "readSensorsTask", 
    2048, 
    NULL, 
    1 | portPRIVILEGE_BIT,
    &readSensorsTaskHandle); 
  
}
