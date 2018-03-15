#
"""
Various classifier classes.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# pylint: disable=not-context-manager, too-many-arguments, too-many-locals
# pylint: disable=protected-access

import tensorflow as tf

from texar.utils.exceptions import TexarError
from texar.modules.classifiers.classifier_base import ClassifierBase
from texar.modules.encoders.conv_encoders import Conv1DEncoder

__all__ = [
    "Conv1DClassifier"
]


class Conv1DClassifier(ClassifierBase):
    """Simple Conv-1D classifiers.
    """

    def __init__(self, hparams=None):
        ClassifierBase.__init__(self, hparams)

        with tf.variable_scope(self.variable_scope):
            self._encoder = Conv1DEncoder(hparams=hparams)
            # Add an additional dense layer if needed
            nclass = self._hparams.num_classes
            if nclass > 0:
                if self._hparams.num_dense_layers <= 0:
                    self._encoder.nn._append_layer({"type": "Flatten"})

                logit_kwargs = {}
                if self._hparams.logit_layer_kwargs is not None:
                    if not isinstance(self._hparams.logit_layer_kwargs, dict):
                        raise ValueError(
                            "hparams['logit_layer_kwargs'] must be a dict.")
                    logit_kwargs = self._hparams.logit_layer_kwargs
                logit_kwargs.update({"units": nclass})
                if 'name' not in logit_kwargs:
                    logit_kwargs['name'] = "logit_layer"
                self._encoder.nn._append_layer(
                    {"type": "Dense", "kwargs": logit_kwargs})

    @staticmethod
    def default_hparams():
        """Returns a dictionary of hyperparameters with default values.
        """
        hparams = Conv1DEncoder.default_hparams()
        hparams.update(
            {"num_classes": 2, "logit_layer_kwargs": None})
        return hparams

    def _build(self, inputs, mode=None): # pylint: disable=arguments-differ
        logits = self._encoder(inputs, mode)
        pred = tf.argmax(logits, 1, name="pred")
        self._built = True
        return logits, pred

    @property
    def trainable_variables(self):
        """The list of trainable variables of the module.
        """
        if not self._built:
            raise TexarError(
                "Attempting to access trainable_variables before module %s "
                "was fully built. The module is built once it is called, "
                "e.g., with `%s(...)`" % (self.name, self.name))
        return self._encoder.trainable_variables

    @property
    def nn(self): # pylint: disable=invalid-name
        """The neural network.
        """
        return self._encoder.nn

    def has_layer(self, layer_name):
        """Returns `True` if the network with the name exists. Returns `False`
        otherwise.

        Args:
            layer_name (str): Name of the layer.
        """
        return self._encoder.has_layer(layer_name)

    def layer_by_name(self, layer_name):
        """Returns the layer with the name. Returns 'None' if the layer name
        does not exist.

        Args:
            layer_name (str): Name of the layer.
        """
        return self._encoder.layer_by_name(layer_name)

    @property
    def layers_by_name(self):
        """A dictionary mapping layer names to the layers.
        """
        return self._encoder.layers_by_name

    @property
    def layers(self):
        """A list of the layers.
        """
        return self._encoder.layers

    @property
    def layer_names(self):
        """A list of uniquified layer names.
        """
        return self._encoder.layer_names

    def layer_outputs_by_name(self, layer_name):
        """Returns the output tensors of the layer with the specified name.
        Returns `None` if the layer name does not exist.

        Args:
            layer_name (str): Name of the layer.
        """
        return self._encoder.layer_outputs_by_name(layer_name)

    @property
    def layer_outputs(self):
        """A list containing output tensors of each layer.
        """
        return self._encoder.layer_outputs
