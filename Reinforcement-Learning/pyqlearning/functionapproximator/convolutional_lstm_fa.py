# -*- coding: utf-8 -*-
import numpy as np
from logging import getLogger, StreamHandler, NullHandler, DEBUG, ERROR

from pyqlearning.function_approximator import FunctionApproximator

from pydbm.cnn.convolutional_neural_network import ConvolutionalNeuralNetwork
from pydbm.cnn.layerablecnn.convolution_layer import ConvolutionLayer
from pydbm.cnn.layerable_cnn import LayerableCNN
from pydbm.cnn.feature_generator import FeatureGenerator
from pydbm.optimization.opt_params import OptParams
from pydbm.verification.interface.verificatable_result import VerificatableResult
from pydbm.loss.interface.computable_loss import ComputableLoss

from pydbm.rnn.lstmmodel.conv_lstm_model import ConvLSTMModel

# Loss function.
from pydbm.loss.mean_squared_error import MeanSquaredError
# Adam as a optimizer.
from pydbm.optimization.optparams.adam import Adam
# Verification.
from pydbm.verification.verificate_function_approximation import VerificateFunctionApproximation


class ConvolutionalLSTMFA(FunctionApproximator):
    '''
    Convolutional LSTM Networks as a Function Approximator,
    which is a model that structurally couples convolution operators to LSTM networks, 
    can be utilized as components in constructing the Function Approximator.
    
    References:
        - Sainath, T. N., Vinyals, O., Senior, A., & Sak, H. (2015, April). Convolutional, long short-term memory, fully connected deep neural networks. In Acoustics, Speech and Signal Processing (ICASSP), 2015 IEEE International Conference on (pp. 4580-4584). IEEE.
        - Xingjian, S. H. I., Chen, Z., Wang, H., Yeung, D. Y., Wong, W. K., & Woo, W. C. (2015). Convolutional LSTM network: A machine learning approach for precipitation nowcasting. In Advances in neural information processing systems (pp. 802-810).
    '''
    
    __next_action_arr_list = []
    
    def __init__(
        self,
        batch_size,
        conv_lstm_model,
        seq_len=10,
        learning_rate=1e-05,
        computable_loss=None,
        opt_params=None,
        verificatable_result=None,
        pre_learned_path_list=None,
        verbose_mode=False
    ):
        logger = getLogger("pydbm")
        handler = StreamHandler()
        if verbose_mode is True:
            handler.setLevel(DEBUG)
            logger.setLevel(DEBUG)
        else:
            handler.setLevel(ERROR)
            logger.setLevel(ERROR)

        logger.addHandler(handler)

        self.__logger = getLogger("pyqlearning")
        handler = StreamHandler()
        if verbose_mode is True:
            self.__logger.setLevel(DEBUG)
        else:
            self.__logger.setLevel(ERROR)
            
        self.__logger.addHandler(handler)

        if isinstance(conv_lstm_model, ConvLSTMModel) is False:
            raise TypeError()

        if computable_loss is None:
            computable_loss = MeanSquaredError()
        if verificatable_result is None:
            verificatable_result = VerificateFunctionApproximation()
        if opt_params is None:
            opt_params = Adam()
            opt_params.weight_limit = 0.5
            opt_params.dropout_rate = 0.0

        self.__conv_lstm_model = conv_lstm_model
        self.__seq_len = seq_len
        self.__batch_size = batch_size
        self.__computable_loss = computable_loss
        self.__learning_rate = learning_rate
        self.__verbose_mode = verbose_mode
        self.__q_logs_list = []

    def learn_q(self, q, new_q):
        '''
        Infernce Q-Value.
        
        Args:
            q:                  Predicted Q-Value.
            new_q:              Real Q-Value.
        '''
        q_arr = np.array([q] * self.__batch_size).reshape(-1, 1)
        new_q_arr = np.array([new_q] * self.__batch_size).reshape(-1, 1)
        cost_arr = self.__computable_loss.compute_loss(q_arr, new_q_arr)
        delta_arr = self.__computable_loss.compute_delta(q_arr, new_q_arr)
        delta_arr = delta_arr / self.__batch_size
        delta_arr, grads_list = self.__conv_lstm_model.back_propagation(q_arr, delta_arr)

        self.__conv_lstm_model.optimize(grads_list, self.__learning_rate, 1)
        self.__q_logs_list.append((q, new_q, cost_arr.mean()))

    def inference_q(self, next_action_arr):
        '''
        Infernce Q-Value.
        
        Args:
            next_action_arr:     `np.ndarray` of action.
        
        Returns:
            `np.ndarray` of Q-Values.
        '''
        self.__next_action_arr_list.append(next_action_arr)
        while len(self.__next_action_arr_list) > self.__seq_len:
            self.__next_action_arr_list = self.__next_action_arr_list[1:]
        while len(self.__next_action_arr_list) < self.__seq_len:
            self.__next_action_arr_list.append(self.__next_action_arr_list[-1])

        _next_action_arr = np.array(self.__next_action_arr_list)
        _next_action_arr = _next_action_arr.transpose((1, 0, 2, 3, 4))

        q_arr = self.__conv_lstm_model.inference(_next_action_arr)
        return q_arr[:, -1]

    def get_q_logs_list(self):
        ''' getter '''
        return self.__q_logs_list

    def set_q_logs_list(self, value):
        ''' setter '''
        self.__q_logs_list = value
    
    q_logs_list = property(get_q_logs_list, set_q_logs_list)
