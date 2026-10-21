# Model and dependency notices

The embedding model is
[sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41),
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0.
Its model card specifies 384-dimensional vectors and mean pooling for direct
Transformers use. This suite uses CPU Transformers inference and normalization.
Weights and tokenizer files are not distributed in this repository.

The six committed model hashes were computed from the pinned snapshot already
cached by the reference retrieval workbench, copied into this project's private
cache without modifying the source. Downloads resolve the same explicit revision.
The adapter checks all six hashes before importing the model runtime.

PyTorch, NumPy, Transformers, Hugging Face Hub, Safetensors, and transitive
packages retain their upstream licenses. The package lock records the actual
reference environment, not a license override or universal dependency guarantee.
The source corpus contains no copied external documents or real operating guidance.
