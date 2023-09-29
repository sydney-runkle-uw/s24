from server import PredictionCache  # type: ignore

import numpy as np

prediction_cache = PredictionCache()

coefs = np.array([1, 2, 3], dtype=np.float32).reshape(-1, 1)

inputs = np.array([1, 2, 3], dtype=np.float32).reshape(-1, 1)
inputs_delta = np.array([0.00004, 0.00001, -0.00004], dtype=np.float32).reshape(-1, 1)

prediction_cache.SetCoefs(coefs=coefs)
resp = prediction_cache.Predict(X=inputs)
print(f"value={resp.value}, hit={resp.hit}")  # should be 14, false
resp = prediction_cache.Predict(X=inputs)
print(f"value={resp.value}, hit={resp.hit}")  # should be 14, true
resp = prediction_cache.Predict(X=inputs + inputs_delta)
print(f"value={resp.value}, hit={resp.hit}")  # should be 14, true
resp = prediction_cache.Predict(X=inputs + 1)
print(f"value={resp.value}, hit={resp.hit}")  # should be 20, false
