'''
Tensorflow implementation of
Interaction-aware Factorization Machines for Recommender Systems (IFM)
https://arxiv.org/abs/1902.09757

@author: 
cstur4@zju.edu.cn

@references:
https://github.com/hexiangnan/attentional_factorization_machine

'''
import math
import os, sys
import numpy as np
import tensorflow as tf
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.metrics import mean_squared_error
from sklearn.metrics import accuracy_score
from sklearn.metrics import roc_auc_score
from time import time
import argparse
import model.LoadData as DATA
from tensorflow.contrib.layers.python.layers import batch_norm as batch_norm

#################### Arguments ####################
def parse_args():
    parser = argparse.ArgumentParser(description="Run IFM.")
    parser.add_argument('--process', nargs='?', default='train',
                        help='Process type: train, evaluate.')
    parser.add_argument('--mla', type=int, default=0,
                        help='Set the experiment mode to be Micro Level Analysis or not: 0-disable, 1-enable.')
    parser.add_argument('--path', nargs='?', default='../data/',
                        help='Input data path.')
    parser.add_argument('--dataset', nargs='?', default='frappe',
                        help='Choose a dataset.')
    parser.add_argument('--valid_dimen', type=int, default=10,
                        help='Valid dimension of the dataset. (e.g. frappe=10, ml-tag=3)')
    parser.add_argument('--epoch', type=int, default=20,
                        help='Number of epochs.')
    parser.add_argument('--pretrain', type=int, default=-1,
                        help='flag for pretrain. 1: initialize from pretrain; 0: randomly initialize; -1: save to pretrain file; 2: initialize from pretrain and save to pretrain file')
    parser.add_argument('--batch_size', type=int, default=4096,
                        help='Batch size.')
    parser.add_argument('--attention', type=int, default=1,
                        help='flag for attention. 1: use attention; 0: no attention')
    parser.add_argument('--hidden_factor', nargs='?', default='[8,256]',
                        help='Number of hidden factors.')
    parser.add_argument('--lamda_attention', type=float, default=0.0,
                        help='Regularizer for attention part.')
    parser.add_argument('--lamda_attention1', type=float, default=0.0,
                        help='Regularizer for attention part.')
  
    parser.add_argument('--kf', type=int, default=16,
                        help='k_f.')
    parser.add_argument('--temp', type=float, default=1.0,
                        help='temperature for attention part.')
    parser.add_argument('--keep', nargs='?', default='[1.0,0.5]',
                        help='Keep probility (1-dropout) of each layer. 1: no dropout. The first index is for the attention-aware pairwise interaction layer.')
    parser.add_argument('--lr', type=float, default=0.1,
                        help='Learning rate.')
    parser.add_argument('--freeze_fm', type=int, default=0,
                        help='Freese all params of fm and learn attention params only.')
    parser.add_argument('--optimizer', nargs='?', default='AdagradOptimizer',
                        help='Specify an optimizer type (AdamOptimizer, AdagradOptimizer, GradientDescentOptimizer, MomentumOptimizer).')
    parser.add_argument('--verbose', type=int, default=1,
                        help='Whether to show the performance of each epoch (0 or 1)')
    parser.add_argument('--batch_norm', type=int, default=0,
                    help='Whether to perform batch normalization (0 or 1)')
    parser.add_argument('--decay', type=float, default=0.999,
                    help='Decay value for batch norm')
    parser.add_argument('--activation', nargs='?', default='relu',
                    help='Which activation function to use for deep layers: relu, sigmoid, tanh, identity')

    return parser.parse_args()

