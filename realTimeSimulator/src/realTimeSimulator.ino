// Learn about the ESP32 WiFi simulation in
// https://docs.wokwi.com/guides/esp32-wifi

#include "WiFi.h"
#include "PubSubClient.h"
#include "DHTesp.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// function prototypes
void readTemperatureAndHumidityFromSensor_task(void *pvParameter);
void readUltrasoundSensor_task(void *pvParameter);
void readPhotoresistorSensor_task(void *pvParameter);

TaskHandle_t loopCheckTaskHandle = NULL;
TaskHandle_t readSensorsTaskHandle = NULL;

String stMac;
char mac[50];
String ip;
char clientId[50];

const char* mqttServer = "broker.hivemq.com";
int port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

const int ledPin = 2;

const int ULTRASOUND_ECHO_PIN = 25;
const int ULTRASOUND_TRIGGER_PIN = 26;

const int DHT_PIN = 32;
DHTesp dhtSensor;

const int PHOTORESISTOR_PIN = 35;
const float GAMMA = 0.7;
const float RL10 = 50;

const int MAX_LIST_SIZE = 10;

float temperature_list[MAX_LIST_SIZE];
int temperature_list_index = 0;
float temperature_prev_edge_input_value = 0.0;
float temperature_prev_edge_low_pass = 0.0;

float humidity_list[MAX_LIST_SIZE];
int humidity_list_index = 0;
float humidity_prev_edge_input_value = 0.0;
float humidity_prev_edge_low_pass = 0.0;

float distance_list[MAX_LIST_SIZE];
int distance_list_index = 0;
float distance_prev_edge_input_value = 0.0;
float distance_prev_edge_low_pass = 0.0;

float photoresistor_list[MAX_LIST_SIZE];
int photoresistor_list_index = 0;
float photoresistor_prev_edge_input_value = 0.0;
float photoresistor_prev_edge_low_pass = 0.0;



void setup() {

  Serial.begin(115200);

  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin , LOW);

  dhtSensor.setup(DHT_PIN, DHTesp::DHT22);

  pinMode(ULTRASOUND_TRIGGER_PIN , OUTPUT);
  pinMode( ULTRASOUND_ECHO_PIN , INPUT );

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

  client.setServer(mqttServer, port);
  client.setCallback(callback);

}

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

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String stMessage = "";
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    stMessage += (char)message[i];
  }
  Serial.println();

  Serial.print("Message size: ");
  Serial.println(length);
  Serial.println();
  Serial.println("-----------------------");
  Serial.println(stMessage);
}

