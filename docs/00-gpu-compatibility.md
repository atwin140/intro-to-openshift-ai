# OAI-00-GPU — RTX 4070 feasibility and support assessment

Applies to the proposed RTX 4070 12 GB lab with OpenShift 4.22 / OpenShift AI 3.5. Sources checked 2026-09-22. This is a read-only assessment supporting OAI-00, not an installation stage. Required role: no cluster access to read; cluster-admin and existing host access for environment evidence.

## Conclusion

The RTX 4070 is a reasonable candidate for the small, single-GPU chatbot. Public specifications support technical feasibility. The lab has now demonstrated driver loading and CUDA vector addition on both workers (see the separate progress record). Stage 4 has now demonstrated inference on gpu-worker-01 with the pinned runtime and selected AWQ model; the original 4K-context test retained 1011 MiB free, and the later 16K-context test retained 831 MiB free in sampled measurements. Answer-quality acceptance remains open. The separate image-generation extension has demonstrated inference on gpu-worker-02; the chat model has not been relocated there. Treat the complete configuration as an unsupported lab experiment unless the vendors explicitly confirm otherwise. We recommend continuing staged validation with the existing cards before considering a hardware change.

## What the evidence establishes

| Layer | Verified documentation fact | Meaning for this lab |
| --- | --- | --- |
| GPU compute | NVIDIA lists GeForce RTX 4070 at compute capability 8.9. [CUDA GPU table](https://developer.nvidia.com/cuda/gpus) | Hardware generation is suitable for CUDA inference. This does not validate an image or model. |
| Linux driver | Driver 595.91.07 lists desktop RTX 4070 IDs 2709 and 2786. [Supported products](https://download.nvidia.com/XFree86/Linux-x86_64/595.91.07/README/supportedchips.html) | There is a Linux driver path. Local device and driver-container tests are recorded separately in lab progress; serving-image compatibility still needs validation. |
| GPU Operator | 26.7 lists RHCOS/OpenShift 4.18–4.22 and driver 595.91.07 as its default/recommended branch version. Its hardware tables omit GeForce RTX 4070. [Platform matrix](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html) | Platform compatibility does not confer support on an unlisted card. |
| Upstream serving engine | Current vLLM GPU requirements include NVIDIA compute capability 7.5 or later. [vLLM requirements](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/) | RTX 4070 meets that hardware threshold. A particular Red Hat image can have additional restrictions. |
| Red Hat serving support | The Red Hat AI Inference 3.5 accelerator table includes H100 and several Ada data-center GPUs, but not GeForce RTX 4070. [Red Hat accelerator table](https://docs.redhat.com/en/documentation/red_hat_ai/3/html/supported_product_and_hardware_configurations/rhaiis-supported-ai-accelerators_supported-configurations) | Do not present the lab as a supported customer inference configuration. |

Compute capability identifies the GPU instruction/features generation. It is not a measure of available memory or overall speed. vLLM is an inference engine: it loads the model and manages generation requests and the key/value (KV) cache used during generation.

The conclusion about lab feasibility is an inference from these separate sources, not a published certification of RTX 4070 with this exact software stack.

## Virtualized worker considerations

GPU identity at a guest PCI address does not prove bare-metal deployment. Record virtualization evidence separately from the original hardware description. NVIDIA lists virtual machines with GPU passthrough as a deployment option, but that does not add RTX 4070 to its supported hardware list. Guest-visible devices still need driver initialization and computation tests; hypervisor assignment and reset behavior are not established by `lspci`. Do not install vGPU or OpenShift Virtualization components merely because a worker is a virtual machine. [NVIDIA deployment options](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html)

## Driver and operator selection

26.7 is the current supported GPU Operator line in the reviewed matrix; 26.3 is deprecated. A catalog can still offer older, unsupported releases. Recheck before installation, and pin the selected bundle and driver image after testing. [Operator lifecycle](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/platform-support.html)

NVIDIA recommends open kernel modules on GPUs that support them. Ada supports that approach, but open and proprietary modules must not be mixed. This is guidance for choosing the operator-managed driver configuration, not an instruction to run a standalone driver installer on CoreOS. [Driver kernel modules](https://download.nvidia.com/XFree86/Linux-x86_64/595.91.07/README/kernel_open.html)

The initial implementation must use the verified OpenShift driver-toolkit/operator path. Verify the actual driver container, kernel build, module loading, firmware, and any Secure Boot requirements before calling the driver ready. Do not infer readiness from a general driver product list. See the [NVIDIA OpenShift procedure](https://docs.nvidia.com/datacenter/cloud-native/openshift/latest/install-gpu-ocp.html).

Choose a host driver that directly supports the inference image's CUDA requirements. Do not rely on a `cuda-compat` forward-compatibility package to make an older driver work on GeForce: NVIDIA limits that mechanism to data-center GPUs, selected NGC Server Ready RTX products, and Jetson. The RTX product name alone does not establish eligibility. [CUDA forward-compatibility restrictions](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html)

## Memory plan

12 GB is the reported physical-device budget, not 12 GB available exclusively for weights. Confirm actual device memory in MiB with `nvidia-smi`. Include weights, runtime allocations, CUDA workspaces/graphs, and KV cache for both active users. Leave room for any existing display use or other GPU processes.

Illustrative weight-only arithmetic, not model benchmarks:

| Parameter count | Two bytes per parameter, approximately | Implication |
| --- | --- | --- |
| 3 billion | 6.0 GB / 5.6 GiB | Reasonable starting scale; runtime and context still need measurement |
| 4 billion | 8.0 GB / 7.5 GiB | Less headroom; investigate only after runtime profiling |
| 7 billion | 14.0 GB / 13.0 GiB | Does not fit unquantized within the reported device capacity |

Quantization stores weights at lower precision to reduce memory. It also adds format, kernel, and quality constraints. Do not assume that any 4-bit download will run in the chosen serving image. For a new model evaluation, small models are a starting point; this lab ultimately selected the pinned 7B AWQ model after testing. Use command-quality tests and measured memory to decide, not parameter count alone.

Keep context length and simultaneous generation requests bounded. Two browser users do not require two model replicas: the server can queue requests. A runtime's memory-utilization setting is a process budget, not a hardware memory partition. Final limits belong in OAI-04 after image and model verification.

## Known differences from H100

- RTX 4070 does not support MIG. H100 supports MIG, with profile choices depending on the exact model. Keep H100 settings in a separate overlay. [MIG hardware](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/supported-gpus.html)
- Time-slicing does not provide GPU memory isolation. Whole-GPU allocation remains the initial design. [GPU sharing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/24.9.2/gpu-sharing.html)
- NVIDIA Data Center GPU Manager (DCGM) exposes limited functionality on non-data-center GPUs. Missing metrics or unsupported diagnostics need investigation; they do not by themselves prove CUDA inference cannot run. Do not disable all monitoring preemptively. [DCGM platform scope](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/getting-started.html)
- H100 support does not validate the customer's full host, OpenShift, driver, runtime, and model combination. Validate that configuration independently.

## Validation gates and checkpoint

These are acceptance gates for later executable stages, not commands to install anything now:

1. OAI-00/01: identify every GPU by node and PCI address; confirm GPU count and actual VRAM. Distinguish GPU display/3D functions from HDMI audio devices.
2. OAI-01: operator-managed driver loads; `nvidia-smi` succeeds; device plugin advertises the correct whole-GPU count. Run a pinned CUDA computation test on each GPU worker, not just `nvidia-smi`.
3. OAI-02/04: selected OpenShift AI serving components reconcile and the chosen inference image can initialize on the GPU.
4. OAI-04/05: chosen model fits with headroom under one and two users; no out-of-memory errors; command-quality acceptance passes.

Only after these checks can the guide say “works in this lab.” None establishes vendor support for an unlisted card. Record failing command, node, image/driver versions, and logs if a gate fails; stop the dependent stage before trying a different combination.

No configuration is applied by this assessment, so no rollback is required. Deployment and cleanup instructions will be supplied in their own stages.