class AFM(BaseEstimator, TransformerMixin):
    def __init__(self, features_M, pretrain_flag, save_file, attention, hidden_factor, valid_dimension, activation_function, num_variable, 
                 freeze_fm, epoch, batch_size, learning_rate, lamda_attention, lamda_attention1, kf, temp, keep, optimizer_type, batch_norm, decay, verbose, micro_level_analysis, random_seed=2016):
        # bind params to class
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.attention = attention
        self.hidden_factor = hidden_factor
        self.valid_dimension = valid_dimension
        self.activation_function = activation_function
        self.num_variable = num_variable
        self.save_file = save_file
        self.pretrain_flag = pretrain_flag
        self.features_M = features_M
        self.lamda_attention = lamda_attention
        self.lamda_attention1 = lamda_attention1
        self.kf = kf
        self.temp = temp
        self.keep = keep
        self.freeze_fm = freeze_fm
        self.epoch = epoch
        self.random_seed = random_seed
        self.optimizer_type = optimizer_type
        self.batch_norm = batch_norm
        self.decay = decay
        self.verbose = verbose
        self.micro_level_analysis = micro_level_analysis
        # performance of each epoch
        self.train_rmse, self.valid_rmse, self.test_rmse = [], [], []

        # init all variables in a tensorflow graph
        self._init_graph()

    def _init_graph(self):
        '''
        Init a tensorflow Graph containing: input data, variables, model, loss, optimizer
        '''
        self.graph = tf.Graph()
        with self.graph.as_default():  # , tf.device('/cpu:0'):
            # Set graph level random seed
            tf.set_random_seed(self.random_seed)
            # Input data.
            self.train_features = tf.placeholder(tf.int32, shape=[None, None], name="train_features_afm")  # None * features_M
            self.train_labels = tf.placeholder(tf.float32, shape=[None, 1], name="train_labels_afm")  # None * 1
            self.dropout_keep = tf.placeholder(tf.float32, shape=[None], name="dropout_keep_afm")
            self.train_phase = tf.placeholder(tf.bool, name="train_phase_afm")

            # Variables.
            self.weights = self._initialize_weights()

            # Model.
            self.nonzero_embeddings = tf.nn.embedding_lookup(self.weights['feature_embeddings'], self.train_features) # None * M' * K
            
            element_wise_product_list = []
            interactions = []
            count = 0
            for i in range(0, self.valid_dimension):
                for j in range(i+1, self.valid_dimension):
                    element_wise_product_list.append(tf.multiply(self.nonzero_embeddings[:,i,:], self.nonzero_embeddings[:,j,:]))
                    interactions.append(tf.multiply(self.weights['interaction'][i,:], self.weights['interaction'][j,:]))
                    count += 1
            self.element_wise_product = tf.stack(element_wise_product_list) # (M'*(M'-1)) * None * K
            self.element_wise_product = tf.transpose(self.element_wise_product, perm=[1,0,2], name="element_wise_product") # None * (M'*(M'-1)) * K
            self.interactions = tf.reduce_sum(self.element_wise_product, 2, name="interactions")
            # _________ MLP Layer / attention part _____________
            num_interactions = self.valid_dimension*(self.valid_dimension-1)// 2
            self.num_interactions = num_interactions
            if self.attention:
                self.attention_mul = tf.reshape(tf.matmul(tf.reshape(self.element_wise_product, shape=[-1, self.hidden_factor[1]]), \
                    self.weights['attention_W']), shape=[-1, num_interactions, self.hidden_factor[0]])
                self.attention_mul = self.attention_mul / self.temp
                self.attention_exp = tf.exp(tf.reduce_sum(tf.multiply(self.weights['attention_p'], tf.nn.relu(self.attention_mul + \
                    self.weights['attention_b'])), 2, keep_dims=True)) # None * (M'*(M'-1)) * 1
                self.attention_sum = tf.reduce_sum(self.attention_exp, 1, keep_dims=True) # None * 1 * 1
                self.attention_out = tf.div(self.attention_exp, self.attention_sum, name="attention_out") # None * (M'*(M'-1)) * 1
                self.attention_out = tf.nn.dropout(self.attention_out, self.dropout_keep[0]) # dropout
            
            # _________ Attention-aware Pairwise Interaction Layer _____________
     
            self.AFM = self.attention_out * self.element_wise_product
            self.AFM = tf.reshape(self.AFM, [-1, num_interactions * self.hidden_factor[1]])
            self.AFM = tf.nn.dropout(self.AFM, self.dropout_keep[1]) # dropout
            
            self.field_interactions = tf.stack(interactions)  
            self.attention_interaction = tf.matmul(self.field_interactions, self.weights['factor'])
            self.attention_interaction = tf.reshape(self.attention_interaction, [num_interactions * self.hidden_factor[1], 1])
            self.AFM = tf.tensordot(self.AFM, self.attention_interaction, axes=1)
            self.AFM = tf.reduce_sum(self.AFM, reduction_indices=[1])
             
            self.prediction = self.AFM
            Bilinear = tf.expand_dims(self.prediction, -1)
            self.Feature_bias = tf.reduce_sum(tf.nn.embedding_lookup(self.weights['feature_bias'], self.train_features) , 1)  # None * 1
            Bias = self.weights['bias'] * tf.ones_like(self.train_labels)  # None * 1
            self.out = tf.add_n([Bilinear, self.Feature_bias, Bias], name="out_afm")  # None * 1

            # Compute the loss.
            if self.lamda_attention > 0:
                self.loss = tf.nn.l2_loss(tf.subtract(self.train_labels, self.out)) + tf.contrib.layers.l2_regularizer(self.lamda_attention)(self.weights['attention_W'])  # regulizer
            else:
                self.loss = tf.nn.l2_loss(tf.subtract(self.train_labels, self.out))
                
            if self.lamda_attention1 > 0:
                self.loss += tf.contrib.layers.l2_regularizer(self.lamda_attention1)(self.weights['interaction']) \
                            + tf.contrib.layers.l2_regularizer(self.lamda_attention1)(self.weights['factor'])

            # Optimizer.
            if self.optimizer_type == 'AdamOptimizer':
                self.optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate, beta1=0.9, beta2=0.999, epsilon=1e-8).minimize(self.loss)
            elif self.optimizer_type == 'AdagradOptimizer':
                self.optimizer = tf.train.AdagradOptimizer(learning_rate=self.learning_rate, initial_accumulator_value=1e-8).minimize(self.loss)
            elif self.optimizer_type == 'GradientDescentOptimizer':
                self.optimizer = tf.train.GradientDescentOptimizer(learning_rate=self.learning_rate).minimize(self.loss)
            elif self.optimizer_type == 'MomentumOptimizer':
                self.optimizer = tf.train.MomentumOptimizer(learning_rate=self.learning_rate, momentum=0.95).minimize(self.loss)

            # init
            self.saver = tf.train.Saver()
            init = tf.global_variables_initializer()
            self.sess = self._init_session()
            self.sess.run(init)

            # number of params
            total_parameters = 0
            for variable in list(self.weights.values()):
                shape = variable.get_shape() # shape is an array of tf.Dimension
                variable_parameters = 1
                for dim in shape:
                    variable_parameters *= dim.value
                total_parameters += variable_parameters
            if self.verbose > 0:
                print("#params: %d" % total_parameters)
    
    def _init_session(self):
        # adaptively growing video memory
        # config = tf.ConfigProto()
        # config.gpu_options.allow_growth = True
        # return tf.Session()
        return tf.Session()

    def _initialize_weights(self):
        all_weights = dict()
        # if freeze_fm, set all other params untrainable
        trainable = self.freeze_fm == 0
        if self.pretrain_flag > 0:
            from_file = self.save_file
            # if self.micro_level_analysis:
            from_file = self.save_file
            print("load from {}".format(from_file))
            weight_saver = tf.train.import_meta_graph(from_file + '.meta')
            pretrain_graph = tf.get_default_graph()
            feature_embeddings = pretrain_graph.get_tensor_by_name('feature_embeddings:0')
            feature_bias = pretrain_graph.get_tensor_by_name('feature_bias:0')
            bias = pretrain_graph.get_tensor_by_name('bias:0')
            with self._init_session() as sess:
                weight_saver.restore(sess, from_file)
                fe, fb, b = sess.run([feature_embeddings, feature_bias, bias])
            # all_weights['feature_embeddings'] = tf.Variable(fe, dtype=tf.float32, name='feature_embeddings')
            all_weights['feature_embeddings'] = tf.Variable(fe, dtype=tf.float32, name='feature_embeddings', trainable=trainable)
            all_weights['feature_bias'] = tf.Variable(fb, dtype=tf.float32, name='feature_bias', trainable=trainable)
            all_weights['bias'] = tf.Variable(b, dtype=tf.float32, name='bias', trainable=trainable)
        else:
            all_weights['feature_embeddings'] = tf.Variable(
                tf.random_normal([self.features_M, self.hidden_factor[1]], 0.0, 0.01),
                name='feature_embeddings', trainable=trainable)  # features_M * K
            all_weights['feature_bias'] = tf.Variable(
                tf.random_uniform([self.features_M, 1], 0.0, 0.0), name='feature_bias', trainable=trainable)  # features_M * 1
            all_weights['bias'] = tf.Variable(tf.constant(0.0), name='bias', trainable=trainable)  # 1 * 1

        # attention
        interaction_factor_hidden = self.kf
        if self.attention:
            glorot = np.sqrt(2.0 / (self.hidden_factor[0]+self.hidden_factor[1]))
            all_weights['attention_W'] = tf.Variable(
                np.random.normal(loc=0, scale=glorot, size=(self.hidden_factor[1], self.hidden_factor[0])), dtype=np.float32, name="attention_W")  # K * AK
            all_weights['attention_b'] = tf.Variable(
                np.random.normal(loc=0, scale=glorot, size=(1, self.hidden_factor[0])), dtype=np.float32, name="attention_b")  # 1 * AK
            all_weights['attention_p'] = tf.Variable(
                np.random.normal(loc=0, scale=1, size=(self.hidden_factor[0])), dtype=np.float32, name="attention_p") # AK
            num_interaction = self.valid_dimension * (self.valid_dimension - 1) // 2
            all_weights['interaction'] = tf.Variable(
                np.random.normal(loc=0, scale=1, size=(self.valid_dimension, interaction_factor_hidden)), dtype=np.float32, name="interaction") # AK
            all_weights['factor'] = tf.Variable(
                np.random.normal(loc=0, scale=1, size=(interaction_factor_hidden, self.hidden_factor[1])), dtype=np.float32, name="factor") # AK

        return all_weights

    def batch_norm_layer(self, x, train_phase, scope_bn):
        bn_train = batch_norm(x, decay=self.decay, center=True, scale=True, updates_collections=None,
            is_training=True, reuse=None, trainable=True, scope=scope_bn)
        bn_inference = batch_norm(x, decay=self.decay, center=True, scale=True, updates_collections=None,
            is_training=False, reuse=True, trainable=True, scope=scope_bn)
        z = tf.cond(train_phase, lambda: bn_train, lambda: bn_inference)
        return z

    def partial_fit(self, data):  # fit a batch
        feed_dict = {self.train_features: data['X'], self.train_labels: data['Y'], self.dropout_keep: self.keep, self.train_phase: True}
        loss, opt = self.sess.run((self.loss, self.optimizer), feed_dict=feed_dict)
        return loss

    def get_random_block_from_data(self, data, batch_size):  # generate a random block of training data
        start_index = np.random.randint(0, len(data['Y']) - batch_size)
        X , Y = [], []
        # forward get sample
        i = start_index
        while len(X) < batch_size and i < len(data['X']):
            if len(data['X'][i]) == len(data['X'][start_index]):
                Y.append([data['Y'][i]])
                X.append(data['X'][i])
                i = i + 1
            else:
                break
        # backward get sample
        i = start_index
        while len(X) < batch_size and i >= 0:
            if len(data['X'][i]) == len(data['X'][start_index]):
                Y.append([data['Y'][i]])
                X.append(data['X'][i])
                i = i - 1
            else:
                break
        return {'X': X, 'Y': Y}
    
    def get_ordered_block_from_data(self, data, batch_size, index):  # generate a ordered block of data
        start_index = index*batch_size
        X , Y = [], []
        # get sample
        i = start_index
        while len(X) < batch_size and i < len(data['X']):
            if len(data['X'][i]) == len(data['X'][start_index]):
                Y.append(data['Y'][i])
                X.append(data['X'][i])
                i = i + 1
            else:
                break
        return {'X': X, 'Y': Y}

    def shuffle_in_unison_scary(self, a, b): # shuffle two lists simutaneously
        rng_state = np.random.get_state()
        np.random.shuffle(a)
        np.random.set_state(rng_state)
        np.random.shuffle(b)

    def train(self, Train_data, Validation_data, Test_data):  # fit a dataset
        # Check Init performance
        if self.verbose > 0:
            t2 = time()
            init_train = self.evaluate(Train_data)
            init_valid = self.evaluate(Validation_data)
            init_test  = self.evaluate(Test_data)
            print(("Init: \t train=%.4f, validation=%.4f, test=%.4f [%.1f s]" %(init_train, init_valid, init_test, time()-t2)))


        for epoch in range(self.epoch):
            t1 = time()
            self.shuffle_in_unison_scary(Train_data['X'], Train_data['Y'])
            total_batch = int(len(Train_data['Y']) / self.batch_size)
            for i in range(total_batch):
                # generate a batch
                batch_xs = self.get_random_block_from_data(Train_data, self.batch_size)
                # Fit training
                self.partial_fit(batch_xs)
            t2 = time()

            # evaluate training and validation datasets
            train_result = self.evaluate(Train_data)
            valid_result = self.evaluate(Validation_data)
            test_result  = self.evaluate(Test_data)

            self.train_rmse.append(train_result)
            self.valid_rmse.append(valid_result)
            self.test_rmse.append(test_result)
            if self.verbose > 0 and epoch%self.verbose == 0:
                print(("Epoch %d [%.1f s]\ttrain=%.4f, validation=%.4f, Test=%.4f [%.1f s]"
                      %(epoch+1, t2-t1, train_result, valid_result, test_result, time()-t2)))

            # test_result = self.evaluate(Test_data)
            # print("Epoch %d [%.1f s]\ttest=%.4f [%.1f s]"
            #       %(epoch+1, t2-t1, test_result, time()-t2))
            if self.eva_termination(self.valid_rmse):
                break

        if self.pretrain_flag < 0 or self.pretrain_flag == 2:
            print("Save model to file as pretrain.")
            self.saver.save(self.sess, self.save_file)

    def eva_termination(self, valid):
        if len(valid) > 5:
            if valid[-1] > valid[-2] and valid[-2] > valid[-3] and valid[-3] > valid[-4] and valid[-4] > valid[-5]:
                return True
        return False

    def evaluate(self, data):  # evaluate the results for an input set
        num_example = len(data['Y'])
        # fetch the first batch
        batch_index = 0
        batch_xs = self.get_ordered_block_from_data(data, self.batch_size, batch_index)
        # batch_xs = data
        y_pred = None
        # if len(batch_xs['X']) > 0:
        while len(batch_xs['X']) > 0:
            num_batch = len(batch_xs['Y'])
            feed_dict = {self.train_features: batch_xs['X'], self.train_labels: [[y] for y in batch_xs['Y']], self.dropout_keep: list(1.0 for i in range(len(self.keep))), self.train_phase: False}
            a_exp, a_sum, a_out, batch_out = self.sess.run((self.attention_exp, self.attention_sum, self.attention_out, self.out), feed_dict=feed_dict)
            
            if batch_index == 0:
                y_pred = np.reshape(batch_out, (num_batch,))
            else:
                y_pred = np.concatenate((y_pred, np.reshape(batch_out, (num_batch,))))
            # fetch the next batch
            batch_index += 1
            batch_xs = self.get_ordered_block_from_data(data, self.batch_size, batch_index)
        
