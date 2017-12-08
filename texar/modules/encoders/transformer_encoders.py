"""
transformer encoders. Multihead-SelfAttention
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from texar.modules.encoders.encoder_base import EncoderBase
from texar.core import layers
from texar import context

class TransformerEncoder(EncoderBase):
    """Base class for all encoder classes.
    Args:
        embedding (optional): A `Variable` or a 2D `Tensor` (or `numpy array`)
            of shape `[vocab_size, embedding_dim]` that contains the token
            embeddings.
            If a `Variable`, it is directly used in encoding, and
            the hyperparameters in :attr:`hparams["embedding"]` is ignored.
            If a `Tensor` or `numpy array`, a new `Variable` is created taking
            :attr:`embedding` as initial value. The :attr:`"initializer"` and
            :attr:`"dim"` hyperparameters in :attr:`hparams["embedding"]` are
            ignored.
            If not given, a new `Variable` is created as specified in
            :attr:`hparams["embedding"]`.
        vocab_size (int, optional): The vocabulary size. Required if
            :attr:`embedding` is not provided.
        hparams (dict, optional): Encoder hyperparameters. If it is not
            specified, the default hyperparameter setting is used. See
            :attr:`default_hparams` for the sturcture and default values.
    """
    def __init__(self,
                 embedding=None,
                 vocab_size=None,
                 hparams=None):
        EncoderBase.__init__(self, hparams)
        self._embedding = None
        if self._hparams.embedding_enabled:
            if embedding is None and vocab_size is None:
                raise ValueError("If `embedding` is not provided, "
                                "`vocab_size` must be specified.")
            if isinstance(embedding, tf.Variable):
                self._embedding = embedding
            else:
                self._embedding = layers.get_embedding(
                    self._hparams.embedding, embedding, vocab_size,
                    self.variable_scope)

            embed_dim = self._embedding.shape.as_list()[1]
            if self._hparams.zero_pad:
                self._embedding = tf.concat((tf.zeros(shape=[1, embed_dim]),
                                            self._embedding[1:, :]), 0)
            if self._hparams.embedding.trainable:
                self._add_trainable_variable(self._embedding)

    @staticmethod
    def default_hparams():
        """Returns a dictionary of hyperparameters with default values.
        The dictionary has the following structure and default values.
        See :meth:`~texar.core.layers.default_rnn_cell_hparams` for the
        default rnn cell hyperparameters, and
        :meth:`~texar.core.layers.default_embedding_hparams` for the default
        embedding hyperparameters.
        .. code-block:: python
            {
                # (bool) Wether embedding is used in the encoder. If `True`
                # (default), input to the encoder should contain integer
                # indexes and will be used to look up the embedding vectors.
                # If `False`, the input is directly fed into the RNN to encode.
                "embedding_enabled": True,

                # A dictionary of token embedding hyperparameters for embedding
                # initialization.
                #
                # Ignored if "embedding_enabled" is `False`, or a tf.Variable
                # is given to `embedding` in the encoder constructor. Note that
                # in the second case, the embedding variable might be updated
                # outside the encoder even if "embedding.trainable" is set to
                # `False` and not updated by the encoder.
                #
                # If a Tensor or array is given to `embedding` in the
                # constructor, "dim" and "initializer" in the configuration
                # are ignored.
                "embedding": texar.core.layers.default_embedding_hparams(),
                # Name of the encoder.
                "name": "transformer_encoder"
            }
        """
        return {
            "embedding_enabled": True,
            "embedding":layers.default_embedding_hparams(),
            "name":"transformer_encoder",
            "zero_pad":True,
            "max_seq_length":10,
            'scale':True,
            'sinusoid':False,
            'dropout':0.1,
            'num_blocks':6,
            'num_heads':8,
        }

    def _build(self, inputs, **kwargs):
        if self._embedding is not None:
            enc = tf.nn.embedding_lookup(self._embedding, inputs)
        else:
            enc = inputs
        dim = enc.shape.as_list()[-1]
        if self._hparams.scale:
            enc = enc * (dim**0.5)

        with tf.variable_scope(self.variable_scope):
            if self._hparams.sinusoid:
                enc += layers.sinusoid_positional_encoding(inputs,
                        num_units=dim,
                        max_time=self._hparams.max_seq_length,
                        variable_scope='enc_pe',
                    )
            else:
                position_enc_embedding = layers.get_embedding(
                        hparams = self._hparams.embedding,
                        vocab_size=self._hparams.max_seq_length,
                        variable_scope='enc_pe',
                        )
                enc += tf.nn.embedding_lookup(position_enc_embedding,
                        tf.tile(tf.expand_dims(tf.range(tf.shape(inputs)[1]), 0), \
                                [inputs.shape[0], 1]))

            print('dropout rate:{}'.format(self._hparams.dropout))
            print('encoder num_heads:{}'.format(self._hparams.num_heads))
            enc = tf.layers.dropout(enc,
                    rate=self._hparams.dropout,
                    training=context.is_train())

            for i in range(self._hparams.num_blocks):
                with tf.variable_scope("num_blocks_{}".format(i)):
                    enc = layers.multihead_attention(queries=enc,
                        keys=enc,
                        num_heads=self._hparams.num_heads,
                        dropout_rate=self._hparams.dropout,
                        num_units=self._hparams.embedding.dim,
                        causality=False)
                    enc = layers.poswise_feedforward(enc,
                        num_units=[4*self._hparams.embedding.dim, self._hparams.embedding.dim])
        self._add_internal_trainable_variables()
        self._built=True
        return enc