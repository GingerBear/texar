"""
Trainer for classifier.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import cPickle as pkl
import numpy as np
import tensorflow as tf
import json
import os

from texar.hyperparams import HParams
from texar.models.tsf import TSF
from texar.models.classifier import Classifier

from trainer_base import TrainerBase
from utils import *
from classifier_utils import *
from stats import Stats

class ClassifierTrainer(TrainerBase):
  """Classifier Trainer."""
  def __init__(self, hparams=None):
    TrainerBase.__init__(self, hparams)

  @staticmethod
  def default_hparams():
    return {
      
    }

  def prepare_data(self, train, val, test):
    train_x = train[0] + train[1]
    train_y = [0] * len(train[0]) + [1] * len(train[1])
    val_x = val[0] + val[1]
    val_y = [0] * len(val[0]) + [1] * len(val[1])
    test_x = test[0] + test[1]
    test_y = [0] * len(test[0]) + [1] * len(test[1])
    return (train_x, train_y), (val_x, val_y), (test_x, test_y)

  def eval_model(self, model, sess, vocab, x, y):
    batches = get_batches(x, y, vocab["word2id"], self._hparams.batch_size)
    probs = []
    losses = []
    for batch in batches:
      loss, prob = model.eval_step(sess, batch)
      losses += loss[:batch["actual_size"]]
      probs += prob.tolist()[:batch["actual_size"]]
    y_hat = [ p > 0.5 for p in probs]
    same = [ p == q for p, q in zip(y, y_hat)]
    loss = sum(losses) / len(losses)
    accu = 100*sum(same) / len(y)
    return loss, accu

  def train(self):
    if "config" in self._hparams.keys():
      with open(self._hparams.config) as f:
        self._hparams = HParams(pkl.load(f))

    log_print("Start training with hparams:")
    log_print(json.dumps(self._hparams.todict(), indent=2))
    if not "config" in self._hparams.keys():
      with open(os.path.join(self._hparams.expt_dir, self._hparams.name)
                + ".config", "w") as f:
        pkl.dump(self._hparams, f)

    vocab, train, val, test = self.load_data()
    train, val, test = self.prepare_data(train, val, test)

    # set vocab size
    self._hparams.vocab_size = vocab["size"]

    with tf.Session() as sess:
      model = Classifier(self._hparams)
      log_print("finished building model")

      if "model" in self._hparams.keys():
        model.saver.restore(sess, self._hparams.model)
      else:
        sess.run(tf.global_variables_initializer())
        sess.run(tf.local_variables_initializer())


      best_dev = float("-inf")
      loss = 0.
      accu = 0.
      step = 0
      batches = get_batches(train[0], train[1], self._hparams.batch_size,
                            shuffle=True)
      
      log_dir = os.path.join(self._hparams.expt_dir, self._hparams.log_dir)
      train_writer = tf.summary.FileWriter(log_dir, sess.graph)

      for epoch in range(1, self._hparams.max_epoch + 1):
        # shuffle across batches
        log_print("------------------epoch %d --------------"%(epoch))
        log_print("gamma %.3f"%(gamma))
        random.shuffle(batches)

        for batch in batches:
          step_loss, step_accu = model.train_step(sess, batch)

          step += 1
          loss += step_loss / self._hparams.disp_interval
          accu += accu / self._hparams.disp_interval
          if step % self._hparams.disp_interval == 0:
            log_print("step %d: loss %.2f accu %.3f "%(step), loss, accu )
            loss = 0.
            accu = 0.


        dev_loss, dev_accu = self.eval_model(
          model, sess, vocab, val[0], val[1])
        if dev_accu > best_dev:
          best_dev = dev_accu
          file_name = (
            self._hparams["name"] + "_" + "%.3f" %(best_dev) + ".model")
          model.saver.save(
            sess, os.path.join(self._hparams['expt_dir'], file_name),
            latest_filename=self._hparams['name'] + '_checkpoint',
            global_step=step)
          log_print("saved model %s"%(file_name))

    return best_dev


def main(unused_args):
  trainer = ClassifierTrainer()
  trainer.train()

if __name__ == "__main__":
  tf.app.run()









