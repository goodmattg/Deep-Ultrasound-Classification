import argparse
import json
import logging
import uuid

import numpy as np
import tensorflow as tf

from tqdm import tqdm
from utilities.partition.patient_partition import patient_train_test_validation_split
from pipeline.patientsample.patient_sample_generator import PatientSampleGenerator

from constants.exceptions.customExceptions import ExtractSavePatientFeatureException

from constants.ultrasound import (
    IMAGE_TYPE,
    NUMBER_CHANNELS_COLOR,
    NUMBER_CHANNELS_GRAYSCALE)

from constants.model import (
    DEFAULT_BATCH_SIZE,
    RESNET50_REQUIRED_NUMBER_CHANNELS,
    SAMPLE_WIDTH,
    SAMPLE_HEIGHT,
    INCEPTION_RESNET_V2_WIDTH,
    INCEPTION_RESNET_V2_HEIGHT,
    RESNET_50_HEIGHT,
    RESNET_50_WIDTH)
    
from tensorflow.keras.models import Model
from tensorflow.keras.applications import inception_resnet_v2
from tensorflow.keras.applications import resnet50
from tensorflow.keras.preprocessing.image import ImageDataGenerator

logger = logging.getLogger('research')

def extract_save_patient_features(
    benign_top_level_path, 
    malignant_top_level_path, 
    manifest_path, 
    output_directory_path,
    batch_size=DEFAULT_BATCH_SIZE,
    image_data_generator=None,
    image_type=IMAGE_TYPE.ALL,
    target_shape=[RESNET_50_HEIGHT, RESNET_50_WIDTH],
    timestamp=None,
    override_filename_prefix=None):
    """Builds and saves a Numpy dataset with neural network extracted features

    Arguments:
        benign_top_level_path                absolute path to benign directory
        malignant_top_level_path             absolute path to malignant directory
        manifest_path                        absolute path to JSON manifest
        output_directory_path                absolute path to output directory

    Optional:
        batch_size                           number of samples to take from each input frame (default 16)
        image_data_generator                 preprocessing generator to run on input images
        image_type                           type of image frames to process (IMAGE_TYPE Enum). i.e. grayscale or color
        target_shape                         array containing target shape to use for output samples [rows, columns]. 
                                                No channel dimension should be included.
        
        timestamp                            timestamp string to append in focus directory path. 
                                                i.e. ***/focus_{timestamp}/***
    Returns:
        Integer status code. Zero indicates clean processing and write to file. 
        Non-zero indicates error in feature generation script. 

    Raises:
        PatientSampleGeneratorException      for any error generating sample batches
    """

    try:
        
        # When include_top=True input shape must be 224,224
        # TODO: This should be part of a generic configuration
        base_model = resnet50.ResNet50(
            include_top=True,
            classes=2,
            weights=None)

        # base_model = inception_resnet_v2.InceptionResNetV2(
        #     include_top=True,
        #     classes=2,
        #     weights=None)

        # Pre-softmax layer may be way too late
        model = Model(
            input=base_model.input,
            output=base_model.get_layer('avg_pool').output)

        # Load the patient manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f) 

        # Generate a random patient partition. Split the partition the data into train and test partitions.
        # Shuffle the patients as best practice to prevent even out training over classes

        partition = patient_train_test_validation_split(
            benign_top_level_path,
            malignant_top_level_path,
            include_validation = False)

        image_data_generator = ImageDataGenerator(
            featurewise_center=True,
            featurewise_std_normalization=True,
            horizontal_flip=True,
            vertical_flip=True)

        training_partition = partition["benign_train"] + partition["malignant_train"]
        test_partition = partition["benign_test"] + partition["malignant_test"]

        np.random.shuffle(training_partition)
        np.random.shuffle(test_partition)

        logging.info("Training Partition: {}".format(len(training_partition)))
        logging.info("Test Partition: {}".format(len(test_partition)))

        # Instantiate generators over training/test/(validation) partitions

        training_sample_generator = PatientSampleGenerator(
            training_partition,
            benign_top_level_path,
            malignant_top_level_path,
            manifest,
            target_shape = target_shape,
            batch_size = batch_size,
            image_type = image_type,
            image_data_generator = image_data_generator,
            timestamp = timestamp,
            kill_on_last_patient = True)

        test_sample_generator = PatientSampleGenerator(
            test_partition,
            benign_top_level_path,
            malignant_top_level_path,
            manifest,
            target_shape = target_shape,
            batch_size = batch_size,
            image_type = image_type,
            image_data_generator = image_data_generator,
            timestamp = timestamp,
            kill_on_last_patient = True)
        
        training_count = training_sample_generator.total_num_cleared_frames
        test_count = test_sample_generator.total_num_cleared_frames
        print("Training Count: {}".format(training_count))
        print("Test Count: {}".format(test_count))
        
        training_gen = next(training_sample_generator)
        test_gen = next(test_sample_generator)

        # Set feature/label matrices in outer scope
        X_training = X_test = y_training = y_test = None
       
        PREALLOCATE_FLAG = True

        # Extract training features
        for bx in tqdm(range(training_count), desc="TRAINING Feature Extraction"):
            current_batch = next(training_gen)
            current_features = np.squeeze(model.predict(current_batch[0]))
            current_classes = current_batch[1]

            if PREALLOCATE_FLAG:
                print("Features shape determined to be: {}".format(current_features.shape))
                print("Compressed feature shape: {}".format(np.squeeze(current_features).shape))
                print("Sample classes shape: {}".format(current_batch[1].shape))

                output_feature_shape = np.squeeze(current_features).shape

                ## Preallocate output feature matrix
                X_training = np.empty((batch_size * training_count, output_feature_shape[1]))
                X_test = np.empty((batch_size * test_count, output_feature_shape[1]))
                print("Final training features output shape: {}".format(X_training.shape))
                print("Final test features output shape: {}".format(X_test.shape))
            
                y_training = np.empty(training_count * batch_size)
                y_test = np.empty(test_count * batch_size)
                print("Final training classes output shape: {}".format(y_training.shape))
                print("Final test classes output shape: {}".format(y_test.shape))

                PREALLOCATE_FLAG = False

            X_training[batch_size*bx:batch_size*(bx+1), :] = current_features
            y_training[batch_size*bx:batch_size*(bx+1)] = current_classes

        # Extract test features
        for bx in tqdm(range(test_count), desc="TEST Feature Extraction"):
            current_batch = next(test_gen)
            current_features = np.squeeze(model.predict(current_batch[0]))
            current_classes = current_batch[1]

            X_test[batch_size*bx:batch_size*(bx+1), :] = current_features
            y_test[batch_size*bx:batch_size*(bx+1)] = current_classes

        output_hash = uuid.uuid4()

        if override_filename_prefix is not None:
            output_filename = "{}/{}.npy".format(output_directory_path, override_filename_prefix)
        else:
            output_filename = "{}/features_{}_{}.npy".format(output_directory_path, timestamp, output_hash)

        # TODO: Should probably add a hash to the output of this function
        with open(output_filename, "wb") as f:
            data = {
                "test_features": X_test, 
                "test_labels": y_test,
                "test_partition": test_partition,
                "test_count": test_count,
                "training_features": X_training,
                "training_labels": y_training,
                "training_partition": training_partition,
                "training_count": training_count
            }
            np.save(f, data)
            logging.info("Saved generated features to output directory. Output hash: {}".format(output_hash))

        return output_hash

    except Exception as e:
        logging.critical(e)
        return 1
