import cv2
import numpy as np
from tqdm import tqdm

from handcrafted_image_representations.machine_learning.descriptor_set import DescriptorSet
from handcrafted_image_representations.machine_learning.key_point_set import KeyPointSet


def validate_feature_extraction_settings(sampling_method, features_to_use):
    if sampling_method not in ["kaze", "akaze"] and "kaze" in features_to_use:
        print("[WARNING] Features KAZE are only compatible with KAZE key points")
        print("[WARNING] Sampling Method was changed to - kaze -")
        return "kaze", features_to_use

    if sampling_method == "sift" and "sift" not in features_to_use:
        print("[WARNING] Sampling Method SIFT is only compatible with SIFT features")
        print("[WARNING] Sampling Method was changed to - kaze -")
        return "kaze", features_to_use
    return sampling_method, features_to_use


class FeatureExtractor:
    def __init__(self,
                 features_to_use,
                 normalize=True,
                 sampling_method="dense",
                 sampling_steps=20,
                 sampling_window=20,
                 image_height=None,
                 image_width=None,
                 resize_option="standard",
                 ):

        sampling_method, features_to_use = validate_feature_extraction_settings(sampling_method, features_to_use)
        if type(features_to_use) is not list():
            features_to_use = [features_to_use]
        self.features_to_use = features_to_use
        self.normalize = normalize
        self.sampling_method = sampling_method
        self.sampling_steps = sampling_steps
        self.sampling_window = sampling_window
        self.resize_option = resize_option

        self.img_height = image_height
        self.img_width = image_width

    def describe_sampling(self):
        if self.sampling_method == "dense":
            return "{} - IMG:{}/{} DENSE: W:{}/S:{}".format(
                self.features_to_use,
                self.img_height,
                self.img_width,
                self.sampling_window,
                self.sampling_steps
            )
        else:
            return "{} - IMG:{}/{} - {}".format(
                self.features_to_use,
                self.img_height,
                self.img_width,
                self.sampling_method
            )

    def resize(self, image, height, width):
        if height is None and width is None:
            return image
        
        o_height, o_width = image.shape[:2]

        if height < 1 or width < 1:
            height = int(o_height * height)
            width = int(o_width * width)
            return cv2.resize(
                image,
                (int(width), int(height)),
                interpolation=cv2.INTER_CUBIC
            )
        
        if height is None:
            height = int(o_height * (width / o_width))
        if width is None:
            width = int(o_width * (height / o_height))
        return cv2.resize(
            image,
            (int(width), int(height)),
            interpolation=cv2.INTER_CUBIC
        )

    def extract_trainings_data(self, tags):
        x, y = [], []
        print("[INFO] Extracting Features: [{}] for Tags".format(self.describe_sampling()))
        for tag in tqdm(tags):
            tag_data = tag.load_data()
            x_tag = self.extract_x(tag_data)
            y_tag = tag.load_y()

            x.append(x_tag)
            y.append(y_tag)
        assert x is not None, "No Feature was activated"
        return x, y

    def extract_x(self, image):
        kp_set = KeyPointSet(self.sampling_method, self.sampling_steps, self.sampling_window)
        image = self.resize(image, self.img_height, self.img_width)
        x = []
        for feature in self.features_to_use:
            dc_set = DescriptorSet(feature)
            dc_x = dc_set.compute(image, kp_set)
            if dc_x is None:
                continue
            x.append(dc_x)
        if len(x) == 0:
            return None
        if len(x) == 1:
            return x[0]
        return np.concatenate(x, axis=1)
