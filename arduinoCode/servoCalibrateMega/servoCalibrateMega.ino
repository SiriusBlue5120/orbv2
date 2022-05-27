/*
Code to calibrate servos using a ds4 controller
*/

#include <Servo.h>


// Serial recieve variables
#define BAUDRATE 115200
const byte numChars = 48;
char receivedChars[numChars];
boolean newData = false;
boolean serialConnected = false;
char testWord[] = "ping";
unsigned int pingInterval = 500;


// Servo variables
// Expands array as required
#define LEGS 4
#define SERVOS 12

Servo joints[SERVOS];
int servoPins[SERVOS] = { 13,  12,  11,
                          10,  9,  8,
                          7,  6, 5,
                         4, 3, 2};

// Initially set to positions specified below
float servoStates[SERVOS] = { 90, 100,  20,      // Hip, shoulder, knee
                              90,  50, 165,
                              75, 110,  35,
                              90,  90, 90};

// Range of movement = {60, 90, 120} degrees for {hip, shoulder, knee}
  
int minServoStates[SERVOS] = { 60, 130,  20,
                              120,  20, 165,
                               45, 140,  35,
                              0,  0, 0};
                              
int maxServoStates[SERVOS] = {120,  40,  140,  
                              60, 110,  45,
                              105,  50,  155,
                              180, 180, 180};

// Max swing rate in degrees per second
float maxSwingRate = 90;
// Refresh time in milliseconds
unsigned int servoRefresh = 10;

unsigned long prevServo = millis();


// Controller state
// Number of independent state variables
#define STATES 7
#define MIDSTATE 10

// L3x2, R3x2, L2, R2, Square
int controller[STATES] = {10, 10, 10, 10, 0, 0, 0};
int currentLeg = 0;
int legServoIndexOffset = 3*currentLeg;

unsigned long prevController = millis();


// General states
unsigned long currentTime = millis();



void setup(){
  // Establishing connection through serial
  establishSerialConnection();
  
  // Setting up servos
  maxSwingRate = maxSwingRate * servoRefresh / 1000;
  // initializeServoPosition();

  attachServoPins();
    
  currentTime = millis();
}


void loop(){
  // Update loop time
  currentTime = millis();
  
  // Recieve data from serial
  receiveSerialData();

  if (newData){
    newData = false;
    extractControllerState();
    checkLegChange();
    writeServoStateSerial();
  }  
  
  if ((currentTime-prevServo)>=servoRefresh){
    updateServoStates();
    
    writeStatesToServos();
  }
}


// Function to attach pins to corresponding servos
void attachServoPins() {
  for (int i = 0; i < SERVOS; i ++){  
    // Attach pins to the corresponding servo
    joints[i].write(servoStates[i]);
    joints[i].attach(servoPins[i]);
  
    // Delay before continuing
    delay(100);
  }
}


// Function to establish connection through serial
void establishSerialConnection() {
  Serial.begin(115200);
  
  while (!serialConnected) {
    
    receiveSerialData();
    
    if (newData) {
      newData = false;
      
      serialConnected = true;
      
      for (int i = 0; receivedChars[i]!='\0'; i++) {
        if (receivedChars[i]!=testWord[i]) {
          serialConnected = false;
          
          break;
        }
      }
      
      Serial.print("<");
      Serial.print(testWord);
      Serial.println(">");
    }
   
    else {
      delay(pingInterval);
      
      Serial.print("<");
      Serial.print(testWord);
      Serial.println(">");
    } 
  }  
}


// Function to remove start and stop characters from serial message
void receiveSerialData(){
  static boolean recvInProgress = false;
  static byte ndx = 0;
  static char startMarker = '<';
  static char endMarker = '>';
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();

    if (recvInProgress == true) {
      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1;
        }
      }
      else {
        receivedChars[ndx] = '\0'; // Terminate the string
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
    }

    else if (rc == startMarker) {
      recvInProgress = true;
    }
  }
}


/* 
Function to extract controller values from serial message based
on message start character
*/
void extractControllerState(){
  char * token = strtok(receivedChars, " ");
  
  if (*token == 'd'){
    token = strtok(NULL, " ");
    for (int i = 0; i < STATES; i ++){
      controller[i] = atoi(token);
      
      token = strtok(NULL, " ");
    }
  }
}


// Function to update servo states
void updateServoStates(){
  legServoIndexOffset = 3*currentLeg;
  
  servoStates[legServoIndexOffset+0] = servoStates[legServoIndexOffset+0] + (maxSwingRate*(controller[0] - MIDSTATE) / MIDSTATE) * 
                                        ((maxServoStates[legServoIndexOffset+0] - minServoStates[legServoIndexOffset+0]) / 
                                        abs(maxServoStates[legServoIndexOffset+0] - minServoStates[legServoIndexOffset+0]));
                                        
  servoStates[legServoIndexOffset+1] = servoStates[legServoIndexOffset+1] + (maxSwingRate*(controller[2] - MIDSTATE) / MIDSTATE) * 
                                        (-(minServoStates[legServoIndexOffset+1] - maxServoStates[legServoIndexOffset+1]) / 
                                        abs(minServoStates[legServoIndexOffset+1] - maxServoStates[legServoIndexOffset+1]));
                                        
  servoStates[legServoIndexOffset+2] = servoStates[legServoIndexOffset+2] + (maxSwingRate*(controller[5] - controller[4]) / MIDSTATE) * 
                                        ((maxServoStates[legServoIndexOffset+2] - minServoStates[legServoIndexOffset+2]) / 
                                        abs(maxServoStates[legServoIndexOffset+2] - minServoStates[legServoIndexOffset+2]));
  
  prevServo = currentTime;
}


// Function to copy minServoStates to servoStates
void initializeServoPosition(){
  for (int i = 0; i < SERVOS; i ++){
    servoStates[i] = minServoStates[i];
  }
}


// Function to write servoState to all servos
void writeStatesToServos(){
  for (int k = 0; k < SERVOS; k ++){
    // Clamp servoStates within limits
    if (maxServoStates[k] > minServoStates[k]){
      if (servoStates[k] > maxServoStates[k]){
        servoStates[k] = maxServoStates[k];
      }
      else if (servoStates[k] < minServoStates[k]){
        servoStates[k] = minServoStates[k];
      }
    }
    else {
      if (servoStates[k] > minServoStates[k]){
        servoStates[k] = minServoStates[k];
      }
      else if (servoStates[k] < maxServoStates[k]){
        servoStates[k] = maxServoStates[k];
      }
    }
    
    
    // Write state to servo
    joints[k].write(servoStates[k]);
  }
}


// Function to write servoStates to serial
void writeServoStateSerial() {
  Serial.print("<s");
  
  Serial.print(" ");
  Serial.print(int(currentLeg));
  Serial.print(" ");
  
  for (int i = (3*currentLeg); i < ((3*currentLeg)+3); i ++) {
    Serial.print(" ");
    Serial.print(int(servoStates[i]));
  }
  
  Serial.println(">");
}


// Function to check for leg change
void checkLegChange() {
  static boolean legChange = false;
  
  if ((controller[6]==1)&&(legChange==false)) {
    legChange = true;
    currentLeg = currentLeg + 1;
    
    if (currentLeg > (LEGS - 1)) {
      currentLeg = 0;
    }
  }
  
  else if ((controller[6]==0)&&(legChange==true)) {
    legChange = false;
  }
}