#         field_out, batch_out = self.sess.run((self.attention_interaction, self.out), feed_dict=feed_dict)
#         analysis = np.reshape(field_out, [self.num_interactions, self.hidden_factor[1]])
#         analysis = np.square(analysis)
#         analysis = np.sum(analysis, axis=1)
#         print(analysis)
        y_true = np.reshape(data['Y'], (num_example,))

        predictions_bounded = np.maximum(y_pred, np.ones(num_example) * min(y_true))  # bound the lower values
        predictions_bounded = np.minimum(predictions_bounded, np.ones(num_example) * max(y_true))  # bound the higher values
#         accuracy = accuracy_score(y_true, predictions_bounded > 0.5)
#         return accuracy
#         AUC = roc_auc_score(y_true, predictions_bounded)
#         return AUC
        RMSE = math.sqrt(mean_squared_error(y_true, predictions_bounded))
        return RMSE

def make_save_file(args):
    pretrain_path = '../pretrain/fm_%s_%d' %(args.dataset, eval(args.hidden_factor)[1])
    # pretrain_path = '../pretrain/fm_frappe_256'

    if args.mla:
        pretrain_path += '_mla'
    if not os.path.exists(pretrain_path):
        os.makedirs(pretrain_path)
    save_file = pretrain_path+'/%s_%d' %(args.dataset, eval(args.hidden_factor)[1])
    # save_file = pretrain_path+ '/frappe_256'
    print(save_file)
    return save_file

