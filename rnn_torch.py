# -*- coding:utf-8 -*-
__author__ = 'chenjun'

import torch
import torch.nn as nn
import cPickle as pickle
import numpy as np
import torch.optim as opt
from torch_models.qa_rnn import QARNNModel
from data_process.load_data import data_loader
from qa_score import qa_evaluate
from torch.autograd import Variable
import warnings
warnings.filterwarnings('ignore')


def train_rnn(n_epochs, batch_size, sequence_length, n_in_rnn, n_hidden_rnn, n_in_mlp, n_hidden_mlp, n_out,
                learning_rate, random=False, non_static=True):
    print "loading the data... "
    path = "/Users/chenjun/PycharmProjects/DBQA/"
    loader = data_loader(path + "pkl/data-train-nn.pkl", path + "pkl/data-valid-nn.pkl", path + "pkl/data-test-nn.pkl",
                         path + "/pkl/index2vec.pkl", )
    valid_group_list = pickle.load(open(path + "pkl/valid_group.pkl"))
    test_group_list = [int(x.strip()) for x in open(path + "data/dbqa-data-test.txt.group")]

    datasets, emb_words = loader.get_input_by_model(model="pytorch", random=random)
    train_q_data, valid_q_data, test_q_data = datasets[0]
    train_a_data, valid_a_data, test_a_data = datasets[1]
    train_l_data, valid_l_data, test_l_data = datasets[2]

    # calculate the number of batches.
    n_train_batches = train_q_data.size(0) // batch_size
    n_valid_batches = valid_q_data.size(0) // batch_size
    n_test_batches = test_q_data.size(0) // batch_size
    print "batch_size: %i, n_train_batches: %i, n_valid_batches: %i, n_test_batches: %i" % \
          (batch_size, n_train_batches, n_valid_batches, n_test_batches)

    ###############
    # BUILD MODEL #
    ###############
    print "building the model... "
    embedding = nn.Embedding(emb_words.size(0), emb_words.size(1))
    embedding.weight = nn.Parameter(emb_words, requires_grad=non_static)
    qa_rnn_model = QARNNModel(embedding, batch_size, sequence_length, n_in_rnn, n_hidden_rnn, n_in_mlp, n_hidden_mlp, n_out)
    parameters = filter(lambda p: p.requires_grad, qa_rnn_model.parameters())
    print qa_rnn_model
    ###############
    # TRAIN MODEL #
    ###############
    print "training the model... "
    criterion = nn.CrossEntropyLoss()
    optimzier = opt.RMSprop(parameters, learning_rate)
    epoch = 0
    while epoch < n_epochs:
        epoch += 1
        train_loss = 0.0
        for index1 in xrange(n_train_batches):
            train_q_batch = Variable(train_q_data[batch_size * index1: batch_size * (index1 + 1)])
            train_a_batch = Variable(train_a_data[batch_size * index1: batch_size * (index1 + 1)])
            train_l_batch = Variable(train_l_data[batch_size * index1: batch_size * (index1 + 1)])
            train_prop_batch, _ = qa_rnn_model(train_q_batch, train_a_batch, drop_rate=0.5)
            loss = criterion(train_prop_batch, train_l_batch)
            optimzier.zero_grad()
            loss.backward()
            optimzier.step()
            train_loss += loss.data[0] / batch_size
            if index1 % 100 == 0:
                print ("epoch: %d/%d, batch: %d/%d, cost: %f") % (epoch, n_epochs, index1, n_train_batches, train_loss)
                # valid
                valid_score_data = []
                for index in xrange(n_valid_batches):
                    vaild_q_batch = Variable(valid_q_data[batch_size * index: batch_size * (index + 1)])
                    valid_a_batch = Variable(valid_a_data[batch_size * index: batch_size * (index + 1)])
                    valid_prop_batch, _ = qa_rnn_model(vaild_q_batch, valid_a_batch, drop_rate=0.0)
                    valid_score_data.append(valid_prop_batch.data.numpy()[:, 1])
                valid_score_list = (np.concatenate(np.asarray(valid_score_data), axis=0)).tolist()
                valid_label_list = valid_l_data.numpy().tolist()
                for i in xrange(len(valid_score_list), len(valid_label_list)):
                    valid_score_list.append(np.random.random())
                _eval = qa_evaluate(valid_score_list, valid_label_list, valid_group_list, label=1, mod="mrr")
                print "---valid mrr: ", _eval
                # test
                test_score_data = []
                for index in xrange(n_test_batches):
                    test_q_batch = Variable(test_q_data[batch_size * index: batch_size * (index + 1)])
                    test_a_batch = Variable(test_a_data[batch_size * index: batch_size * (index + 1)])
                    test_prop_batch, _ = qa_rnn_model(test_q_batch, test_a_batch, drop_rate=0.0)
                    test_score_data.append(test_prop_batch.data.numpy()[:, 1])
                test_score_list = (np.concatenate(np.asarray(test_score_data), axis=0)).tolist()
                test_label_list = test_l_data.numpy().tolist()
                for i in xrange(len(test_score_list), len(test_label_list)):
                    test_score_list.append(np.random.random())
                _eval = qa_evaluate(test_score_list, test_label_list, test_group_list, label=1, mod="mrr")
                print "---test mrr: ", _eval


if __name__ == "__main__":
    train_rnn(n_epochs=5,
              batch_size=64,
              sequence_length=50,
              n_in_rnn=50,
              n_hidden_rnn=128,
              n_in_mlp=20,
              n_hidden_mlp=128,
              n_out=2,
              learning_rate=0.01,
              random=False,
              non_static=True
            )



