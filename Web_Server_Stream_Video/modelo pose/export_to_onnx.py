import tensorflow as tf
import tf2onnx

model = tf.keras.models.load_model("pose_model.h5")

spec = (tf.TensorSpec((None, 21), tf.float32, name="input"),)

output_path = "pose_model.onnx"

model_proto, _ = tf2onnx.convert.from_keras(
    model,
    input_signature=spec,
    output_path=output_path,
    opset=13
)

print("Exportado a", output_path)
