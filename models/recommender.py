import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

class ContentRecommender:
    """Simple content-based recommender using activities and attributes."""
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df['features'] = (self.df['activities'].fillna('') + ' ' + self.df['climate'].fillna(''))
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.df['features'])

    def recommend(self, dest_name, topn=5):
        if dest_name not in self.df['destination_name'].values:
            return []
        idx = self.df.index[self.df['destination_name'] == dest_name][0]
        cosine_sim = linear_kernel(self.tfidf_matrix[idx:idx+1], self.tfidf_matrix).flatten()
        sim_scores = list(enumerate(cosine_sim))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        results = []
        for i, score in sim_scores[1: topn+1]:
            row = self.df.iloc[i].to_dict()
            row['score'] = float(score)
            results.append(row)
        return results
