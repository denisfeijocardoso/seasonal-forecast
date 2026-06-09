from sklearn.ensemble import RandomForestRegressor 

class CalibrationModel:

    def fit(self, X, y):
        ...

    def predict(self, X):
        ...

class LinearRegressionCalibration(CalibrationModel):
    ...

class CoxCalibration(CalibrationModel):
    ...

class RandomForestCalibration(CalibrationModel):
    ...

class XGBoostCalibration(CalibrationModel):
    ...
    