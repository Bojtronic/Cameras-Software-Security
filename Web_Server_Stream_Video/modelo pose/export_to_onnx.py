import tensorflow as tf
import os

print("Cargando modelo...")
model = tf.keras.models.load_model("pose_model.h5")

print("Exportando a SavedModel...")
model.export("saved_pose_model")

print("Convirtiendo a ONNX...")

cmd = (
    "python -m onnxruntime.tools.convert_onnx "
    "--input saved_pose_model "
    "--output pose_model.onnx "
    "--opset 13"
)

print(cmd)
os.system(cmd)

print("ONNX generado: pose_model.onnx")
