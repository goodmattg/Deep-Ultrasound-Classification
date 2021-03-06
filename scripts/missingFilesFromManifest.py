import argparse
import json
import os

def check_missing_files(args):

    with open (args["manifest"]) as f:
        manifest = json.load(f)

    missing_files = []

    # Searching for grayscale images that are listed in the manifest but the files do not exist
    for k in manifest:
        for frame in manifest[k]:
            src = "{0}/{1}/{2}/{3}".format(args["source"], frame["TUMOR_TYPE"], k, frame["FRAME"])
            if not os.path.isfile(src):
                missing_files.append("{0}: {1}".format(k, frame["FRAME"]))
    
    # We assert that no files are missing w.r.t the manifest
    assert len(missing_files) == 0

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-M",
        "--manifest",
        help="Path to manifest",
        required=True
    )

    parser.add_argument(
        "-S",
        "--source",
        help="Path to source data directory",
        required=True
    )

    args = parser.parse_args()
    check_missing_files(args.__dict__)