def train(args):
    # Data loading
    data = DATA.LoadData(args.path, args.dataset)
    if args.verbose > 0:
        print(("IFM: dataset=%s, factors=%s, attention=%d, freeze_fm=%d, #epoch=%d, batch=%d, lr=%.4f, lambda_attention=%.1e, lambda_attention1=%.1e, kf=%d, temp=%.1e, keep=%s, optimizer=%s, batch_norm=%d, decay=%f, activation=%s"
              %(args.dataset, args.hidden_factor, args.attention, args.freeze_fm, args.epoch, args.batch_size, args.lr, args.lamda_attention, args.lamda_attention1, args.kf, args.temp, args.keep, args.optimizer, 
              args.batch_norm, args.decay, args.activation)))
    activation_function = tf.nn.relu
    if args.activation == 'sigmoid':
        activation_function = tf.sigmoid
    elif args.activation == 'tanh':
        activation_function == tf.tanh
    elif args.activation == 'identity':
        activation_function = tf.identity
    
    save_file = make_save_file(args)
    # Training
    t1 = time()

    num_variable = data.truncate_features()
    if args.mla:
        args.freeze_fm = 1
    model = AFM(data.features_M, args.pretrain, save_file, args.attention, eval(args.hidden_factor), args.valid_dimen, 
        activation_function, num_variable, args.freeze_fm, args.epoch, args.batch_size, args.lr, args.lamda_attention, args.lamda_attention1, args.kf, args.temp, eval(args.keep), args.optimizer, 
        args.batch_norm, args.decay, args.verbose, args.mla)
    
    model.train(data.Train_data, data.Validation_data, data.Test_data)
    
    # Find the best validation result across iterations
    best_valid_score = 0
    best_valid_score = min(model.valid_rmse)
    best_epoch = model.valid_rmse.index(best_valid_score)
    print(("Best Iter(validation)= %d\t train = %.4f, valid = %.4f Test = %.4f [%.1f s]" 
           %(best_epoch+1, model.train_rmse[best_epoch], model.valid_rmse[best_epoch], model.test_rmse[best_epoch], time()-t1)))

