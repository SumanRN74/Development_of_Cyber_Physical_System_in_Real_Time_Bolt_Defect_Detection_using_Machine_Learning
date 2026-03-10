#include <AFMotor.h>
#include <Servo.h>

// Create motor and servo objects
AF_DCMotor motor1(1);  // Motor 1 on M1 terminal
Servo myServo;         // Servo on SERVO1 (pin 10)

// Serial communication variables
String receivedMessage = "";
bool messageComplete = false;

void setup() {
  Serial.begin(9600);

  // Initialize motor
  motor1.setSpeed(83);   // Speed (0–255)
  motor1.run(FORWARD);    // Run forward

  // Attach servo
  myServo.attach(10);     // SERVO1 on D10
  myServo.write(0);       // Start at 0°

  Serial.println("Adafruit L293D Motor Shield Ready");
  Serial.println("Motor running at speed 200");
  Serial.println("Send 'HIGH' to move servo 150° then return to 0°");
}

void loop() {
  // Read serial data
  if (Serial.available() > 0) {
    char incomingChar = Serial.read();

    if (incomingChar == '\n' || incomingChar == '\r') {
      if (receivedMessage.length() > 0) {
        messageComplete = true;
      }
    } else {
      receivedMessage += incomingChar;
    }
  }

  // Process when message complete
  if (messageComplete) {
    processMessage(receivedMessage);
    receivedMessage = "";
    messageComplete = false;
  }
}

void processMessage(String message) {
  message.trim();
  message.toUpperCase();

  Serial.print("Received: ");
  Serial.println(message);

  if (message == "HIGH") {
    delay(700);
    myServo.write(160);
    Serial.println("Servo moved to 150°");
    delay(500);  // Wait for 1 second at 150°
    myServo.write(0);
    Serial.println("Servo returned to 0°");
  } 
  else {
    Serial.println("Unknown command. Use 'HIGH'");
  }

  delay(300);
}
