import unittest
from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np

from scripts.train_uv_model import fourier, rolling_forecasts


class RollingForecastTest(unittest.TestCase):
    def test_two_day_forecast_uses_observations_from_two_days_earlier(self):
        class State:
            def __init__(self, latest):
                self.latest = latest

            def get_forecast(self, *, steps, exog):
                return SimpleNamespace(predicted_mean=np.array([self.latest + 1, self.latest + 2]))

            def extend(self, values, *, exog):
                return State(values[0])

        days = [date(2026, 1, 1) + timedelta(days=i) for i in range(5)]
        values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        one_day, two_days = rolling_forecasts(State(20.0), days, values, fourier(days), 2, 5)
        np.testing.assert_array_equal(one_day, [21.0, 31.0, 41.0])
        np.testing.assert_array_equal(two_days[1:], [22.0, 32.0])
        self.assertTrue(np.isnan(two_days[0]))
