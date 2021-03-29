import glob
import os
import time
import json

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


    class Calibrate:
        """Class for camera calibration"""
        def __init__(self, chessBoardSize, squareSize, path = "captures/calibrate/*.png"):
            self.cornerSubPixCriteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            self.chessBoardSize = chessBoardSize
            self.squareSize = squareSize # mm

            # Preparing object points like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0), multiplied by square size
            self.objectPointPrep = np.zeros((self.chessBoardSize[0]*self.chessBoardSize[1],3), np.float32)
            self.objectPointPrep[:,:2] = np.multiply(np.mgrid[0:self.chessBoardSize[0],0:self.chessBoardSize[1]].T.reshape(-1,2), self.squareSize)

            # Arrays to store object points and image points from all images
            self.objectPoints = [] # 3D point in real world space
            self.imagePoints = [] # 2D points in image plane

            # Pull up checkerboard images
            self.images = glob.glob(path)

            # Flag
            self.calibrated = False

        def findCorners(self):
            """Find chessboard corners on images from folder"""
            self.calibrated = False

            for fileName in self.images:
                image = cv2.imread(fileName)
                self.grayImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                # Find the chess board corners
                retVal, corners = cv2.findChessboardCorners(self.grayImage, self.chessBoardSize, None)

                # If found, add object points, image points (after refining them)
                if retVal == True:
                    self.objectPoints.append(self.objectPointPrep)
                    subPixCorners = cv2.cornerSubPix(self.grayImage, corners, (11,11), (-1,-1), self.cornerSubPixCriteria)
                    self.imagePoints.append(subPixCorners)

                    # Draw and display the corners
                    cv2.drawChessboardCorners(image, self.chessBoardSize, subPixCorners, retVal)
                    cv2.imshow('Chessboard', image)
                    cv2.waitKey(500)

            cv2.destroyAllWindows()
        
        def calibrate(self):
            retVal, self.cameraMatrix, self.distortionCoeffs, self.rotationVecs, self.translationVecs = \
                cv2.calibrateCamera(self.objectPoints, self.imagePoints, self.grayImage.shape[::-1], None, None)
            if retVal:
                self.calibrated = True
                print("Calibration complete")
            else:
                self.calibrated = False
                print("Calibration failed")
            
        def printResults(self):
            if self.calibrated:
                with np.printoptions(precision=3, suppress=True):
                    print("Camera matrix:\n\n", self.cameraMatrix, "\n")
                    print("Distortion coefficients:\n\n", self.distortionCoeffs, "\n")
                    print("Rotation vectors:\n\n", self.rotationVecs, "\n")
                    print("Translation vectors:\n\n", self.translationVecs, "\n")
            else:
                print("Not calibrated yet")

        def exportResults(self):
            results = {"CameraMatrix" : self.cameraMatrix.tolist()}
            with open("calibration.json", "w") as resultJson: 
                json.dump(results, resultJson)
            print("Exported to calibration.json")


if __name__=="__main__":
    Stereo = StereoCam(leftID=0, rightID=2, width=1280, height=720, fps=2)
    Stereo.camPreview()