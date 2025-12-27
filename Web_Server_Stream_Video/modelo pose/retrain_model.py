import pandas as pd
import tensorflow as tf
from sklearn.preprocessing import StandardScaler

model = tf.keras.models.load_model("pose_model.h5")

data = pd.read_csv("pose_dataset.csv", header=None)

X = data.iloc[:, :-1]
y = data.iloc[:, -1]

scaler = StandardScaler()
X = scaler.fit_transform(X)

model.fit(X, y, epochs=10)

model.save("pose_model.h5")
print("Modelo reentrenado")
