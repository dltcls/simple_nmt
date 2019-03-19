import os
import random
from pickle import load
from datetime import datetime
import torch
from torch import optim

from experiment.train_eval import evaluateInput, GreedySearchDecoder, trainIters, eval_test, plot_training_results
from global_settings import device, FILENAME, SAVE_DIR, PREPRO_DIR, TRAIN_FILE, TEST_FILE, EXPERIMENT_DIR, LOG_FILE
from model.model import EncoderLSTM, DecoderLSTM
from utils.prepro import read_lines, preprocess_pipeline, load_cleaned_data, save_clean_data
from utils.tokenize import build_vocab, batch2TrainData

from global_settings import DATA_DIR
from utils.utils import split_data, filter_pairs, max_length



if __name__ == '__main__':

    experiment_execution_time = datetime.now()

    start_root = "."
    src_lang = "eng"
    trg_lang = "deu"
    exp_contraction = True
    src_reversed = False
    limit = None
    trimming = False

    cleaned_file = "%s-%s_cleaned" % (src_lang, trg_lang) + "_rude" if not exp_contraction else "%s-%s_cleaned" % (
        src_lang, trg_lang) + "_full"
    cleaned_file = cleaned_file + "reversed.pkl" if src_reversed else cleaned_file + ".pkl"

    if os.path.isfile(os.path.join(PREPRO_DIR, cleaned_file)):
        print("File already preprocessed! Loading file....")
        pairs = load_cleaned_data(PREPRO_DIR, filename=cleaned_file)
    else:
        print("No preprocessed file found. Starting data preprocessing...")
        pairs = read_lines(os.path.join(start_root, DATA_DIR), FILENAME)
        pairs, path = preprocess_pipeline(pairs, cleaned_file, exp_contraction) #data/prepro/eng-deu_cleaned_full.pkl


    print("Sample from data:")
    print(random.choice(pairs))

    limit = 50000

    if limit:
        pairs = pairs[:limit]

    train_set, val_set, test_set = split_data(pairs)

    print("Data in train set:", len(train_set))
    print("Data in val set:", len(val_set))
    print("Data in test set:", len(test_set))


    print("Building vocabularies...")
    train_data = train_set+val_set

    # Build vocabularies based on dataset
    src_sents = [item[0] for item in train_data]
    trg_sents = [item[1] for item in train_data]

    max_src_l = max_length(src_sents)
    max_trg_l = max_length(trg_sents)

    print("Max sentence length in source sentences:", max_src_l)
    print("Max sentence length in source sentences:", max_trg_l)

    input_lang = build_vocab(src_sents, "eng")
    output_lang = build_vocab(trg_sents, "deu")

    print("Source vocabulary:", input_lang.num_words)
    print("Target vocabulary:", output_lang.num_words)

    if trimming:
        input_lang.trim(2)
        output_lang.trim(3)

        print("Source vocabulary:", input_lang.num_words)
        print("Target vocabulary:", output_lang.num_words)


    test_batches = [batch2TrainData(input_lang, output_lang, [random.choice(test_set) for _ in range(1)])
                        for _ in range(len(test_set))]

    # Configure models
    model_name = ''
    model_name += 'simple_nmt_model'+str(limit) if limit else 'simple_nmt_model_full'
    hidden_size = 512
    encoder_n_layers = 2
    decoder_n_layers = 2
    batch_size = 64
    input_size = input_lang.num_words
    output_size = output_lang.num_words
    embedding_size = 512

    print('Building encoder and decoder ...')
    encoder = EncoderLSTM(input_size=input_size, emb_size=embedding_size, hidden_size=hidden_size,
                         n_layers=encoder_n_layers)
    decoder = DecoderLSTM(output_size=output_size, emb_size=embedding_size, hidden_size=hidden_size, n_layers= decoder_n_layers)

    encoder = encoder.to(device)
    decoder = decoder.to(device)
    print('Models built:')
    print(encoder)
    print(decoder)

    clip = 50.0
    teacher_forcing_ratio = 0.3
    learning_rate = 0.0001 #0.0001
    decoder_learning_ratio = 2.0 #5.0
    n_iteration = 10000
    print_every = 100
    save_every = 500

    # Initialize optimizers
    print('Building optimizers ...')
    encoder_optimizer = optim.Adam(encoder.parameters(), lr=learning_rate)
    decoder_optimizer = optim.Adam(decoder.parameters(), lr=learning_rate * decoder_learning_ratio)


    # Run training iterations
    print("Starting Training!")
    start_time = datetime.now()
    val_loss, directory, train_history, val_history = trainIters(model_name, input_lang, output_lang, train_set, val_set, encoder, decoder, encoder_optimizer, decoder_optimizer,
                                     encoder_n_layers, decoder_n_layers, SAVE_DIR, n_iteration, batch_size,
                                     print_every, save_every, clip, FILENAME)

    end_time = datetime.now()
    duration = end_time-start_time
    print('Training duration: {}'.format(duration))

    test_loss = eval_test(test_batches, encoder, decoder)
    print("Test loss:", test_loss)

    print("Checkponits saved in %s" %(directory))

    #Log file name
    try:
        with open(os.path.join(start_root, EXPERIMENT_DIR, LOG_FILE), encoding="utf-8", mode="w") as f:
            #Logging to last_experiment.txt
            f.write(str(directory))
        with open(os.path.join(start_root, EXPERIMENT_DIR, "log_history.txt"), encoding="utf-8", mode="a") as hf:
            #Logging in the history document
            hf.write("Execution date: %s" % str(experiment_execution_time))
            hf.write("\nExperiment name:\n")
            hf.write(model_name)
            hf.write("\nDirectory:\n")
            hf.write(str(directory))
            hf.write("\n Number of samples:")
            hf.write(str(len(pairs)))
            hf.write("\n Max src length %s" % max_src_l)
            hf.write("\n Max trg length %s" % max_trg_l)
            hf.write("\n Learning rate: %s" % str(learning_rate))
            hf.write("\nAverage validation loss:\n")
            hf.write(str(val_loss))
            hf.write("\nTest loss:")
            hf.write(str(test_loss))
            hf.write("\nTraining iterations:")
            hf.write(str(n_iteration))
            hf.write("\n Training duration:")
            hf.write(str(duration))
            hf.write("\n**********************************\n")
    except IOError or TypeError or RuntimeError:
        print("Log to file failed!")

    print("Plotting results...")
    try:
        plot_training_results(model_name, train_history, val_history, SAVE_DIR, FILENAME, decoder_n_layers, hidden_size,
                          live_show=False)
        print("Plots stored in %s" %SAVE_DIR)

    except IOError or RuntimeError:
        pass