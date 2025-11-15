"""
Mock sklearn implementation for testing purposes.

This module provides a mock implementation of sklearn functionality
to enable testing without requiring the full scikit-learn library.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Union, Tuple
from unittest.mock import MagicMock


class MockClassifier:
    """Mock classifier implementation."""

    def __init__(self, **kwargs):
        """Initialize the mock classifier."""
        self.params = kwargs
        self.classes_ = np.array([0, 1])
        self.feature_importances_ = np.random.rand(10)
        self.n_features_in_ = 10
        self.n_outputs_ = 1
        self._fitted = False

    def fit(self, X, y):
        """Mock fit method."""
        self._fitted = True
        self.classes_ = np.unique(y)
        self.n_features_in_ = X.shape[1] if hasattr(X, 'shape') else len(X[0])
        return self

    def predict(self, X):
        """Mock predict method."""
        if not self._fitted:
            raise ValueError("Model not fitted")
        return np.random.choice(self.classes_, size=len(X) if hasattr(X, '__len__') else 1)

    def predict_proba(self, X):
        """Mock predict_proba method."""
        if not self._fitted:
            raise ValueError("Model not fitted")
        n_samples = len(X) if hasattr(X, '__len__') else 1
        n_classes = len(self.classes_)
        # Generate random probabilities that sum to 1
        probs = np.random.rand(n_samples, n_classes)
        probs = probs / probs.sum(axis=1, keepdims=True)
        return probs

    def score(self, X, y):
        """Mock score method."""
        predictions = self.predict(X)
        return float(np.mean(predictions == y))


class MockRegressor:
    """Mock regressor implementation."""

    def __init__(self, **kwargs):
        """Initialize the mock regressor."""
        self.params = kwargs
        self.feature_importances_ = np.random.rand(10)
        self.n_features_in_ = 10
        self.n_outputs_ = 1
        self._fitted = False

    def fit(self, X, y):
        """Mock fit method."""
        self._fitted = True
        self.n_features_in_ = X.shape[1] if hasattr(X, 'shape') else len(X[0])
        return self

    def predict(self, X):
        """Mock predict method."""
        if not self._fitted:
            raise ValueError("Model not fitted")
        n_samples = len(X) if hasattr(X, '__len__') else 1
        return np.random.rand(n_samples)

    def score(self, X, y):
        """Mock score method."""
        predictions = self.predict(X)
        return float(np.corrcoef(predictions, y)[0, 1])


class MockStandardScaler:
    """Mock StandardScaler implementation."""

    def __init__(self, **kwargs):
        """Initialize the mock scaler."""
        self.params = kwargs
        self.mean_ = None
        self.scale_ = None
        self.n_features_in_ = None
        self._fitted = False

    def fit(self, X):
        """Mock fit method."""
        X_array = np.array(X)
        self.mean_ = np.mean(X_array, axis=0)
        self.scale_ = np.std(X_array, axis=0)
        self.n_features_in_ = X_array.shape[1]
        self._fitted = True
        return self

    def transform(self, X):
        """Mock transform method."""
        if not self._fitted:
            raise ValueError("Scaler not fitted")
        X_array = np.array(X)
        return (X_array - self.mean_) / self.scale_

    def fit_transform(self, X):
        """Mock fit_transform method."""
        return self.fit(X).transform(X)


class MockModelSelection:
    """Mock model selection module."""

    @staticmethod
    def train_test_split(*arrays, **options):
        """Mock train_test_split function."""
        test_size = options.get('test_size', 0.25)
        random_state = options.get('random_state', None)

        if random_state is not None:
            np.random.seed(random_state)

        result = []
        for arr in arrays:
            arr_array = np.array(arr)
            n_samples = len(arr_array)
            indices = np.random.permutation(n_samples)
            split_idx = int(n_samples * (1 - test_size))

            train_indices = indices[:split_idx]
            test_indices = indices[split_idx:]

            result.append(arr_array[train_indices])
            result.append(arr_array[test_indices])

        return tuple(result)

    @staticmethod
    def cross_val_score(estimator, X, y, cv=5):
        """Mock cross_val_score function."""
        return np.random.rand(cv)


class MockMetrics:
    """Mock metrics module."""

    @staticmethod
    def accuracy_score(y_true, y_pred):
        """Mock accuracy_score function."""
        return float(np.mean(np.array(y_true) == np.array(y_pred)))

    @staticmethod
    def precision_score(y_true, y_pred, **kwargs):
        """Mock precision_score function."""
        return np.random.rand()

    @staticmethod
    def recall_score(y_true, y_pred, **kwargs):
        """Mock recall_score function."""
        return np.random.rand()

    @staticmethod
    def f1_score(y_true, y_pred, **kwargs):
        """Mock f1_score function."""
        return np.random.rand()

    @staticmethod
    def mean_squared_error(y_true, y_pred):
        """Mock mean_squared_error function."""
        return float(np.mean((np.array(y_true) - np.array(y_pred)) ** 2))


class MockEnsemble:
    """Mock ensemble module."""

    def __init__(self):
        """Initialize the mock ensemble module."""
        self.RandomForestClassifier = MockClassifier
        self.GradientBoostingRegressor = MockRegressor


# Create the mock sklearn module
mock_sklearn = MagicMock()
mock_sklearn.ensemble = MockEnsemble()
mock_sklearn.model_selection = MockModelSelection()
mock_sklearn.preprocessing = MagicMock()
mock_sklearn.preprocessing.StandardScaler = MockStandardScaler
mock_sklearn.metrics = MockMetrics()


def apply_sklearn_mock():
    """Apply the sklearn mock to prevent import errors."""
    import sys
    from unittest.mock import MagicMock

    # Replace the sklearn module in sys.modules
    sys.modules['sklearn'] = mock_sklearn
    sys.modules['sklearn.ensemble'] = mock_sklearn.ensemble
    sys.modules['sklearn.model_selection'] = mock_sklearn.model_selection
    sys.modules['sklearn.preprocessing'] = mock_sklearn.preprocessing
    sys.modules['sklearn.metrics'] = mock_sklearn.metrics
