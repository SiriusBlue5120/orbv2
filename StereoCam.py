import json
import os
import time

import cv2
import numpy as np


class StereoCam:
    """Class to handle a camera pair as a synchronized stereo pair"""
    def __init__(self, leftID, rightID, width = 1280, height = 720, fps=2):
        self.leftCam = cv2.VideoCapture(leftID)
        self.rightCam = cv2.VideoCapture(rightID)

        # Set camera resolution
        self.leftCam.set(3, width)
        self.leftCam.set(4, height)
        self.rightCam.set(3, width)
        self.rightCam.set(4, height)

        # Set format to MJPG in FourCC format 
        self.leftCam.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc('M','J','P','G'))
        self.rightCam.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc('M','J','P','G'))

        # Timing
        self.previousTime = time.time()
        self.frameTime = float(1/fps)

        # Capture details
        self.imgCounter = 0
        self.capturePath = "captures/" 


    def checkOpen(self):
        """Check if cameras have initialized"""
        if self.leftCam.isOpened() and self.rightCam.isOpened():
            return True
        else:
            return False


    def grabFrame(self):
        """Grab a frame from both cameras at the same time"""
        for i in range(10):
            self.leftCam.grab()
            self.rightCam.grab()


    def retrieveFrame(self):
        """Retrieve the grabbed frames"""
        retLeft, self.leftImg = self.leftCam.retrieve()
        retRight, self.rightImg = self.rightCam.retrieve()
        if retLeft and retRight:
            return True
        else:
            return False


    def captureImages(self):
        """Capture and save images from both cameras"""
        for (cam, frame) in [("left", self.leftImg), ("right", self.rightImg)]:
            imgName = "".join([cam, "_{}.png".format(self.imgCounter)])
            cv2.imwrite(os.path.join(self.capturePath, imgName), frame)
            print("Captured {}".format(imgName))
        self.imgCounter += 1

    
    def camPreview(self):
        """Preview the camera outputs"""
        if self.checkOpen():
            self.grabFrame()
            retVal = self.retrieveFrame()
            while retVal:
                if ((time.time()-self.previousTime)>=self.frameTime):
                    self.previousTime = time.time()

                    self.grabFrame()
                    retVal = self.retrieveFrame()

                    cv2.imshow('Left', self.leftImg)
                    cv2.imshow('Right', self.rightImg)

                    key = cv2.waitKey(20)
                    if key == 27: # Exit on ESC
                        break
                    if key == 32: # Capture on SPACE
                        self.captureImages()

            cv2.destroyAllWindows()
        else:
            print('Could not initialize camera pair')

    def loadCalibration(self, path="data/calibration.json"):
        try:
            with open(path, "r") as matrixJson:
                calibrationDict = json.load(matrixJson)
                self.cameraMatrix = np.array(calibrationDict["cameraMatrix"])
                self.distortionMatrix = np.array(calibrationDict["distortionCoefficients"])
            print("Calibration loaded")
        except:
            print("Could not load array")


if __name__=="__main__":
    Stereo = StereoCam(leftID=0, rightID=2, width=1280, height=720, fps=2)
    Stereo.camPreview()