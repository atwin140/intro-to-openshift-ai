import importlib.metadata, json, pathlib, torch
from huggingface_hub import snapshot_download
print("vllm", importlib.metadata.version("vllm"), "torch",torch.__version__, "CUDA build",torch.version.cuda, flush=True)
path = snapshot_download(repo_id="Qwen/Qwen2.5-Coder-7B-Instruct-AWQ", revision="8e8ed243bbe6f9a5aff549a0924562fc719b2b8a", local_dir="/models/qwen-coder-7b", allow_patterns=["*.json","*.safetensors","*.txt","LICENSE","README.md"], max_workers=3)
index=json.loads(pathlib.Path(path,"model.safetensors.index.json").read_text())
for name in set(index["weight_map"].values()):
 assert pathlib.Path(path,name).stat().st_size > 0, name
pathlib.Path(path,"REVISION").write_text("8e8ed243bbe6f9a5aff549a0924562fc719b2b8a\n")
print("DOWNLOAD-VERIFIED",path,"weight_bytes",index["metadata"]["total_size"],flush=True)
