"""Module containing class Arduino to handle connections to Arduino COM and log data"""

import os
import time
import re
import multiprocessing
import csv

import serial
from serial.serialutil import SerialTimeoutException


class Arduino:
    """Class to handle connections to Arduino COM"""
    # Connection
    arduino = None
    baudrate = 115200
    connected = None
    timeout = 15
    interval = 0.5

    testWord = "ping"

    writeVerbose = False
    logToCsv = False
    verbose = True

    # Use different port name list for connection based on platform
    # Linux
    if os.name == "posix":
        ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyACM2", "/dev/ttyACM3"]
    # Windows
    elif os.name == "nt":
        ports = ["COM8", "COM6"]

    if logToCsv:
        csvFile = open("logs/arduinoLog.csv", "w", encoding="UTF-8")
        csvWriter = csv.writer(csvFile)


    def __init__(self):
        # Connection 
        self.arduino = serial.Serial()
        self.arduino.baudrate = self.baudrate
        self.connected = False

        self.syncEvent = multiprocessing.Event()


    def attemptPortConnection(self, port):
        """Attempt to connect on the passed port"""
        count = 0
        self.connected = False
        self.arduino.port = port
        print(''.join(['\nConnecting on port ', port, '...\n']))
        try:
            self.arduino.open()
            self.arduino.flushInput()
            
            time.sleep(5)

            while not self.connected:
                self.writeToSerial(self.testWord)
                time.sleep(self.interval)
                
                if self.readFromSerial() is not None:                    
                    print(''.join(['Connected on port ', port, '.']))
                    self.arduino.flushInput()

                    self.connected = True
                    
                    return True
            
                else: 
                    count += 1
                    if count * self.interval > self.timeout:
                        raise SerialTimeoutException(''.join(['Could not connect on ', \
                                                port, ' within timeout interval.']))
        except:
            print(''.join(['Could not connect on port ', port, '.']))
            self.connected = False
            return False


    def attemptConnection(self):
        """Attempt to connect on all specified ports, tries the next if one fails. 
        Uses attemptPortConnection to do so internally."""
        for port in self.ports:
            if (self.attemptPortConnection(port)):
                time.sleep(1)
                return True
        print('Could not connect on any port.')
        return False
     

    def writeToSerial(self, content):
        """Write the passed content to serial with start and end characters"""
        try:
            message = "".join(["<", content, ">"]).encode("utf_8")
            self.arduino.write(message)

            if self.writeVerbose:
                print("Serial write:", content)

            self.syncEvent.clear()

        except:
            print("Could not send message through serial")

    
    def readFromSerial(self):
        """Reads content from serial and removes start and end characters"""
        if self.arduino.in_waiting:
            try:
                content = re.search("<.*?>", self.arduino.readline().decode("utf-8"))
                content = content.group()[1:-1]

            except:
                content = 0

            if content:
                if self.verbose:
                    print("Serial read:", content)

                if self.logToCsv:
                    self.csvWriter.writerow(content.split())

                self.syncEvent.set()

                return content
            else:
                return None


    def closeConnection(self):
        """Close connection and exit"""
        print('Cleaning up and closing connection...\n')
        if self.logToCsv:
            self.csvFile.close()

        try:
            self.arduino.close()
            self.connected = False
            print ('Done!\n')
        except Exception as e:
            print (e)
            print ('Something went wrong when wrapping up. Closing down anyway...')



if __name__ == "__main__":
    print("Import to use")