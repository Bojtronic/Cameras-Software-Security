import pandas as pd
import tensorflow as tf

model = tf.keras.models.load_model("pose_model.h5")

data = pd.read_csv("pose_dataset.csv")

X = data.iloc[:, :-1].values.astype("float32")
y = data.iloc[:, -1].values.astype("int")

model.fit(X, y, epochs=10, batch_size=32)

model.save("pose_model.h5")

print("Modelo reentrenado")
