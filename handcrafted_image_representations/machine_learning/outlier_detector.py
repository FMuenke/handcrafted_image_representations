import copy
import joblib
import numpy as np
from sklearn.model_selection import ParameterGrid
from handcrafted_image_representations.data_structure.data_set import DataSet
from handcrafted_image_representations import machine_learning as ml

import os
import shutil
from handcrafted_image_representations.utils.utils import check_n_make_dir, save_dict, load_dict
from handcrafted_image_representations.utils.outlier_removal import get_best_threshold

from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.gaussian_process import GaussianProcessClassifier, kernels

from sklearn.metrics import roc_auc_score, classification_report


class OutlierByGaussianProcess:
    def __init__(self):
        self.model = None

    def __str__(self):
        return "OutlierByGaussianProcess"

    def fit(self, x, y):
        self.model = GaussianProcessClassifier((1.0 * kernels.RBF(1.0)), n_jobs=-1)
        self.model.fit(x, y)

    def score_sample(self, x):
        proba = self.model.predict_proba(x)
        return np.max(proba, axis=1)

    def load(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        self.model = joblib.load(path_to_model)

    def save(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        if self.model is not None:
            joblib.dump(self.model, path_to_model)


class OutlierByRandomForest:
    def __init__(self):
        self.model = None

    def fit(self, x, y):
        self.model = RandomForestClassifier(n_jobs=-1)
        self.model.fit(x, y)

    def score_sample(self, x):
        proba = self.model.predict_proba(x)
        return np.max(proba, axis=1)

    def load(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        self.model = joblib.load(path_to_model)

    def save(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        if self.model is not None:
            joblib.dump(self.model, path_to_model)


class OutlierByIsolationForest:
    def __init__(self):
        self.model = None

    def fit(self, x, y):
        self.model = IsolationForest(n_jobs=-1)
        self.model.fit(x)

    def score_sample(self, x):
        return self.model.score_samples(x)

    def load(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        self.model = joblib.load(path_to_model)

    def save(self, path):
        path_to_model = os.path.join(path, "outlier_model.pkl")
        if self.model is not None:
            joblib.dump(self.model, path_to_model)


class OutlierByDistance:
    def __init__(self):
        self.x_mean = None
        self.x_std = None
        self.max_distance = None
        self.min_distance = None

    def __str__(self):
        return "OutlierByDistance"

    def compute_distance(self, x):
        distance = np.square((x - self.x_mean) / self.x_std)
        return np.sqrt(np.sum(distance, axis=1))

    def fit(self, x, y=None):
        self.x_mean = np.mean(x, axis=0)
        self.x_std = np.std(x, axis=0)
        self.x_std[self.x_std == 0.0] = 1e-9

        dist = self.compute_distance(x)
        self.max_distance = np.max(dist)
        self.min_distance = np.min(dist)

    def score_sample(self, x):
        return -1 * self.compute_distance(x)

    def predict(self, x):
        distance = self.compute_distance(x)
        prediction = np.zeros(distance.shape)
        prediction[distance > self.max_distance] = -1
        prediction[distance <= self.max_distance] = 1
        return prediction

    def save(self, path):
        param_path = os.path.join(path, "outlier_parameters.json")
        np.save(os.path.join(path, "outlier_param_x_mean.npy"), self.x_mean)
        np.save(os.path.join(path, "outlier_param_x_std.npy"), self.x_std)
        save_dict({
            "max_dist": int(self.max_distance),
            "min_dist": int(self.min_distance),
        }, param_path)

    def load(self, path):
        param_path = os.path.join(path, "outlier_parameters.json")
        param = load_dict(param_path)
        self.x_mean = np.load(os.path.join(path, "outlier_param_x_mean.npy"))
        self.x_std = np.load(os.path.join(path, "outlier_param_x_std.npy"))
        self.max_distance = int(param["max_dist"])
        self.min_distance = int(param["min_dist"])


class OutlierDetector:
    def __init__(self, opt=None, class_mapping=None):
        self.opt = opt
        self.class_mapping = class_mapping
        self.class_mapping_inv = None

        self.feature_extractor = None
        self.aggregator = None
        self.remover = None

    def new(self):
        self.feature_extractor = ml.FeatureExtractor(
            features_to_use=self.opt["feature"],
            image_height=self.opt["image_size"]["height"],
            image_width=self.opt["image_size"]["width"],
            sampling_method=self.opt["sampling_method"],
            sampling_steps=self.opt["sampling_step"],
            sampling_window=self.opt["sampling_window"]
        )
        self.aggregator = ml.Aggregator(self.opt)
        if self.opt["method"] == "by_classifier":
            self.remover = OutlierByGaussianProcess()
        else:
            self.remover = OutlierByDistance()

    def load(self, path):
        path_to_opt = os.path.join(path, "outlier_detector_opt.json")
        self.opt = load_dict(path_to_opt)
        path_to_class_mapping = os.path.join(path, "class_mapping.json")
        self.class_mapping = load_dict(path_to_class_mapping)
        self.class_mapping_inv = {v: k for k, v in self.class_mapping.items()}
        self.new()
        self.aggregator.load(path)
        self.remover.load(path)

    def evaluate(self, data_path_test, tag_type, results_path):
        print("[INFO] EVALUATING...")
        ds_test = DataSet(data_path_test, tag_type, self.class_mapping)
        ds_test.load_data()
        tags_test = ds_test.get_tags(classes_to_consider="all")

        x_test, y_test = self.feature_extractor.extract_trainings_data(tags_test)
        y_test = np.array(y_test)
        y_test[y_test != -1] = 1

        x_transformed_test = self.aggregator.transform(x_test)
        x_transformed_test = np.concatenate(x_transformed_test, axis=0)
        y_rm = self.remover.score_sample(x_transformed_test)
        score = roc_auc_score(y_test, y_rm)
        best_threshold = get_best_threshold(y_rm, y_test)

        s = ""
        s += "[RESULT]: AUROC {} / THRESHOLD: {}\n\n".format(score, best_threshold)

        remove_status = np.zeros(y_rm.shape)
        remove_status[y_rm >= best_threshold] = 1
        remove_status[y_rm < best_threshold] = -1
        s += str(classification_report(y_test, remove_status))

        print(s)
        with open(os.path.join(results_path, "outlier_report.txt"), "w") as f:
            f.write(s)

        path_wrongly_accepted = os.path.join(results_path, "wrongly_accepted")
        check_n_make_dir(path_wrongly_accepted)
        path_wrongly_rejected = os.path.join(results_path, "wrongly_rejected")
        check_n_make_dir(path_wrongly_rejected)
        for tag_id in tags_test:
            tag = tags_test[tag_id]
            if remove_status[tag_id] == -1 and y_test[tag_id] == 1:
                tag.export_box(path_wrongly_rejected)

            if remove_status[tag_id] == 1 and y_test[tag_id] == -1:
                tag.export_box(path_wrongly_accepted)


class OutlierDetectorAggregatorSearch:
    def __init__(self, opt, class_mapping):
        self.opt = opt
        self.class_mapping = class_mapping

        self.aggregator_opt = ["aggregator", "complexity"]

        self.feature_extractor = None
        self.aggregator_list = None
        self.remover_list = None
        self.remover = None

        self.final_aggregator = None
        self.final_remover = None

    def new(self):
        self.feature_extractor = ml.FeatureExtractor(
            features_to_use=self.opt["feature"],
            image_height=self.opt["image_size"]["height"],
            image_width=self.opt["image_size"]["width"],
            sampling_method=self.opt["sampling_method"],
            sampling_steps=self.opt["sampling_step"],
            sampling_window=self.opt["sampling_window"]
        )

        for k in self.aggregator_opt:
            if k not in self.opt:
                continue
            if type(self.opt[k]) is not list:
                self.opt[k] = [self.opt[k]]

        aggregator_opt_list = list(ParameterGrid({k: self.opt[k] for k in self.aggregator_opt if k in self.opt}))

        self.aggregator_list = [ml.Aggregator(opt) for opt in aggregator_opt_list]
        if self.opt["method"] == "by_classifier":
            self.remover = OutlierByGaussianProcess()
        else:
            self.remover = OutlierByDistance()

    def fit(self, model_folder, data_path_known, data_path_test, tag_type, report_path=None):
        self.new()
        best_score = 0
        best_candidate = None

        ds = DataSet(data_path_known, tag_type, self.class_mapping)
        ds.load_data()
        ds_test = DataSet(data_path_test, tag_type, self.class_mapping)
        ds_test.load_data()
        tags = ds.get_tags(self.class_mapping)
        tags_test = ds_test.get_tags(classes_to_consider="all")

        x, y = self.feature_extractor.extract_trainings_data(tags)
        x_test, y_test = self.feature_extractor.extract_trainings_data(tags_test)
        y_test = np.array(y_test)
        y_test[y_test != -1] = 1

        for aggregator in self.aggregator_list:
            x_transformed = aggregator.fit_transform(x)
            x_transformed_test = aggregator.transform(x_test)
            x_transformed = np.concatenate(x_transformed, axis=0)
            x_transformed_test = np.concatenate(x_transformed_test, axis=0)
            self.remover.fit(x_transformed, y)
            y_rm = self.remover.score_sample(x_transformed_test)
            score = roc_auc_score(y_test, y_rm)
            print("RUN: {} / {} - AUROC: {}".format(aggregator, self.remover, round(score, 3)))
            if score > best_score:
                best_score = score
                best_candidate = aggregator
                self.final_aggregator = aggregator
                self.final_remover = self.remover
                current_opt = copy.deepcopy(self.opt)
                for k in aggregator.opt:
                    current_opt[k] = best_candidate.opt[k]
                self.save(model_folder, current_opt)

        print("[RESULT] Best AUROC-Score: {}".format(best_score))
        for k in best_candidate.opt:
            print("[RESULT] ", k, self.opt[k], " --> ", best_candidate.opt[k])
            self.opt[k] = best_candidate.opt[k]
        return best_score

    def save(self, path, current_opt):
        check_n_make_dir(path)
        path_to_opt = os.path.join(path, "outlier_detector_opt.json")
        save_dict(current_opt, path_to_opt)
        path_to_class_mapping = os.path.join(path, "class_mapping.json")
        save_dict(self.class_mapping, path_to_class_mapping)
        self.final_aggregator.save(path)
        self.final_remover.save(path)


class OutlierDetectorSearch:
    def __init__(self, opt, class_mapping):
        self.opt = opt
        self.class_mapping = class_mapping

        self.feature_opt = ["feature", "sampling_method", "sampling_step", "sampling_window", "image_size"]

        self.model_list = None

    def new(self):

        for k in self.feature_opt:
            if k not in self.opt:
                continue
            if type(self.opt[k]) is not list:
                self.opt[k] = [self.opt[k]]

        feature_opt_list = list(ParameterGrid({k: self.opt[k] for k in self.feature_opt if k in self.opt}))

        for opt in feature_opt_list:
            for k in self.opt:
                if k not in opt:
                    opt[k] = self.opt[k]

        self.model_list = [OutlierDetectorAggregatorSearch(opt, self.class_mapping) for opt in feature_opt_list]

    def fit(self, model_folder, data_path_known, data_path_test, tag_type, report_path=None):
        self.new()

        best_score = 0
        best_candidate = None

        check_n_make_dir(model_folder)

        for i, model in enumerate(self.model_list):
            score = model.fit(
                os.path.join(model_folder, "version_{}".format(i)),
                data_path_known,
                data_path_test,
                tag_type,
                report_path=report_path
            )

            if score > best_score:
                best_candidate = i
                best_score = score

        print("[FINAL-RESULT] Best Model: {} ({})".format(best_candidate, best_score))
        for f in os.listdir(os.path.join(model_folder, "version_{}".format(best_candidate))):
            shutil.copy(
                os.path.join(model_folder, "version_{}".format(best_candidate), f),
                os.path.join(model_folder, f))
        return best_score
