from constants.ultrasoundConstants import (
    IMAGE_TYPE,
    IMAGE_TYPE_LABEL,
    TUMOR_BENIGN,
    TUMOR_MALIGNANT,
    TUMOR_TYPE_LABEL,
    FOCUS_HASH_LABEL)
from constants.modelConstants import DEFAULT_BATCH_SIZE
from utilities.imageUtilities import image_random_sampling_batch
from keras.preprocessing.image import ImageDataGenerator
from constants.exceptions.customExceptions import PatientSampleGeneratorException
import numpy as np
import cv2, os, json

class PatientSampleGenerator:
    """Generator that returns batches of samples for training and evaluation
    
    Arguments:
        patient_list: list of patients. Patient is tuple (patientId, TUMOR_TYPE)
        benign_top_level_path: absolute path to benign directory
        malignant_top_level_path: absolute path to malignant directory
        manifest: dictionary parsed from JSON containing all information from image OCR, tumor types, etc
        batch_size: (optional) number of images to output in a batch
        image_data_generator: (optional) preprocessing generator to run on input images
        image_type: (optional) type of image frames to process (IMAGE_TYPE Enum). i.e. grayscale or color
        timestamp: (optional) optional timestamp string to append in focus directory path. i.e. "*/focus_timestamp/*

    Returns:
        Tuple containing ((batch_size, (target_shape)), [labels]) where the labels array is length batch_size 

    Raises:
        PatientSampleGeneratorException for any error generating sample batches
    """

    def __init__(self, 
        patient_list, 
        benign_top_level_path, 
        malignant_top_level_path, 
        manifest, 
        batch_size=DEFAULT_BATCH_SIZE,
        image_data_generator=None,
        image_type=IMAGE_TYPE.COLOR, 
        timestamp=None):
        
        self.image_type = image_type
        self.raw_patient_list = patient_list
        self.manifest = manifest
        self.benign_top_level_path = benign_top_level_path
        self.malignant_top_level_path = malignant_top_level_path
        self.timestamp = timestamp
        self.image_data_generator = image_data_generator
        self.batch_size = batch_size

        # Find all the patientIds with at least one frame in the specified IMAGE_TYPE

        cleared_patients = list(filter(
            lambda patient: any([frame[IMAGE_TYPE_LABEL] == image_type.value for frame in manifest[patient]]), 
            [patient[0] for patient in patient_list]))

        if len(cleared_patients) == 0:
            raise PatientSampleGeneratorException(
                "No patients found with focus in image type: {0}".format(self.image_type.value))
        
        self.cleared_patients = cleared_patients
        self.patient_index = self.frame_index = 0

        self.__update_current_patient_information()


    def __update_current_patient_information(self):
        """Private method to update current patient information based on patient_index"""
        self.patient_id = self.cleared_patients[self.patient_index]
        self.patient_record = self.manifest[self.patient_id]
        self.patient_type = self.patient_record[0][TUMOR_TYPE_LABEL]

        # Find all patient's frames matching the specified image type

        self.patient_frames = list(filter(
            lambda frame: frame[IMAGE_TYPE_LABEL] == self.image_type.value,
            self.manifest[self.cleared_patients[self.patient_index]]
        ))


    def __next__(self):

        while True:


            skip_flag = False
            is_last_frame = self.frame_index == len(self.patient_frames) - 1

            # print("{}/{}/{}/{}".format(
            #     (self.benign_top_level_path if self.patient_type == TUMOR_BENIGN else self.malignant_top_level_path),
            #     self.patient_id,
            #     ("focus" if self.timestamp is None else "focus_{}".format(self.timestamp)),
            #     self.patient_frames[self.frame_index][FOCUS_HASH_LABEL]
            # ))

            loaded_image = cv2.imread("{}/{}/{}/{}".format(
                (self.benign_top_level_path if self.patient_type == TUMOR_BENIGN else self.malignant_top_level_path),
                self.patient_id,
                ("focus" if self.timestamp is None else "focus_{}".format(self.timestamp)),
                self.patient_frames[self.frame_index][FOCUS_HASH_LABEL]
            ),
                (cv2.IMREAD_COLOR if self.image_type.value == IMAGE_TYPE.COLOR.value else cv2.IMREAD_GRAYSCALE))

            if loaded_image is None:
                skip_flag = True
            elif len(loaded_image.shape) < 3 or loaded_image.shape[0] < 224 or loaded_image.shape[1] < 224:
                # print(loaded_image.shape)
                skip_flag = True
            else:
                print("Training on patient: {} | frame: {}".format(self.patient_id, self.frame_index))
                # Produce a randomly sampled batch from the focus image

                min_non_channel_dim = np.min(loaded_image.shape[:2]) # assumes image format channel_last
                raw_image_batch = image_random_sampling_batch(
                    loaded_image, 
                    target_shape=(224, 224, 3),
                    batch_size=self.batch_size)

                frame_label = self.patient_frames[self.frame_index][TUMOR_TYPE_LABEL]
                frame_label = 0 if frame_label == TUMOR_BENIGN else 1

            if not is_last_frame:
                self.frame_index += 1
            else:
                self.patient_index += 1
                self.frame_index = 0
                self.__update_current_patient_information()
           
            if not skip_flag:
                print("Batch shape: {} | label: {}".format(raw_image_batch.shape, frame_label))
                yield (raw_image_batch, np.repeat(frame_label, self.batch_size))
            else:
                continue

        return

if __name__ == "__main__":

    dirname = os.path.dirname(__file__)

    with open(os.path.abspath("processedData//manifest_COMPLETE_2018-07-11_18-51-03.json"), "r") as fp:
        manifest = json.load(fp)

    patient_sample_generator = next(PatientSampleGenerator(
        [("00BER3003855", "BENIGN"), ("01PER2043096", "BENIGN")],
        os.path.join(dirname, "../../100_Cases/ComprehensiveMaBenign/Benign"),
        os.path.join(dirname, "../../100_Cases/ComprehensiveMaBenign/Malignant"),
        manifest,
        image_type=IMAGE_TYPE.COLOR,
        timestamp="2018-07-11_18-51-03"))

    # gen = 
    raw_image_batch, labels = next(patient_sample_generator)

    for i in range(16):
        cv2.imshow(str(labels[i]), raw_image_batch[i])
        cv2.waitKey(0)    

    raw_image_batch, labels = next(patient_sample_generator)


    for i in range(16):
        cv2.imshow(str(labels[i]), raw_image_batch[i])
        cv2.waitKey(0)    

    raw_image_batch, labels = next(patient_sample_generator)


    for i in range(16):
        cv2.imshow(str(labels[i]), raw_image_batch[i])
        cv2.waitKey(0)    

    raw_image_batch, labels = next(patient_sample_generator)

    for i in range(16):
        cv2.imshow(str(labels[i]), raw_image_batch[i])
        cv2.waitKey(0)    