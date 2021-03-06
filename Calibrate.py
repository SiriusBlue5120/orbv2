import glob
import time

import cv2
import numpy as np

from helperScripts import jsonHelper
from helperScripts.TimeKeeper import TimeKeeper


class Calibrate:
    """Class for camera calibration"""
    def __init__(self, chessBoardSize, squareSize):
        # Termination criteria for distortion calibration
        self.cornerSubPixCriteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.stereoCriteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # Chessboard properties
        self.chessBoardSize = chessBoardSize
        self.squareSize = squareSize # mm

        # Preparing object points like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0), multiplied by square size
        self.objectPointPrep = np.zeros((self.chessBoardSize[0]*self.chessBoardSize[1],3), np.float32)
        self.objectPointPrep[:,:2] = \
            np.multiply(np.mgrid[0:self.chessBoardSize[0],0:self.chessBoardSize[1]].T.reshape(-1,2), \
                self.squareSize)

        # Arrays to store object points and image points from all images
        self.objectPoints = [] # 3D point in real world space
        self.imagePointsL = [] # 2D points in image plane, left
        self.imagePointsR = [] # right        

        # Flags
        self.monoCalibrated = False
        self.stereoCalibrated = False
        self.stereoRectified = False
        self.imageLoaded = False

        # Camera properties
        self.apertureSize = (3.84, 2.16) # (width, height) in mm

        # Debug
        self.timeKeeper = TimeKeeper()


    def loadImagesForCalibration(self, imageFormat=".png", path="captures"):
        """Loads images of specified format from path for calibration"""
        self.imageFormat = imageFormat
        self.path = path
        try:
            self.imageGlobL = sorted(glob.glob("".join([self.path, "/left_*", self.imageFormat])))
            self.imageGlobR = sorted(glob.glob("".join([self.path, "/right_*", self.imageFormat])))

            if len(self.imageGlobL)==0 or len(self.imageGlobR)==0:
                raise FileNotFoundError
            
            self.vertical = False

        except:
            self.imageGlobL = sorted(glob.glob("".join([self.path, "/top_*", self.imageFormat])))
            self.imageGlobR = sorted(glob.glob("".join([self.path, "/bottom_*", self.imageFormat])))

            self.vertical = True

        # Counting number of images in directory
        # Ensure that only required and matching images are stored here
        self.imageCount = len(self.imageGlobL) + len(self.imageGlobR)
        
        assert len(self.imageGlobL)==len(self.imageGlobR), \
                                        "Unpaired images exist in folder"
        
        print("Found {} images in folder ({} image pairs)".format(\
                                self.imageCount, int(self.imageCount/2)))
        self.imageLoaded = True

    
    def isImageLoaded(self):
        """Check if images have been loaded"""
        if self.imageLoaded:
            return True

        else:
            print("Images not loaded")
            return False  


    def findCorners(self, previewDelay=500):
        """Find chessboard corners on images from folder"""
        self.monoCalibrated = False

        if not self.isImageLoaded():
            return

        # Count of image pairs where chessboard was detected
        chessboardCount = 0

        for fileNameL, fileNameR in zip(self.imageGlobL, self.imageGlobR):
            # Reading left and right images
            self.imageL = cv2.imread(fileNameL)
            self.imageR = cv2.imread(fileNameR)

            # Converting to grayscale
            self.grayImageL = cv2.cvtColor(self.imageL, cv2.COLOR_BGR2GRAY)
            self.grayImageR = cv2.cvtColor(self.imageR, cv2.COLOR_BGR2GRAY)

            # Finding chess board corners
            retValL, cornersL = cv2.findChessboardCorners(self.grayImageL, self.chessBoardSize, None)
            retValR, cornersR = cv2.findChessboardCorners(self.grayImageR, self.chessBoardSize, None)

            # If found, add object points, image points (after refining them)
            if retValL and retValR:
                chessboardCount += 1

                self.objectPoints.append(self.objectPointPrep)

                cornersL = cv2.cornerSubPix(self.grayImageL, cornersL, (11,11), (-1,-1), self.cornerSubPixCriteria)
                cornersR = cv2.cornerSubPix(self.grayImageR, cornersR, (11,11), (-1,-1), self.cornerSubPixCriteria)
                
                self.imagePointsL.append(cornersL)
                self.imagePointsR.append(cornersR)

                # Draw and display the corners
                cv2.drawChessboardCorners(self.imageL, self.chessBoardSize, cornersL, retValL)
                cv2.drawChessboardCorners(self.imageR, self.chessBoardSize, cornersR, retValR)

                cv2.imshow('Chessboard_Left', self.imageL)
                cv2.imshow('Chessboard_Right', self.imageR)

                cv2.waitKey(previewDelay)

            else:
                print("Chessboards not found in pair: {}, {}".format(\
                    fileNameL.replace("".join([self.path, "/"]), ""), \
                    fileNameR.replace("".join([self.path, "/"]), "")))
            
        print("Chessboards were found in {} image pairs (out of {} image pairs)"\
                            .format(chessboardCount, int(self.imageCount/2)))

        cv2.destroyAllWindows()
        

    def monoCalibrate(self):
        """Calculate camera matrix, distortion coefficients and rotation and 
        translation vectors"""
        self.timeKeeper.startPerfCounter()

        # Left
        retValL, self.cameraMatrixL, self.distortionCoeffsL, \
            self.rotationVecsL, self.translationVecsL = \
            cv2.calibrateCamera(self.objectPoints, self.imagePointsL, \
                self.grayImageL.shape[::-1], None, None)
        # Right
        retValR, self.cameraMatrixR, self.distortionCoeffsR, \
            self.rotationVecsR, self.translationVecsR = \
            cv2.calibrateCamera(self.objectPoints, self.imagePointsR, \
                self.grayImageR.shape[::-1], None, None)

        # Finding optimal camera matrices and regions of interest
        # Left
        self.heightL, self.widthL = self.grayImageL.shape[:2]
        self.optimalCameraMatrixL, self.roiL = \
            cv2.getOptimalNewCameraMatrix(self.cameraMatrixL,\
                self.distortionCoeffsL, (self.widthL, self.heightL), 1,\
                (self.widthL, self.heightL))
        # Right
        self.heightR, self.widthR = self.grayImageR.shape[:2]
        self.optimalCameraMatrixR, self.roiR = \
            cv2.getOptimalNewCameraMatrix(self.cameraMatrixR,\
                self.distortionCoeffsR, (self.widthR, self.heightR), 1,\
                (self.widthR, self.heightR))

        if retValL and retValR:
            self.monoCalibrated = True
            print("Mono calibration completed in {:.5f} seconds".format(\
                                        self.timeKeeper.returnPerfCounter()))

        else:
            self.monoCalibrated = False
            print("Calibration failed")

    
    def isMonoCalibrated(self):
        """Check if mono calibration has been done"""
        if self.monoCalibrated:
            return True
        else:
            print("Not mono calibrated yet")
            return False


    def printMonoCalibration(self):
        """Print mono calibration results"""
        if not self.isMonoCalibrated():
            return

        with np.printoptions(precision=3, suppress=True):
            print("Left:\n\n")
            print("Camera matrix:\n", self.cameraMatrixL, "\n")
            print("Distortion coeffs:\n", self.distortionCoeffsL, "\n")
            print("Rotation vectors:\n", self.rotationVecsL, "\n")
            print("Translation vectors:\n", self.translationVecsL, "\n")

            print("\n\nRight:\n\n")
            print("Camera matrix:\n", self.cameraMatrixR, "\n")
            print("Distortion coeffs:\n", self.distortionCoeffsR, "\n")
            print("Rotation vectors:\n", self.rotationVecsR, "\n")
            print("Translation vectors:\n", self.translationVecsR, "\n")


    def exportMonoCalibration(self, path="data/monoCalibration.json"):
        """Export results of mono calibration as a json"""
        if not self.isMonoCalibrated():
            return

        # Crafting dictionary to hold results
        results = {
            "left":{    
                "cameraMatrix":self.cameraMatrixL.tolist(),
                "distortionCoeffs":self.distortionCoeffsL.tolist()
            },
            "right":{
                "cameraMatrix":self.cameraMatrixR.tolist(),
                "distortionCoeffs":self.distortionCoeffsR.tolist()
            }
        }

        jsonHelper.dictToJson(results, path)


    def exportCameraProperties(self, path="data/cameraProperties.json"):
        """Computes various useful camera characteristics from the previously 
        estimated camera matrix"""
        if not self.isMonoCalibrated():
            return

        # Left
        fovXL, fovYL, focalLengthL, principalPointL, aspectRatioL = \
            cv2.calibrationMatrixValues(self.cameraMatrixL, \
            (self.widthL, self.heightL), self.apertureSize[0], \
            self.apertureSize[1])	

        # Right
        fovXR, fovYR, focalLengthR, principalPointR, aspectRatioR = \
            cv2.calibrationMatrixValues(self.cameraMatrixR, \
            (self.widthR, self.heightR), self.apertureSize[0], \
            self.apertureSize[1])

        # Crafting dictionary to hold results
        results = {
            "left":{
                "fieldOfView":{
                    "horizontal":fovXL, 
                    "vertical":fovYL
                    },
                "focalLength":focalLengthL,
                "principalPoint":principalPointL,
                "aspectRatio":aspectRatioL
            },
            "right":{
                "fieldOfView":{
                    "horizontal":fovXR, 
                    "vertical":fovYR
                    },
                "focalLength":focalLengthR,
                "principalPoint":principalPointR,
                "aspectRatio":aspectRatioR
            },
        }
        
        jsonHelper.dictToJson(results, path)


    def findReprojectionError(self):
        """Find reprojection error. Closer to zero, more accurate the 
        calibration"""
        if not self.isMonoCalibrated():
            return

        meanError = [0, 0] # [Left, Right]
        error = [0, 0]
        for i in range(len(self.objectPoints)):
            # Left
            imgpoints2L, jacobianL = cv2.projectPoints(self.objectPoints[i], \
                self.rotationVecsL[i], self.translationVecsL[i], \
                self.cameraMatrixL, self.distortionCoeffsL)
            error[0] = cv2.norm(self.imagePointsL[i], imgpoints2L, \
                     cv2.NORM_L2)/len(imgpoints2L)
            meanError[0] += error[0]

            imgpoints2R, jacobianR = cv2.projectPoints(self.objectPoints[i], \
                self.rotationVecsR[i], self.translationVecsR[i], \
                self.cameraMatrixR, self.distortionCoeffsR)
            error[1] = cv2.norm(self.imagePointsR[i], imgpoints2R, \
                     cv2.NORM_L2)/len(imgpoints2R)
            meanError[1] += error[1]

        print("Total error (left): {}".format(meanError[0]/len(self.objectPoints)))
        print("Total error (right): {}".format(meanError[1]/len(self.objectPoints)))


    def undistortImages(self, previewDelay=500):
        """Undistort and preview images used for calibration"""
        if not self.isMonoCalibrated():
            return

        for fileNameL, fileNameR in zip(self.imageGlobL, self.imageGlobR):
            # Reading left and right images
            self.imageL = cv2.imread(fileNameL)
            self.imageR = cv2.imread(fileNameR)

            # Left
            undistortImageL = cv2.undistort(self.imageL, self.cameraMatrixL, \
                self.distortionCoeffsL, None, self.cameraMatrixL)
            # Right
            undistortImageR = cv2.undistort(self.imageR, self.cameraMatrixR, \
                self.distortionCoeffsR, None, self.cameraMatrixR)

            cv2.imshow('UndistortedImageL', undistortImageL)
            cv2.imshow('UndistortedImageR', undistortImageR)

            cv2.waitKey(previewDelay)

        cv2.destroyAllWindows()


    def stereoCalibrate(self, useOptimalMatrix=False):
        """Calibrate camera pair with respect to each other. Check code to 
        modify flags"""
        if not self.isMonoCalibrated():
            return

        # Flags for calibration; uncomment to enable
        flags = 0
        flags |= cv2.CALIB_FIX_INTRINSIC
        #flags |= cv2.CALIB_FIX_PRINCIPAL_POINT
        #flags |= cv2.CALIB_USE_INTRINSIC_GUESS
        #flags |= cv2.CALIB_FIX_FOCAL_LENGTH
        #flags |= cv2.CALIB_FIX_ASPECT_RATIO
        #flags |= cv2.CALIB_ZERO_TANGENT_DIST
        #flags |= cv2.CALIB_RATIONAL_MODEL
        #flags |= cv2.CALIB_SAME_FOCAL_LENGTH
        #flags |= cv2.CALIB_FIX_K3
        #flags |= cv2.CALIB_FIX_K4
        #flags |= cv2.CALIB_FIX_K5

        # Intrinsic camara matrices are fixed; only Rotation, Translation
        # Essential, and Fundamental matrices are calculated

        self.timeKeeper.startPerfCounter()

        if useOptimalMatrix:
            cameraMatrixL = self.optimalCameraMatrixL
            cameraMatrixR = self.optimalCameraMatrixR

        else:
            cameraMatrixL = self.cameraMatrixL
            cameraMatrixR = self.cameraMatrixR

        retValStereo, self.cameraMatrixL, self.distortionCoeffsL, \
        self.cameraMatrixR, self.distortionCoeffsR, \
        self.stereoRotationMatrix, self.stereoTranslationMatrix, \
        self.essentialMatrix, self.fundamentalMatrix = \
            cv2.stereoCalibrate(self.objectPoints, \
                self.imagePointsL, self.imagePointsR, \
                cameraMatrixL, self.distortionCoeffsL, \
                cameraMatrixR, self.distortionCoeffsR, \
                self.grayImageL.shape[::-1], criteria=self.stereoCriteria, \
                flags=flags)

        if retValStereo:
            self.stereoCalibrated = True
            print("Stereo calibration completed in {:.5f} seconds".format(\
                                        self.timeKeeper.returnPerfCounter()))
        
        else:
            self.stereoCalibrated = False
            print("Stereo calibration failed")

        
    def isStereoCalibrated(self):
        """Check if stereo calibration has been done"""
        if self.stereoCalibrated:
            return True
        else:
            print("Not stereo calibrated yet")
            return False

    
    def exportStereoCalibration(self, path="data/stereoCalibration.json"):
        """Export results of stereo calibration as a json"""
        if not self.isStereoCalibrated():
            return

        # Crafting dictionary to hold results
        results = {
            "left":{    
                "cameraMatrix":self.cameraMatrixL.tolist(),
                "distortionCoeffs":self.distortionCoeffsL.tolist()
            },
            "right":{
                "cameraMatrix":self.cameraMatrixR.tolist(),
                "distortionCoeffs":self.distortionCoeffsR.tolist()
            },
            "stereoRotationMatrix":self.stereoRotationMatrix.tolist(),
            "stereoTranslationMatrix":self.stereoTranslationMatrix.tolist(),
            "essentialMatrix":self.essentialMatrix.tolist(), 
            "fundamentalMatrix":self.fundamentalMatrix.tolist(),
            "grayImageSizeL":self.grayImageL.shape,
            "grayImageSizeR":self.grayImageR.shape,
            "imageSizeL":self.imageL.shape,
            "imageSizeR":self.imageR.shape
        }

        jsonHelper.dictToJson(results, path)


    def stereoRectify(self, rectifyScale=1):
        """Computes rotation (3x3) and projection matrices (3x4) for each 
        camera, the Q matrix, and valid regions of interest. The Q matrix 
        is a 4??4 disparity-to-depth mapping matrix. Projection matrices are
        in the rectified coordinate frame. Specify rectifyScale to crop
        unwanted pixels; does not crop by default"""
        if not self.isStereoCalibrated():
            return

        # Stereo rectification
        self.rotationMatrixL, self.rotationMatrixR, self.projectionMatrixL,\
        self.projectionMatrixR, self.dispToDepthMatrix, roiL, roiR = \
            cv2.stereoRectify(self.cameraMatrixL, self.distortionCoeffsL, \
                self.cameraMatrixR, self.distortionCoeffsR, \
                self.grayImageL.shape[::-1], self.stereoRotationMatrix, \
                self.stereoTranslationMatrix, alpha=rectifyScale, \
                newImageSize=(0,0))

        self.stereoRectified = True


    def isStereoRectified(self):
        """Check if stereo rectification has been done"""
        if self.stereoRectified:
            return True
        else:
            print("Not stereo rectified yet")
            return False


    def exportStereoRectify(self, path="data/stereoRectify.json"):
        """Export results of stereo rectification as a json"""
        if not self.isStereoRectified():
            return

        # Crafting dictionary to hold results
        results = {
            "left":{    
                "rotationMatrix":self.rotationMatrixL.tolist(),
                "projectionMatrix":self.projectionMatrixL.tolist()
            },
            "right":{
                "rotationMatrix":self.rotationMatrixR.tolist(),
                "projectionMatrix":self.projectionMatrixR.tolist()
            },
            "dispToDepthMatrix":self.dispToDepthMatrix.tolist()
        }

        jsonHelper.dictToJson(results, path)

        

if __name__=="__main__":
    print("Run using calibrateCamera.ipynb")
