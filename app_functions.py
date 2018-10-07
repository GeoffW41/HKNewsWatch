"""
This module contains all NLP functions used by the HKNewsWatch App.

To-do:
Assets migration to Amazon S3 (finders and wordclouds)
Reduce wordcloud generation time/
"""

import pickle
import json
from time import time
from multiprocessing import Pool
from itertools import product
from nltk.collocations import BigramAssocMeasures
import pandas as pd
import numpy as np
import wordcloud

#Word Cloud Parameters
font_path = 'assets/AquaKana.ttc'
w = wordcloud.WordCloud(font_path=font_path, background_color='White',
                        font_step=1, min_font_size=8,
                        width=550, height=620,
                        relative_scaling=0.3, colormap='Dark2')

# Dictionary for Newssource Translation
translate_dict = json.load(open('newssource_chinese_trans.json','r'))

def prepare_data(keywords, sources):
    """
    Pipeline to Create Items needed by the app. To be passed to job queue in
    Worker dyno.
    """
    results = process(keywords, sources)
    df_collocation = compute_collocation_table(results)
    img, img_filename = generate_wordcloud(results, keywords, sources)

    return df_collocation, img, img_filename

def _bidirection_score_ngrams(finder, score_fn, filter_fn):
    """Generates of (ngram, score) pairs as determined by the scoring
    function provided.
    """
    for tup in finder.ngram_fd:
        permutations = [(0, 1), (1, 0)]
        filtereds = [filter_fn(tup[i], tup[j]) for i, j in permutations]
        if all(filtereds):
            continue

        score = finder.score_ngram(score_fn, *tup)
        if score is None:
            continue

        for (i, j), filtered in zip(permutations, filtereds):
            if not filtered:
                yield (tup[i], tup[j]), score

def bidirection_score_ngrams(finder, score_fn, filter_fn):
    """Returns a sequence of (ngram, score) pairs ordered from highest to
    lowest score, as determined by the scoring function provided.
    """
    return sorted(
        _bidirection_score_ngrams(finder, score_fn, filter_fn),
        key=lambda t: (-t[1], t[0]),
    )

def get_collocation(keywords, source):
    """
    Filtering NLTK BigramFinder Object to get the score of maximum likelyhood
    of words (length >= 2) co-occuring with the keywords.
    Returns a dataframe with the scores and the associated words.
    """
    bgm = BigramAssocMeasures()

    word_filter = lambda w1, w2: keywords not in w1 or len(w2) < 2

    filename = f"finder_{source}_trimmed.sav"
    finder = pickle.load(open(filename, 'rb'))

    try:
        scorelist = bidirection_score_ngrams(finder, bgm.likelihood_ratio, word_filter)
        word_pairs, scores = zip(*scorelist)
        key, asso = zip(*word_pairs)
        df = pd.DataFrame(np.array([asso, scores]).transpose(),
                          columns=['Collocation','Score'])
    except:
        # for cases where no word collocations are found
        df = pd.DataFrame(np.array([[np.NaN, np.NaN]]),
                          columns=['Collocation','Score'])

    df['Keyword'] = keywords
    df['Source'] = source
    return df.drop_duplicates('Collocation').reset_index(drop=True)[:80]

def process(keywords, sources):
    """
    Search word collocations with multiprocessing.
    """
    with Pool(processes=4) as p:
        results = p.starmap(get_collocation, product([keywords],sources))
    return results

def compute_collocation_table(results):
    """
    Compute a dataframe to show the Top 15 most frequently co-occured words,
    with regard to each news source.
    """
    df_collocation = pd.DataFrame()
    for df in results:
        source = translate_dict[df.Source[0]]
        df_collocation = pd.concat([df_collocation, df['Collocation'].rename(source)], axis=1)[:15]
    return df_collocation

def compute_freq_dict(results):
    """
    Compute Frequency Dictionary for generating Wordcloud
    """
    df = pd.concat([result for result in results], axis=0)
    df['Score'] = df['Score'].astype('float')
    df_sum = df.groupby('Collocation').Score.sum()
    # Add Keyword to Wordcloud
    df_sum = df_sum.append(pd.Series(df_sum.max()*5, index=df['Keyword'][0]))
    return df_sum.to_dict()

def generate_wordcloud(results, keyword, sources):
    """
    Generate wordcloud based on word collocation scores.
    """
    sources.sort()
    sources_str = '_'.join(sources)
    image_filename = f'wordcloud_{keyword}_{sources_str}.png'

    freq_dict = compute_freq_dict(results)
    if len(freq_dict) < 20:
        return None, 'nodata.png'

    img = w.generate_from_frequencies(freq_dict)
    return img, image_filename