def evaluate(args):
    # load test data
    data_instance = [1, 1, 'morning', 'monday', 'workday', 'home', 'sunny', 'Spain', 0]
    data = DATA.LoadData(args.path, args.dataset).convertData(data_instance)
    save_file = make_save_file(args)
    print("savefile: " ,save_file)
    # load the graph
    weight_saver = tf.train.import_meta_graph(save_file + '.meta')
    pretrain_graph = tf.get_default_graph()
    # load tensors 
    # feature_embeddings = pretrain_graph.get_tensor_by_name('feature_embeddings:0')
    # feature_bias = pretrain_graph.get_tensor_by_name('feature_bias:0')
    # bias = pretrain_graph.get_tensor_by_name('bias:0')
    # afm = pretrain_graph.get_tensor_by_name('afm:0')
    out_of_afm = pretrain_graph.get_tensor_by_name('out_afm:0')
    interactions = pretrain_graph.get_tensor_by_name('interactions:0')
    attention_out = pretrain_graph.get_tensor_by_name('attention_out:0')
    # placeholders for afm
    train_features_afm = pretrain_graph.get_tensor_by_name('train_features_afm:0')
    train_labels_afm = pretrain_graph.get_tensor_by_name('train_labels_afm:0')
    dropout_keep_afm = pretrain_graph.get_tensor_by_name('dropout_keep_afm:0')
    train_phase_afm = pretrain_graph.get_tensor_by_name('train_phase_afm:0')

    # tensors and placeholders for fm
    if args.mla:
         out_of_fm = pretrain_graph.get_tensor_by_name('out_fm:0')
         element_wise_product = pretrain_graph.get_tensor_by_name('element_wise_product:0')
         train_features_fm = pretrain_graph.get_tensor_by_name('train_features_fm:0')
         train_labels_fm = pretrain_graph.get_tensor_by_name('train_labels_fm:0')
         dropout_keep_fm = pretrain_graph.get_tensor_by_name('dropout_keep_fm:0')
         train_phase_fm = pretrain_graph.get_tensor_by_name('train_phase_fm:0')

    # restore session
    #config = tf.ConfigProto()
    #config.gpu_options.allow_growth = True
    #sess = tf.Session(config=config)
    sess = tf.Session()
    weight_saver.restore(sess, save_file)

    # start evaluation
    num_example = len(data['Y'])
    if args.mla:
        feed_dict = {train_features_afm: data['X'], train_labels_afm: [[y] for y in data['Y']], dropout_keep_afm: [1.0,1.0], train_phase_afm: False, \
                     train_features_fm: data['X'], train_labels_fm: [[y] for y in data['Y']], dropout_keep_fm: 1.0, train_phase_fm: False}
        ao, inter, out_fm, predictions = sess.run((attention_out, interactions, out_of_fm, out_of_afm), feed_dict=feed_dict)
    else:
        feed_dict = {train_features_afm: data['X'], train_labels_afm: [[y] for y in data['Y']], dropout_keep_afm: [1.0,1.0], train_phase_afm: False}
        predictions = sess.run((out_of_afm), feed_dict=feed_dict)

    # calculate rmse
    y_pred_afm = np.reshape(predictions, (num_example,))
    y_true = np.reshape(data['Y'], (num_example,))
    
    predictions_bounded = np.maximum(y_pred_afm, np.ones(num_example) * min(y_true))  # bound the lower values
    predictions_bounded = np.minimum(predictions_bounded, np.ones(num_example) * max(y_true))  # bound the higher values
    RMSE = math.sqrt(mean_squared_error(y_true, predictions_bounded))

    print(("Test RMSE: %.4f"%(RMSE)))

    if args.mla:
        # select significant cases
        ao = np.reshape(ao, (num_example, 3))
        y_pred_fm = np.reshape(out_fm, (num_example,))
        pred_abs_fm = abs(y_pred_fm - y_true)
        pred_abs_afm = abs(y_pred_afm - y_true)
        pred_abs = pred_abs_afm - pred_abs_fm

        ids = np.arange(0, num_example, 1)

        # sorted_ids = sorted(ids, key=lambda k: pred_abs_afm[k]+abs(ao[k][0]*ao[k][1]*ao[k][2]))
        # sorted_ids = sorted(ids, key=lambda k: abs(ao[k][0]*ao[k][1]*ao[k][2]))
