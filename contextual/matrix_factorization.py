# Some of the code inspired by http://katbailey.github.io/post/matrix-factorization-with-tensorflow/

from __future__ import division
from __future__ import print_function

import os
import util

import numpy as np
import tensorflow as tf
import rpy2.robjects as robjects

from sklearn.cross_validation import train_test_split
from rpy2.robjects import numpy2ri

from matrix_factorizer import MatrixFactorizer


class MatrixFactorization(object):
    def __init__(self, data_path):
        ratings = self._load_ratings(data_path)
        self._config = config_tr = Config(ratings)
        config_eval = Config(ratings)

        #values, mean_value = self._explicit_data(ratings)
        values, mean_value = self._implicit_data()
        self._mean_value = mean_value

        with tf.Graph().as_default(), tf.Session() as session:
            initializer = tf.random_uniform_initializer(-0.1, 0.1)
            with tf.variable_scope("model", reuse=None, initializer=initializer):
                model = MatrixFactorizer(True, config_tr)
            with tf.variable_scope("model", reuse=True, initializer=initializer):
                model_eval = MatrixFactorizer(False, config_eval)

            tf.initialize_all_variables().run()

            for i in range(config_tr.max_steps):
                if i % 500 == 0:
                    res = session.run([model.cost],
                                      {model.mean_rating: mean_value,
                                       model.input: values}
                                      )
                    av_err = res[0]

                    print("Training - Cost: %s" % av_err)

                    res = session.run([model_eval.cost],
                                      {model_eval.mean_rating: mean_value,
                                       model_eval.input: values}
                                      )
                    av_err_eval = res[0]
                    print("Evaluation - Cost: %s" % av_err_eval)
                else:
                    session.run(model.train_op,
                                {model.mean_rating: mean_value,
                                 model.input: values}
                                )

            output = model.output
            self._R = output['R'].eval()
            self._P = output['P'].eval()
            self._Q = tf.transpose(output['Q']).eval()

    def _explicit_data(self, ratings):
        rating_values = np.array([rating[2] for rating in ratings], dtype=np.float32)
        mean_rating = np.mean(rating_values)

        #ratings_tr, ratings_val = train_test_split(ratings)
        #rating_values_tr = np.array([rating[2] for rating in ratings_tr], dtype=np.float32)
        #rating_values_eval = np.array([rating[2] for rating in ratings_val], dtype=np.float32)

        return rating_values, mean_rating

    def _implicit_data(self):
        return np.ones([self.config.num_ratings]), 0

    def _load_ratings(self, data_path):
        robjects.r['load'](os.path.join(data_path, "ratings-100k.RData"))
        return numpy2ri.ri2py(robjects.r['ratings_df'])

    @property
    def R(self):
        return self._R

    @property
    def Q(self):
        return self._Q

    @property
    def P(self):
        return self._P

    @property
    def config(self):
        return self._config


class Config(object):
    def __init__(self, ratings):
        self.max_steps = 10
        self.learning_rate = 0.9 #0.01
        self.mu = 0.0 # 0.1
        self.rank = 10
        self.num_ratings = len(ratings)
        self.user_indices = [np.int32(rating[0]) for rating in ratings]
        self.item_indices = [np.int32(rating[1]) for rating in ratings]

        self.num_users = len(util.unique(self.user_indices))
        self.num_items = len(util.unique(self.item_indices))