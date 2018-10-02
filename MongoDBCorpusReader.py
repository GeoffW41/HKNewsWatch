# import jieba
# jieba.set_dictionary('Preprocessing/dict_updated.txt')

import pymongo
from nltk.data import LazyLoader
from nltk.util import AbstractLazySequence, LazyMap, LazyConcatenation

class MongoDBLazySequence(AbstractLazySequence):
    def __init__(self, host='mongodb+srv://newswatch:jiebaLDAplotly@cluster0-lmt3i.mongodb.net/test?retryWrites=true', db='newsdb', collection='news', field='Tokens', search_criteria={}):
        self.conn = pymongo.MongoClient(host)
        self.collection = self.conn[db][collection]
        self.field = field
        self.search_criteria = search_criteria

    def __len__(self):
        return self.collection.estimated_document_count()

    def iterate_from(self, start):
        f = lambda d: d.get(self.field, '')
        return iter(LazyMap(f, self.collection.find(self.search_criteria, projection=[self.field], skip=start)))

class MongoDBCorpusReader(object):
    def __init__(self, **kwargs):
        self._seq = MongoDBLazySequence(**kwargs)

    def tokens(self):
        return self._seq   
