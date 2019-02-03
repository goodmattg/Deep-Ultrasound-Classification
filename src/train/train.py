import tensorflow as tf
import json
import yaml


from dotmap import DotMap
from datetime import datetime
from importlib import import_module

from tensorflow.python.lib.io import file_io
from tensorflow.python.framework.errors_impl import NotFoundError
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from src.utilities.partition.patient_partition import patient_train_test_split
from src.utilities.general.general import default_none

DEFAULT_CONFIG = "src/config/default.yaml"

def train_model(args):

    BENIGN_TOP_LEVEL_PATH = args.images + "/Benign"
    MALIGNANT_TOP_LEVEL_PATH = args.images + "/Malignant"

    # Establish logging
    logs_path = args.job_dir + '/logs/' + datetime.now().isoformat()

    # Load the configuration file yaml file if provided
    config_file = default_none(args.config, DEFAULT_CONFIG)
    try:
        with file_io.FileIO(config_file, mode='r') as stream:
            config = DotMap(yaml.load(stream))
    except NotFoundError as _:
        print("Configuration file not found: {0}".format(config_file))
        return
    except Exception as _:
        print("Unable to load configuration file: {0}".format(config_file))
        return

    # Load the manifest file
    try:
        with file_io.FileIO(args.manifest, mode='r') as stream:
            manifest = json.load(stream)
    except NotFoundError as _:
        print("Manifest file not found: {0}".format(args.manifest))
        return
    except Exception as _:
        print("Unable to load manifest file: {0}".format(args.manifest))
        return

    # Train/test split according to config
    patient_split = DotMap(patient_train_test_split(
        BENIGN_TOP_LEVEL_PATH,
        MALIGNANT_TOP_LEVEL_PATH,
        config.train_split,
        config.random_seed
    ))

    image_data_generator = ImageDataGenerator(**config.image_preprocessing.toDict())

    # THESE ARE INCORRECT
    training_sample_generator = PatientSampleGenerator(
        patient_split.train,
        BENIGN_TOP_LEVEL_PATH,
        BENIGN_TOP_LEVEL_PATH,
        manifest,
        target_shape = config.target_shape,
        batch_size = config.batch_size,
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
        batch_size = config.batch_size,
        image_type = image_type,
        image_data_generator = image_data_generator,
        timestamp = timestamp,
        kill_on_last_patient = True)
        

    # Load the model specified in config
    model = import_module("src.models.{0}".format(config.model)).get_model(config)
    
    model.fit_generator(

    )
    # Train the provided model according to the configuration
    # Fail on model load failure

    # Evaluate the model

    # Save the model
    # model.save(config.identifier)
    
    # # Save the model on GC storage
    # with file_io.FileIO(config.identifier, mode='r') as input_f:
    #     with file_io.FileIO(args.job_dir + "/{0}".format(config.identifier), mode='w+') as output_f:
    #         output_f.write(input_f.read())

    return