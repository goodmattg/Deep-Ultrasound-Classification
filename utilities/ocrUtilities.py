# import the necessary packages
from constants.ultrasoundConstants import (
	IMAGE_TYPE,
	READOUT_ABBREVS,
	WALL_FILTER_MODES
)

from PIL import Image

import numpy as np

import os
import re 
import cv2 
import argparse 
import pytesseract 
import uuid


RADIALITY = READOUT_ABBREVS.RADIALITY.value
COLOR_TYPE = READOUT_ABBREVS.COLOR_TYPE.value
COLOR_MODE = READOUT_ABBREVS.COLOR_MODE.value
ARAD = READOUT_ABBREVS.ARAD.value
RAD = READOUT_ABBREVS.RAD.value
CPA = READOUT_ABBREVS.CPA.value
COLOR_LEVEL = READOUT_ABBREVS.COLOR_LEVEL.value
WALL_FILTER = READOUT_ABBREVS.WALL_FILTER.value
PRF = READOUT_ABBREVS.PULSE_REPITITION_FREQUENCY.value
SCALE = READOUT_ABBREVS.SCALE.value
SIZE = READOUT_ABBREVS.SIZE.value

def isolate_text(grayscale_image, image_type):
	
	FOUND_TEXT = {}

	# Hardcoded cropping bounds based on the specific ultrasound dataset
	# TODO: move to constants file

	left_bar_crop= grayscale_image[50:, :100]
	bottom_left_crop = grayscale_image[365:, 30:140]
	scale_crop = grayscale_image[15:40, 585:]

	# write the grayscale image to disk as a temporary file so we can apply OCR to it

	left_bar_filename = "{}.png".format(uuid.uuid4())
	cv2.imwrite(left_bar_filename, left_bar_crop)

	bottom_left_filename = "{}.png".format(uuid.uuid4())
	cv2.imwrite(bottom_left_filename, bottom_left_crop)

	scale_crop_filename = "{}.png".format(uuid.uuid4())
	cv2.imwrite(scale_crop_filename, scale_crop)

	# load the image as a PIL/Pillow image, apply OCR, and then delete
	# the temporary file. Tesseract segmentation mode 11 is critical for this to work
	# None of the other automatic segmentation modes correctly read the text

	raw_text = pytesseract.image_to_string(Image.open(left_bar_filename),
		lang="eng",
		boxes=False,  
		config="--psm 11") 

	# Specifically whitelist numerical characters and "." to aid the OCR engine

	raw_text_size = pytesseract.image_to_string(Image.open(bottom_left_filename),
		lang="eng",
		boxes=False,  
		config="--psm 11 -c tessedit_char_whitelist=0123456789.") 

	# Specifically whitelist numerical characters and "." to aid the OCR engine

	raw_text_scale = pytesseract.image_to_string(Image.open(scale_crop_filename),
		lang="eng",
		boxes=False,  
		config="--psm 11 -c tessedit_char_whitelist=0123456789.") 

	os.remove(left_bar_filename)
	os.remove(bottom_left_filename)
	os.remove(scale_crop_filename)

	text_segments = raw_text.splitlines()
	text_segments = [segment.upper().strip() for segment in text_segments if segment is not ""]
	
	# Isolate the frame scale (e.g. 2.4 cm, 3.9 cm)
	try:
		scale_segments = raw_text_scale.splitlines()
		scale_segments = [segment.upper().strip() for segment in scale_segments if segment is not ""]
		scale_segments = [max(re.findall(r"[\d]+(?:\.[\d]+)*", segment), key=len) for segment in scale_segments]
		scale_segments = [float(ns) for ns in scale_segments]

		# scale must be between 1 and 10 (cm). Use base 10 as check. Use None as placeholder 
		# to infer scale mean at a later stage 

		base_10_mag = np.log10(max(scale_segments))
		if base_10_mag > 0 and base_10_mag < 1:
			FOUND_TEXT[SCALE] = max(scale_segments)
		else:
			FOUND_TEXT[SCALE] = None			

	except Exception as e:
		raise("Unable to isolate frame scale. " + e)


	# Isolate the frame radiality (RAD/ARAD)
	try:
		FOUND_TEXT[RADIALITY] = ARAD if ARAD in text_segments else RAD
	except Exception as e:
		raise("Unable to isolate frame radiality. " + e)
	

	if image_type is IMAGE_TYPE.COLOR:

		FOUND_TEXT[COLOR_MODE] = IMAGE_TYPE.COLOR

		CPA_check = len([ segment for segment in text_segments if CPA in segment]) == 1
		COL_check = len([ segment for segment in text_segments if COLOR_LEVEL in segment]) == 1

		if not CPA_check ^ COL_check:
			raise IOError("Color/CPA text check did not pass for image")

		# Find the color mode

		found_mode = CPA if CPA_check else COLOR_LEVEL
		FOUND_TEXT[COLOR_MODE] = found_mode

		# Find the segment with CPA or COLOR
		
		mode_segment = [ segment for segment in text_segments if found_mode in segment][0]

		# Grab longest integer as color level percentage
		
		numerical_strings = [num_string for num_string in re.findall(r"[\d]+(?:\.[\d]+)*", mode_segment)]
		numerical_strings = [ns.replace(".", "") for ns in numerical_strings]
		color_level = int(max(numerical_strings, key=len))

		# A common transcription error with tesseract OCR is reading "8" as "3".
		# Expert knowledge says it is highly unlikely for the ultrasound operator to take a color
		# scan with power level below 50%. Therefore, manually adjust any "3" as leading digit to "8"

		if divmod(color_level, 10)[0] == 3:
			color_level = 80 + divmod(color_level, 10)[1]

		FOUND_TEXT[COLOR_LEVEL] = color_level

		# Find the segment with Wall Filter (WF)

		WF_check = len([ segment for segment in text_segments if WALL_FILTER in segment]) == 1

		if not WF_check:
			raise IOError("Wall filter check did not pass for image. Incorrect matching segments")

		wf_segment = [ segment for segment in text_segments if WALL_FILTER in segment][0]
		wf_segment = wf_segment.replace(WALL_FILTER, "").strip()

		if wf_segment not in WALL_FILTER_MODES:
			# Can always improve to levenshtein if poor matching
			raise IOError("Wall filter check did not pass for image. Incorrect mode: ${0}".format(wf_segment))

		FOUND_TEXT[WALL_FILTER] = wf_segment

		# Find the segment with Pulse Repitition Frequency (PRF)

		PRF_check = len([ segment for segment in text_segments if PRF in segment]) == 1

		if not PRF_check:
			raise IOError("PRF check did not pass for image. Incorrect matching segments")

		prf_segment = [ segment for segment in text_segments if PRF in segment][0]
		
		numerical_strings = [num_string for num_string in re.findall(r"[\d]+(?:\.[\d]+)*", prf_segment)]
		numerical_strings = [ns.replace(".", "") for ns in numerical_strings]
		FOUND_TEXT[PRF] = int(max(numerical_strings, key=len))

	return FOUND_TEXT

if __name__ == "__main__":


	# construct the argument parse and parse the arguments
	parser = argparse.ArgumentParser()

	parser.add_argument("-i",
                 "--image",
                 required=True,
                 help="path to input image to be OCR'd")

	parser.add_argument("-t",
                     "--image_type",
                     type=str,
                     default=IMAGE_TYPE.GRAYSCALE,
                     help="Image type (COLOR/GRAYSCALE)")

	args = parser.parse_args()

	# load the example image and convert it to grayscale
	image = cv2.imread(args.image)
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	gray = cv2.threshold(gray, 0, 255,
		cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
		
	print(isolate_text(
		gray, 
		args.image_type))
