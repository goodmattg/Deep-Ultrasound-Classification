import argparse, uuid
import cv2
import numpy as np
from constants.ultrasoundConstants import HSV_COLOR_THRESHOLD


def get_color_image_focus(
    path_to_image, 
    path_to_output_directory, 
    HSV_lower_bound, 
    HSV_upper_bound,
    interpolation_factor=None,
    interpolation_method=cv2.INTER_CUBIC,
    crop_inside_boundary_radius=3):
    """
    Determines the "focus" of an ultrasound frame in Color/CPA. 

    Ultrasound frames in Color/CPA mode highlight the tumor under examination to 
    focus the direction of the scan. This function extracts the highlighted region, which
    is surrounded by a bright rectangle and saves it to file. 

    Arguments:
        path_to_image: path to input image file
        path_to_output_directory: path to output directory 
        HSV_lower_bound: np.array([1, 3], uint8) lower HSV threshold to find highlight box
        HSV_upper_bound: np.array([1, 3], uint8) upper HSV threshold to find highlight box

    Optional:
    interpolation_factor                    Factor to use to use for interpolation. e.g. 0.5 is downscale by 2x
    
    interpolation_method                    Method to use for interpolation. Default is bicubic interpolation

    crop_inside_boundary_radius             Crop center of found image focus creating boundary of radius pixels.
                                                Default is 2px boundary radius.

    Returns:
        path_to_image_focus: path to saved image focus with has as filename

    Raises:
        IOError: in case of any errors with OpenCV or file operations 

    """
    try:
        
        # Load the image and convert it to HSV from BGR
        # Then, threshold the HSV image to get only target border color

        bgr_image = cv2.imread(path_to_image, cv2.IMREAD_COLOR)
        hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_image, HSV_lower_bound, HSV_upper_bound)

        # Determine contours of the masked image

        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[1]

        if len(contours) == 0:
             raise Exception("Unable to find any matching contours.")

        # Contour with maximum enclosed area corresponds to highlight rectangle

        max_contour = max(contours, key = cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)

        # Crop the image to the bounding rectangle

        focus_bgr_image = bgr_image[y:y+h, x:x+w]

        # The bounding box includes the border. Remove the border by masking on the same 
        # thresholds as the initial mask, then flip the mask and draw a bounding box. 

        focus_hsv = cv2.cvtColor(focus_bgr_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(focus_hsv, HSV_lower_bound, HSV_upper_bound)
        mask = cv2.bitwise_not(mask)

        contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[1]

        if len(contours) == 0:
            raise Exception("Unable to find any matching contours.")

        #find the biggest area
        max_contour = max(contours, key = cv2.contourArea)

        x, y, w, h = cv2.boundingRect(max_contour)

        # Crop the image to the bounding rectangle
        # As conservative measure crop inwards 3 pixels to guarantee no boundary

        cropped_image = focus_bgr_image[y+3:y+h-3, x+3:x+w-3]

        # Interpolate (upscale/downscale) the found segment if an interpolation factor is passed
        if interpolation_factor is not None:
            cropped_image = cv2.resize(
                cropped_image, 
                None, 
                fx=interpolation_factor, 
                fy=interpolation_factor, 
                interpolation=interpolation_method)

        output_path = "{0}/{1}.png".format(path_to_output_directory, uuid.uuid4())

        cv2.imwrite(output_path, cropped_image)

        return output_path

    except Exception as e:
        raise IOError("Error isolating and saving image focus. " + str(e))

if __name__ == "__main__":

    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()

    ap.add_argument("-i", "--image", required=True,
        help="path to input image target of OCR subroutine")

    ap.add_argument("-p", "--preprocess", type=str, default="thresh",
        help="type of preprocessing to be done")
        
    args = vars(ap.parse_args())

    get_color_image_focus(
        args["image"],
        ".", 
        np.array(HSV_COLOR_THRESHOLD.LOWER.value, np.uint8), 
        np.array(HSV_COLOR_THRESHOLD.UPPER.value, np.uint8))