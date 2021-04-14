import json
import os
import time
import threading

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
            print('Could not initialize camera pair')
            return False


    def getFrames(self):
        """Grab and retrieve frames"""
        for i in range(10):
            self.leftCam.grab()
            self.rightCam.grab()

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

    
    def camPreview_Internal(self):
        """Preview camera outputs"""
        print("Initializing cameras for preview")
        if not self.checkOpen():
            pass

        retVal = self.getFrames()

        while retVal:
            if ((time.time()-self.previousTime)>=self.frameTime):
                self.previousTime = time.time()

                retVal = self.getFrames()

                cv2.imshow('Left', self.leftImg)
                cv2.imshow('Right', self.rightImg)

                key = cv2.waitKey(20)
                if key == 27: # Exit on ESC
                    break
                if key == 32: # Capture on SPACE
                    self.captureImages()

        cv2.destroyAllWindows()

    
    def camPreview(self):
        """Preview camera outputs. Runs as a thread"""
        previewThread = threading.Thread(target=self.camPreview_Internal)
        previewThread.start()


### To do: Load stereo calibration data and matrices from jsons ###


    def stereoRectify(self):
        """Computes rotation (3x3) and projection matrices (3x4) for each 
        camera, the Q matrix, and valid regions of interest. The Q matrix 
        is a 4×4 disparity-to-depth mapping matrix. Projection matrices are
        in the rectified coordinate frame."""
        self.rotationMatrixL, self.rotationMatrixR, self.projectionMatrixL,\
        self.projectionMatrixR, self.dispToDepthMatrix, roiL, roiR = \
            cv2.stereoRectify(self.cameraMatrixL, self.distortionCoeffsL, \
                self.cameraMatrixR, self.distortionCoeffsR, \
                self.grayImageL.shape[::-1], self.stereoRotationMatrix, \
                self.stereoTranslationMatrix, alpha=self.rectifyScale, \
                newImageSize=(0,0))



if __name__=="__main__":
    Stereo = StereoCam(leftID=2, rightID=0, width=1280, height=720, fps=2)
    Stereo.camPreview()