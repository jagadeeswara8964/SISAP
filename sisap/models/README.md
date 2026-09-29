# models

This directory is reserved for locally cached machine-learning artifacts.

SISAP does not vendor model weights in the repository. The sentence-transformer
model `all-MiniLM-L6-v2` (~90 MB) is downloaded once by Hugging Face and cached
in the user's cache directory (`~/.cache/huggingface`) on first use.

Set `HF_HOME` to relocate that cache, for example:

```bash
export HF_HOME=/home/user/sisap/models/hf
```

If the model cannot be downloaded, SISAP automatically falls back to the
deterministic TF-IDF embedding backend so the application keeps working offline.
