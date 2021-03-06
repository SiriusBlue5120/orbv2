import ctypes
import multiprocessing
import time

import cv2
import numpy as np


class StereoCapture(multiprocessing.Process):
    """Class to handle capture from stereo camera setup"""
    def __init__(self, cameraID=(2,0), imageSize=(1280/2,720/2), fps=4, vertical=True):
        super(StereoCapture, self).__init__()

        # Camera IDs and properties
        self.leftID = cameraID[0]   # or top
        self.rightID = cameraID[1]  # or bottom
        self.imageSize = imageSize
        self.fps = fps
        self.vertical = vertical

        # Seting up capture objects
        self.leftCam = cv2.VideoCapture(self.leftID)
        self.rightCam = cv2.VideoCapture(self.rightID)

        # Set camera resolution
        # Left
        self.leftCam.set(3, self.imageSize[0])
        self.leftCam.set(4, self.imageSize[1])
        # Right
        self.rightCam.set(3, self.imageSize[0])
        self.rightCam.set(4, self.imageSize[1])

        # Set format to MJPG in FourCC format 
        self.leftCam.set(cv2.CAP_PROP_FOURCC, \
            cv2.VideoWriter_fourcc('M','J','P','G'))

        self.rightCam.set(cv2.CAP_PROP_FOURCC, \
            cv2.VideoWriter_fourcc('M','J','P','G'))

        # Timing
        self.previousTime = time.time()
        self.frameTime = float(1/self.fps)

        # Events
        self.imageProcessorEvent = multiprocessing.Event()
        self.visualOdometryEvent = multiprocessing.Event()
        self.quitEvent = multiprocessing.Event()

        # Flags
        self.bufferReady = False
        self.denoise = False

        # Debug
        self.verbose = False



    def checkOpen(self):
        """Check if cameras have initialized"""
        if self.leftCam.isOpened() and self.rightCam.isOpened():
            return True
        else:
            raise IOError("Could not initialize camera pair")

    
    def createBuffers(self):
        """Create and shape buffers into image arrays"""
        # Check if camera pair has initialized
        if not self.checkOpen():
            return
        
        print("Initialized camera pair")

        # Finding image shape
        retVal, leftImage = self.leftCam.read()
        if self.vertical:
            leftImage = cv2.rotate(leftImage, cv2.ROTATE_90_COUNTERCLOCKWISE)
        self.cvImageShape = leftImage.shape
        self.cvImageSize = leftImage.size

        # Creating shared memory buffers
        self.leftImageBuffer = multiprocessing.Array(ctypes.c_uint8, \
            self.cvImageSize, lock=False)
        self.rightImageBuffer = multiprocessing.Array(ctypes.c_uint8, \
            self.cvImageSize, lock=False)
        self.captureTimeBuffer = multiprocessing.Array(ctypes.c_double, \
            1, lock=False)

        # Creating arrays from shared memory buffers
        self.imageL = np.frombuffer(self.leftImageBuffer, \
                            dtype=np.uint8).reshape(self.cvImageShape)
        self.imageR = np.frombuffer(self.rightImageBuffer, \
                            dtype=np.uint8).reshape(self.cvImageShape)
        self.captureTime = np.frombuffer(self.captureTimeBuffer,\
                            dtype=np.float64)

        self.bufferReady = True
        print("Initialized capture buffers")

    
    def isBufferReady(self):
        """Check if buffers have been created"""
        if self.bufferReady:
            return True
        
        else:
            print("Buffers not initialized")
            return False

    
    def getCVImageShape(self):
        """Returns shape of image for reshaping buffer"""
        if self.bufferReady:
            return self.cvImageShape
        
        else:
            print("Buffers not initialized")
            return None

    
    def getBuffers(self):
        """Returns references of left, right internal buffers"""
        if self.isBufferReady():
            return (self.leftImageBuffer, self.rightImageBuffer, \
                    self.captureTimeBuffer)
        
        else:
            return None

    
    def getImageProcessorEvents(self):
        """Returns references of image, quit events"""
        return (self.imageProcessorEvent, self.quitEvent)

    
    def getVisualOdometryEvents(self):
        """Returns references of image, quit events"""
        return (self.visualOdometryEvent, self.quitEvent)


    def getFrames(self):
        """Grab and retrieve frames"""
        self.previousTime = time.time()

        for i in range(3):
            self.leftCam.grab()
            self.rightCam.grab()
        
        self.captureTime[0] = time.time()

        retLeft, imageL = self.leftCam.retrieve()
        retRight, imageR = self.rightCam.retrieve()

        # Write images to buffer instead of assigning as array
        if self.vertical:
            imageL = cv2.rotate(imageL, cv2.ROTATE_90_COUNTERCLOCKWISE)
            imageR = cv2.rotate(imageR, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self.imageL[:] = imageL
        self.imageR[:] = imageR

        if retLeft and retRight:
            # Denoise if flag set
            if self.denoise:
                self.denoiseSingleColor()

            self.actualFrameTime = time.time() - self.previousTime
            self.remainingTime = self.frameTime - self.actualFrameTime

            # Set capture events to true
            self.imageProcessorEvent.set()
            self.visualOdometryEvent.set()
            
            return True

        else:
            return False


    def capture(self, denoise=False):
        """Capture images from camera pair"""
        # Check if camera and buffers have initialized
        if not self.checkOpen() or not self.isBufferReady():
            return
            
        # Capture frames from camera pair
        while self.getFrames():

            if self.quitEvent.is_set():
                break     
            
            if self.verbose:
                print("Capture time: {:.5f}  Frame time: {:.5f}  "\
                    .format(self.captureTime[0], self.actualFrameTime), \
                    end="")
                print("Remaining time: {:.5f}  Frame is:"\
                    .format(self.remainingTime), end=" ")

                if self.remainingTime<0:
                    print("late")

                else:
                    print("on time")
                    time.sleep(self.remainingTime)
            
            else:
                if self.remainingTime>0:
                    time.sleep(self.remainingTime)
        
        self.leftCam.release()
        self.rightCam.release()


    def setDenoise(self, denoise):
        """Enable or disable denoising"""
        self.denoise = denoise

    
    def denoiseSingleColor(self):
        """Perform denoising on single color image"""
        self.imageL[:] = cv2.fastNlMeansDenoisingColored(self.imageL, \
            None, 10, 10, 7, 21)
        self.imageR[:] = cv2.fastNlMeansDenoisingColored(self.imageR, \
            None, 10, 10, 7, 21)

        
    def run(self):
        """Runs when start() is called on this process"""
        self.capture()



if __name__=="__main__":
    print("Handled by ProcessManager")
