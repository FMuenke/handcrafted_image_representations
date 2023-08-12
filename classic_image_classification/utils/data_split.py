import numpy as np


def split_random(list_of_tags, ratio=0.2):
    train_tags = []
    test_tags = []

    for tag in list_of_tags:
        if np.random.randint(100) / 100 > ratio:
            train_tags.append(tag)
        else:
            test_tags.append(tag)

    return train_tags, test_tags


def split_fixed(list_of_tags, ratio=0.2):
    train_tags = []
    test_tags = []

    for i, tag in enumerate(list_of_tags):
        if i / 100 >= ratio:
            train_tags.append(tag)
        else:
            test_tags.append(tag)

    return train_tags, test_tags


def split_tags(list_of_tags, ratio=0.2, mode="random"):
    if mode == "random":
        return split_random(list_of_tags, ratio)
    elif mode == "fixed":
        return split_fixed(list_of_tags, ratio)
    else:
        raise Exception("Unknown mode - {} -".format(mode))
