import logging
import argparse
from handcrafted_image_representations import ImageClassifier
from handcrafted_image_representations.utils.utils import load_dict


def main(args_):

    class_mapping = load_dict(args_.class_mapping)
    mf = args_.model_folder
    df = args_.dataset_folder
    tf = args_.test_folder

    cls = ImageClassifier(class_mapping=class_mapping)
    cls.fit(df, tag_type=args_.dataset_type)
    cls.save(mf)
    cls.evaluate(tf, tag_type="cls", report_path=mf)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset_folder",
        "-df",
        help="Path to directory with dataset",
    )
    parser.add_argument(
        "--test_folder",
        "-tf",
        default=None,
        help="Path to directory with test dataset",
    )
    parser.add_argument(
        "--dataset_type",
        "-dtype",
        default="cls",
        help="Choose Dataset Annotation Bounding-Boxes [box] or Image Labels [cls]",
    )
    parser.add_argument(
        "--model_folder",
        "-model",
        help="Path to model",
    )
    parser.add_argument(
        "--class_mapping",
        "-clmp",
        help="Path to class mapping JSON",
    )
    parser.add_argument(
        "--use_cache",
        "-cache",
        type=bool,
        default=False,
        help="Save the Calculated Features in _cache folder",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    args = parse_args()
    main(args)
