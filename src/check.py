import tensorflow as tf
# Check GPU availability
if tf.test.is_gpu_available():
    print("GPU available: ", tf.config.list_physical_devices('GPU'))
else:
    print("No GPU available, training on CPU.")
