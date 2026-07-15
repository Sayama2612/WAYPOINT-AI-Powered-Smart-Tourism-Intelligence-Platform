import unittest
import numpy as np

from utils import explainability


class FakeShap:
    def __init__(self, values):
        # values: 2D numpy array
        self.values = np.array(values)


class TestExplainability(unittest.TestCase):
    def test_summarize_shap_explanation_basic(self):
        # two features, one positive, one negative
        vals = [[0.5, -0.2]]
        fs = FakeShap(vals)
        positives, negatives = explainability.summarize_shap_explanation(fs, ['feature_a', 'feature_b'], row_index=0, top_pos=2, top_neg=2)
        self.assertIn('feature_a: 0.50', positives)
        self.assertIn('feature_b: -0.20', negatives)

    def test_generate_consumer_sentences_mappings(self):
        positives = ['crowd_index: 0.50', 'eco_score: 1.20', 'unknown_feat: 0.30']
        negatives = ['weather_risk: -0.80', 'transport_cost: -1.00', 'crowd_index: -0.40']
        sents = explainability.generate_consumer_sentences(positives, negatives)
        # check that mapped sentences are present
        self.assertIn('Lower crowding improves suitability', sents)
        self.assertIn('High sustainability / eco score', sents)
        self.assertIn('Weather risk may reduce attractiveness', sents)
        self.assertIn('Higher travel or local cost reduces fit', sents)


if __name__ == '__main__':
    unittest.main()
