import os
import random

import torch

from global_settings import device
import matplotlib.pyplot as plt

# Source: https://pytorch.org/tutorials/beginner/chatbot_tutorial.html
# If preprocessing is done with "expand_contractions" flag set to True,
# the prefixes right part, e.g. 'we re', should not appear in the corpus
eng_prefixes = (
    "i am ", "i m ",
    "he is", "he s ",
    "she is", "she s ",
    "you are", "you re ",
    "we are", "we re ",
    "they are", "they re "
)


def max_length(lines):
    """
    Computes max length given an array of sentences
    :param lines:
    :return:
    """
    lens = [[len(sent.split(" "))] for sent in lines]
    return max(lens)


def english_prefixes(sentence):
    """
    Filter checks if a sentence starts with some english prefixes
    :param sentence:
    :return:
    """
    return sentence.startswith(eng_prefixes)



def filter_pairs(pairs, len_tuple=None, filter_func=None):
    """
    Applies filters at pair level
    :param pairs: the parallel corpus
    :param len_tuple: provided as array containing the minimum and the maximum length to consider in pairs
    :param filter_func: provided as function, this will applied to the corpus
    :return: the filtered corpus
    """
    if len_tuple:
        min_length = len_tuple[0]
        max_length = len_tuple[1]
        pairs = [pair for pair in pairs if len(pair[0]) >= min_length and len(pair[0]) <= max_length]

    # This should be improved, thus this is shut down :-)
    filter_func = None
    if filter_func:
        pairs = [pair for pair in pairs if filter_func(pair[0]) or filter_func(pair[1])]

    return pairs


### train / testing utils

def maskNLLLoss(inp, target, mask):
    """
    Source: PyTorch Chatbot Tutorial: https://pytorch.org/tutorials/beginner/chatbot_tutorial.html
    :param inp: Input variable provided as tensor
    :param target: Target variable provided as tensor
    :param mask: THe masking matrix to handle with padded tensors
    :return: the NLLLoss for the given input (prediction) and the real value (target)
    """
    nTotal = mask.sum()
    crossEntropy = -torch.log(torch.gather(inp, 1, target.view(-1, 1)).squeeze(1))
    loss = crossEntropy.masked_select(mask).mean()
    loss = loss.to(device)
    return loss, nTotal.item()


def split_data(data, test_ratio=0.2, seed=40):
    """
    Splits data into training, validation and test set.
    Train set: 70%
    Val set: 20%
    Test set: 10%

    :param data: all the dataset
    :param test_ratio: actually the validation ratio
    :return: 3 splits
    """
    num_samples = len(data)
    test_range = int(num_samples*test_ratio) #test dataset 0.1
    train_range = num_samples-test_range
    random.seed(seed) #30
    random.shuffle(data)

    data_set = data[:train_range]
    val_set = data[train_range:]

    #create test set
    num_samples = len(data_set)
    test_range = int(num_samples * 0.1)
    train_range = num_samples - test_range

    train_set = data_set[:train_range]
    test_set = data_set[train_range:]

    print(len(test_set) + len(train_set) + len(val_set))

    return train_set, val_set, test_set


#### Not used ###########
def plot_grad_flow(save_dir, modelname, corpus_name, n_layers, emb_size, hid_size, bs, enc_statistics, dec_statistics):

    directory = os.path.join(save_dir, modelname, corpus_name,
                             '{}-{}_{}-{}_{}'.format(n_layers, n_layers, emb_size, hid_size, bs))
    store_grad = os.path.join(directory, "gradients")

    if not os.path.isdir(directory):
        os.makedirs(directory)

    encoder_avg_grads, encoder_layers = enc_statistics
    decoder_avg_grads , decoder_layers = dec_statistics

    ### Plotting both figuers side by side

    plt.subplot(1, 2, 1)
    plt.plot(encoder_avg_grads, alpha=0.3, color='b')
    plt.hlines(0, 0, len(encoder_avg_grads)+1, linewidth=1, color="k" )
    plt.xticks(range(0,len(encoder_avg_grads), 1), encoder_layers, rotation="vertical")
    plt.xlim(xmin=0, xmax=len(encoder_avg_grads))
    plt.xlabel("Layers")
    plt.ylabel("average gradient")
    plt.title("Encoder - Gradient flow")
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(decoder_avg_grads, alpha=0.3, color='r')
    plt.hlines(0, 0, len(decoder_layers) + 1, linewidth=1, color="k")
    plt.xticks(range(0, len(decoder_avg_grads), 1), decoder_layers, rotation="vertical")
    plt.xlim(xmin=0, xmax=len(decoder_avg_grads))
    plt.xlabel("Layers")
    plt.ylabel("average gradient")
    plt.title("Decoder - Gradient flow")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(store_grad+"gradient_flow.png")
    plt.close()

