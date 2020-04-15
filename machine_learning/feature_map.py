import numpy as np

from datastructure.matrix_handler import MatrixHandler


class FeatureMap:
    def __init__(self, feature_map):
        self.feature_map = feature_map

    def set_to_resolution(self, resolution):
        mat = MatrixHandler(self.feature_map)
        return resolution * mat.normalize()

    def to_descriptors_with_histogram(self, key_points, resolution):
        descriptors = []
        mat = MatrixHandler(self.set_to_resolution(resolution))
        for x, y, s in key_points:
            roi = mat.cut_roi([x, y], s)
            desc, bins = np.histogram(roi.ravel(),
                                      range=[0,
                                             resolution],
                                      bins=resolution,
                                      density=True)
            desc = np.reshape(desc, (1, -1))
            descriptors.append(desc)
        if len(descriptors) == 0:
            return None
        elif len(descriptors) == 1:
            return descriptors[0]
        else:
            return np.concatenate(descriptors, axis=0)

    def to_descriptor_with_pooling(self, key_points, pooling_mode):
        descriptors = []
        mat_h_f_map = MatrixHandler(self.feature_map)
        for x, y, s in key_points:
            roi = mat_h_f_map.cut_roi([x, y], s)
            mat_h_roi = MatrixHandler(roi)
            descriptors.append(mat_h_roi.global_pooling(pooling_mode=pooling_mode))
        return np.concatenate(descriptors, axis=0)
