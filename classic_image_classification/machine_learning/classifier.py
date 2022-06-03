import os
import joblib
import numpy as np
from time import time

from xgboost import XGBClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier

from imblearn.ensemble import BalancedRandomForestClassifier
from imblearn.ensemble import BalancedBaggingClassifier
from imblearn.ensemble import RUSBoostClassifier

from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.metrics import f1_score

from classic_image_classification.utils.utils import check_n_make_dir, save_dict, load_dict


class Classifier:
    def __init__(self, opt=None, class_mapping=None):
        self.opt = opt
        self.class_mapping = class_mapping
        self.class_mapping_inv = None

        self.classifier = None

        self.best_params = None
        self.best_score = None

    def __str__(self):
        return "Classifier: {}".format(self.opt["type"])

    def fit_single(self, x_train, y_train):
        self.new()
        print("Fitting the {} to the training set".format(self.opt["type"]))
        t0 = time()
        self.classifier.fit(x_train, y_train)
        print("done in %0.3fs" % (time() - t0))

    def fit(self, x_train, y_train):
        if "param_grid" in self.opt:
            self.classifier.fit_inc_hyper_parameter(x_train, y_train, self.opt["param_grid"], n_iter=100)
        else:
            self.classifier.fit(x_train, y_train)

    def fit_inc_hyper_parameter(self, x, y, param_set, scoring='f1_macro', cv=3, n_iter=None, n_jobs=-1):
        self.new()
        if n_iter is None:
            print(" ")
            print("Starting GridSearchCV:")
            searcher = GridSearchCV(self.classifier, param_set, scoring, n_jobs=n_jobs, cv=cv, verbose=2, refit=True)
        else:
            print(" ")
            print("Starting RandomizedSearchCV:")
            searcher = RandomizedSearchCV(self.classifier, param_set, n_iter=n_iter, cv=cv, verbose=2,
                                          random_state=42, n_jobs=n_jobs, scoring=scoring, refit=True)
        searcher.fit(x, y)
        self.best_params = searcher.best_params_
        self.best_score = searcher.best_score_
        self.classifier = searcher.best_estimator_

    def predict(self, x, get_confidence=False):
        if get_confidence:
            try:
                prob = self.classifier.predict_proba(x)
                return [np.argmax(prob)], np.max(prob)
            except:
                return self.classifier.predict(x), 1.00
        return self.classifier.predict(x)

    def evaluate(self, x_test, y_test, save_path=None, print_results=True):
        print("Predicting on the test set")
        t0 = time()
        y_pred = self.predict(x_test)
        print("done in %0.3fs" % (time() - t0))

        s = ""
        s += str(classification_report(y_test, y_pred, zero_division=0))
        s += "\nConfusion Matrix:\n"
        s += str(confusion_matrix(y_test, y_pred))
        if print_results:
            print(s)
        if save_path is not None:
            d = os.path.dirname(save_path)
            if not os.path.isdir(d):
                os.mkdir(d)
            with open(save_path, "w") as f:
                f.write(s)

        return f1_score(y_true=y_test, y_pred=y_pred, average="macro")

    def _init_classifier(self, opt):
        if "base_estimator" in opt:
            b_est = self._init_classifier(opt["base_estimator"])
        else:
            b_est = None

        if "n_estimators" in opt:
            n_estimators = opt["n_estimators"]
        else:
            n_estimators = 200

        if "max_iter" in opt:
            max_iter = opt["max_iter"]
        else:
            max_iter = 100000

        if "num_parallel_tree" in opt:
            num_parallel_tree = opt["num_parallel_tree"]
        else:
            num_parallel_tree = 5

        if "layer_structure" in opt:
            layer_structure = opt["layer_structure"]
        else:
            layer_structure = (100,)

        if opt["type"] in ["random_forrest", "rf"]:
            return RandomForestClassifier(n_estimators=n_estimators, class_weight="balanced", n_jobs=-1)
        elif opt["type"] == "ada_boost":
            return AdaBoostClassifier(base_estimator=b_est, n_estimators=n_estimators)
        elif opt["type"] in ["logistic_regression", "lr"]:
            return LogisticRegression(class_weight='balanced', max_iter=max_iter)
        elif opt["type"] == "sgd":
            return SGDClassifier(class_weight='balanced', max_iter=max_iter)
        elif opt["type"] in ["gaussian_bayes", "bayes", "gaussian_nb"]:
            return GaussianNB()
        elif opt["type"] in ["support_vector_machine", "svm"]:
            return SVC(kernel='rbf', class_weight='balanced', gamma="scale")
        elif opt["type"] in ["multilayer_perceptron", "mlp"]:
            return MLPClassifier(hidden_layer_sizes=layer_structure, max_iter=max_iter)
        elif opt["type"] in ["decision_tree", "dt", "tree"]:
            return DecisionTreeClassifier()
        elif opt["type"] in ["b_decision_tree", "b_dt", "b_tree"]:
            return DecisionTreeClassifier(class_weight="balanced")
        elif opt["type"] in ["neighbours", "knn"]:
            return KNeighborsClassifier(n_neighbors=opt["n_neighbours"])
        elif opt["type"] == "extra_tree":
            return ExtraTreesClassifier(n_estimators=n_estimators, class_weight="balanced", n_jobs=-1)
        elif opt["type"] == "xgboost":
            return XGBClassifier(objective='binary:logistic',
                                 n_estimators=n_estimators,
                                 num_parallel_tree=num_parallel_tree,
                                 tree_method="hist",
                                 booster="gbtree",
                                 n_jobs=-1)
        elif opt["type"] in ["b_random_forrest", "b_rf"]:
            return BalancedRandomForestClassifier(n_estimators=n_estimators, n_jobs=-1)
        elif opt["type"] == "b_bagging":
            return BalancedBaggingClassifier(base_estimator=b_est, n_estimators=n_estimators)
        elif opt["type"] == "b_boosting":
            return RUSBoostClassifier(base_estimator=b_est, n_estimators=n_estimators)
        else:
            raise ValueError("type: {} not recognised".format(opt["type"]))

    def new(self):
        self.classifier = self._init_classifier(self.opt)

    def load(self, model_path):
        path_to_class_mapping = os.path.join(model_path, "class_mapping.json")
        path_to_pipeline_opt = os.path.join(model_path, "pipeline_opt.json")
        path_to_classifier = os.path.join(model_path, "classifier.pkl")
        self.class_mapping = load_dict(path_to_class_mapping)
        self.opt = load_dict(path_to_pipeline_opt)
        self.classifier = joblib.load(path_to_classifier)
        if self.class_mapping is not None:
            self.class_mapping_inv = {v: k for k, v in self.class_mapping.items()}
        print("Classifier was loaded!")

    def save(self, model_path):
        path_to_class_mapping = os.path.join(model_path, "class_mapping.json")
        path_to_pipeline_opt = os.path.join(model_path, "pipeline_opt.json")
        path_to_classifier = os.path.join(model_path, "classifier.pkl")
        check_n_make_dir(model_path, clean=True)
        save_dict(self.class_mapping, path_to_class_mapping)
        save_dict(self.opt, path_to_pipeline_opt)
        if self.classifier is not None:
            joblib.dump(self.classifier, path_to_classifier)