#         for i in range(3):
#             _id = sorted_ids[i]
#             print(('## %d: %d'%(i+1, y_true[_id])))
#             print(('0.33*%.2f + 0.33*%.2f + 0.33*%.2f = %.2f'%(inter[_id][0], inter[_id][1], inter[_id][2], y_pred_fm[_id])))
#             print(('%.2f*%.2f + %.2f*%.2f + %.2f*%.2f = %.2f\n'%(\
#                           ao[_id][0], inter[_id][0], \
#                           ao[_id][1], inter[_id][1], \
#                           ao[_id][2], inter[_id][2], y_pred_afm[_id])))


def infer(path, dataset, pretrain_path, data_instance, k):
    # save_file = make_save_file(args)
    # data_instance = [2, 1, 'morning', 'monday', 'workday', 'home', 'sunny', 'Spain', 0]
    data = DATA.LoadData(path, dataset).convertData(data_instance)


    # save_file = make_save_file(args)
    # print("savefile: " ,save_file)
    # load the graph
    weight_saver = tf.train.import_meta_graph(pretrain_path + '.meta')
    pretrain_graph = tf.get_default_graph()
    sess = tf.Session()
    weight_saver.restore(sess, pretrain_path)
    
    out_of_afm = pretrain_graph.get_tensor_by_name('out_afm:0')
    # interactions = pretrain_graph.get_tensor_by_name('interactions:0')
    # attention_out = pretrain_graph.get_tensor_by_name('attention_out:0')
    # placeholders for afm
    train_features_afm = pretrain_graph.get_tensor_by_name('train_features_afm:0')
    train_labels_afm = pretrain_graph.get_tensor_by_name('train_labels_afm:0')
    dropout_keep_afm = pretrain_graph.get_tensor_by_name('dropout_keep_afm:0')
    train_phase_afm = pretrain_graph.get_tensor_by_name('train_phase_afm:0')

    # num_example = len(data['Y'])

    feed_dict = {train_features_afm: data['X'], train_labels_afm: [[y] for y in data['Y']], dropout_keep_afm: [1.0,1.0], train_phase_afm: False}
    predictions = sess.run((out_of_afm), feed_dict=feed_dict)

    # print(predictions)
    
    predictions = predictions.flatten()

    # Compute the absolute difference from 1
    abs_diff_from_1 = np.abs(1 - predictions)

    # Get the indices of the top 10 smallest differences
    top_k_indices = np.argsort(abs_diff_from_1)[:k]

    # print("Top 10 indices closest to 1:", top_10_indices)
    # Get the top 10 predictions
    # top_10_predictions = predictions[top_10_indices]

    # print("Top 10 predictions closest to 1:", top_10_predictions)

    # closest_to_1 = [(x[1], pred) for x, pred in zip(data['X'][:10], top_10_predictions) if pred >= 0.9]
    # print(closest_to_1)
    # return predictions

    return top_k_indices

if __name__ == '__main__':
    #os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    args = parse_args()
    # if args.mla:
    #     args.lr = 0.1
    #     args.keep = '[1.0,1.0]'
    #     args.lamda_attention = 10.0
    # else:
    #     args.lr = 0.1
    #     args.keep = '[1.0,0.5]'
    #     args.lamda_attention = 100.0
    start = time()
    if args.process == 'train':
        train(args)
    elif args.process == 'evaluate':
        evaluate(args)
    elif args.process == 'infer':
        infer(args)
        
    print("%f used." % (time() - start))
