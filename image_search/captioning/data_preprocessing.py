import os
import re
import pickle
from tqdm import tqdm
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

def load_captions(captions_file):
    with open(captions_file, 'r') as f:
        next(f)
        text = f.read()
    mapping = {}
    for line in tqdm(text.strip().split('\n')):
        tokens = line.split(',')
        if len(tokens) < 2:
            continue
        image_id, caption = tokens[0], " ".join(tokens[1:])
        image_id = image_id.split('.')[0]
        if image_id not in mapping:
            mapping[image_id] = []
        mapping[image_id].append(caption)
    return mapping

def clean_captions(mapping):
    for key, captions in mapping.items():
        for i in range(len(captions)):
            caption = captions[i].lower()
            caption = re.sub(r'[^a-z ]+', '', caption)
            caption = re.sub(r'\s+', ' ', caption)
            caption = 'startseq ' + ' '.join([w for w in caption.split() if len(w)>1]) + ' endseq'
            captions[i] = caption
    return mapping

def create_tokenizer(captions_list):
    tokenizer = Tokenizer()
    tokenizer.fit_on_texts(captions_list)
    return tokenizer

def max_caption_length(captions_list):
    return max(len(caption.split()) for caption in captions_list)
