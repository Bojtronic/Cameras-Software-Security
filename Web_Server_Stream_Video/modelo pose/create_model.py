import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from ..detectors.person_detector import PersonDetector

data = pd.read_csv("pose_dataset.csv")

X = data.iloc[:, :-1].values.astype("float32")
y = data.iloc[:, -1].values.astype("int")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=True
)

model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(21,)),
    tf.keras.layers.Dense(64, activation="relu"),
    tf.keras.layers.Dense(64, activation="relu"),
    tf.keras.layers.Dense(4, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.fit(
    X_train,
    y_train,
    validation_data=(X_test, y_test),
    epochs=50,
    batch_size=32
)

model.save("pose_model.h5")

print("Modelo entrenado y guardado como pose_model.h5")