const char* makeEvenParity( String data_part){
  int total_sum = 0;
  int digit_value = 0;
  for(int i = 0; i < data_part.length(); i++){
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

void lowPassFilter(float* cur_list, int cur_list_index, float* store_prev_low_pass){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  float low_pass_processed_value = 0.0;
  float alpha = 0.5;
  float prev_low_pass_val = (*store_prev_low_pass);

  client.publish("transmit_sensors_collect_topic" , "#l0&" );
  
  low_pass_processed_value = alpha * cur_list[cur_list_index - 1];
  low_pass_processed_value += (1 - alpha)*prev_low_pass_val;

  data_part = String( low_pass_processed_value , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );

  client.publish("transmit_sensors_collect_topic" , value_string );

  prev_low_pass_val = low_pass_processed_value;
  
  (*store_prev_low_pass) = prev_low_pass_val;
}

void customFilter(float* cur_list, int cur_list_index, float* store_prev_input){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  float custom_processed_value = 0.0;
  float beta = 1.0;
  int prev_input = 0;

  client.publish("transmit_sensors_collect_topic" , "#c0&" );
  
  if((cur_list_index-1) > 0){
    custom_processed_value = beta * ( cur_list[cur_list_index - 1] - cur_list[cur_list_index-2] );
  } else {
    custom_processed_value = beta * ( cur_list[cur_list_index - 1] - (*store_prev_input) );
  }

  data_part = String( custom_processed_value , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );

  client.publish("transmit_sensors_collect_topic" , value_string );
}

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

  client.publish("transmit_sensors_collect_topic" , "#a0&" );
  client.publish("transmit_sensors_collect_topic" , value_string );
}

void processChunkList(float* cur_list, int cur_list_index, float* store_prev_input, float* store_prev_low_pass){
  char value_string[10];
  const char* parity_part = "0";
  String data_part = "";

  client.publish("transmit_sensors_collect_topic" , "#o0&" );

  // just send the latest
  data_part = String(cur_list[cur_list_index - 1] , 2);
  parity_part = makeEvenParity( data_part );
  sprintf( value_string , "#%s%s&" , data_part, parity_part );
  client.publish("transmit_sensors_collect_topic" , value_string );
  
  lowPassFilter(cur_list, cur_list_index , store_prev_low_pass );
  customFilter(cur_list, cur_list_index , store_prev_input );
  if(cur_list_index == MAX_LIST_SIZE){
    // only send the average after the chunk of ten filled
    averageOperation(cur_list );
  }
  (*store_prev_input) = cur_list[cur_list_index - 1];
}

void flushList(float* cur_list, int* cur_list_index){
  // clear
  for(int i = 0; i < MAX_LIST_SIZE; i++){
    cur_list[i] = 0;
  }
  
  (*cur_list_index) = 0;
  
}

void addValueToList( float* cur_list , int* cur_list_index, float new_value ){
  
  if( (*cur_list_index) < MAX_LIST_SIZE){
    cur_list[(*cur_list_index)] = new_value;
    (*cur_list_index) = (*cur_list_index) + 1;
  }
}

void readTemperatureAndHumidityFromSensor_task(){
  
  TempAndHumidity  data = dhtSensor.getTempAndHumidity();
  float temp = float(data.temperature); // celsius
  float humidity = float(data.humidity); // percentage

  addValueToList( temperature_list , &temperature_list_index , temp );
  addValueToList( humidity_list , &humidity_list_index , humidity);

}

void readUltrasoundSensor_task(){

  digitalWrite(ULTRASOUND_TRIGGER_PIN, LOW);
  delayMicroseconds(5);
  digitalWrite(ULTRASOUND_TRIGGER_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASOUND_TRIGGER_PIN, LOW);
  int duration = pulseIn(ULTRASOUND_ECHO_PIN, HIGH);
  float cm_distance = duration / 58; // cm
  //Serial.print("Distance in inches: ");
  //Serial.println(duration / 148);

  addValueToList( distance_list , &distance_list_index , cm_distance);
  
}

void readPhotoresistorSensor_task(){

  int analogValue = analogRead( PHOTORESISTOR_PIN );
  float voltage = (analogValue / 4096.) * 5;
  float resistance = (2000 * voltage) / (1 - (voltage / 5) );
  float lux = pow((RL10 * 1e3 * pow(10, GAMMA)) / resistance, (1 / GAMMA));

  addValueToList( photoresistor_list , &photoresistor_list_index , lux );

}

void readSensors_task(void *pvParameter){

  TickType_t passed_ticks_count = 0;
  while(1){
    passed_ticks_count = xTaskGetTickCount();

    readTemperatureAndHumidityFromSensor_task();
    readUltrasoundSensor_task();
    readPhotoresistorSensor_task();

    // send signal to process and send data after each single reading
    xTaskNotifyGive( loopCheckTaskHandle );
    ulTaskNotifyTake( pdTRUE, portMAX_DELAY );

    if(photoresistor_list_index >= MAX_LIST_SIZE){

      // clear lists if all must have reached max
      flushList(temperature_list , &temperature_list_index);
      flushList(humidity_list , &humidity_list_index);
      flushList(distance_list , &distance_list_index);
      flushList(photoresistor_list , &photoresistor_list_index);
    }

    // delay for half a second
    xTaskDelayUntil(&passed_ticks_count , 1000U / portTICK_PERIOD_MS );
  }

  vTaskDelete( NULL );
}

void loopCheckTask(void *pvParameters)
{

  while(1) {
    ulTaskNotifyTake( pdTRUE, portMAX_DELAY );

    if (!client.connected()) {
      mqttReconnect();
    }
    client.loop();

    client.publish("transmit_sensors_collect_topic" , "#T0&" );
    processChunkList( temperature_list , temperature_list_index, &temperature_prev_edge_input_value , &temperature_prev_edge_low_pass );
    client.publish("transmit_sensors_collect_topic" , "#H0&" );
    processChunkList( humidity_list , humidity_list_index , &humidity_prev_edge_input_value , &humidity_prev_edge_low_pass  );
    client.publish("transmit_sensors_collect_topic" , "#D0&" );
    processChunkList( distance_list , distance_list_index , &distance_prev_edge_input_value , &distance_prev_edge_low_pass );
    client.publish("transmit_sensors_collect_topic" , "#P0&" );
    processChunkList( photoresistor_list , photoresistor_list_index , &photoresistor_prev_edge_input_value , &photoresistor_prev_edge_low_pass );
    client.publish("transmit_sensors_collect_topic" , "#X0&" );

    //delay(1000);

    xTaskNotifyGive( readSensorsTaskHandle );
      
  }
}

extern "C" void app_main()
{
  initArduino();

  setup();

  xTaskCreate(loopCheckTask, "loopTask", CONFIG_ARDUINO_LOOP_STACK_SIZE, NULL, 1 | portPRIVILEGE_BIT, &loopCheckTaskHandle);
  
  xTaskCreate(
    &readSensors_task, // task function
    "readSensorsTask", // task name
    2048, // stack size in words
    NULL, // pointer to parameters
    1 | portPRIVILEGE_BIT, // priority
    &readSensorsTaskHandle); // out pointer to task handle
  
}

// for NTC Analog Temperature Sensor from 3813 to 462 --> 3351 to 0
//thermometer_value = 3813 - thermometer_value; // reverse values order
//float celsius_diff = map(thermometer_value , 462 , 3813, -24, 80); // range: 0 to 3351 maps -24 to 80
//float celsius = (1 / (((log(1 / ( 1023. / (thermometer_value - 1) )) / BETA) + 1.0) / 298.15)) - 273.15;
