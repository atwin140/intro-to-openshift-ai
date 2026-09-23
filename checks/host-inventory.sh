#!/usr/bin/env bash
# Read-only host checks. Run inside an authorized node-debug chroot.
set -eu
printf 'Kernel: '; uname -r
printf '\nVirtualization detection (none means no detected virtualization):\n'
if command -v systemd-detect-virt >/dev/null; then systemd-detect-virt || true; fi
printf '\nNVIDIA PCI devices (includes audio functions):\n'
if command -v lspci >/dev/null; then lspci -Dnnk -d 10de:; fi
printf '\nNVIDIA display/3D controllers from sysfs:\n'
count=0
for device in /sys/bus/pci/devices/*; do
  [ "$(cat "$device/vendor")" = 0x10de ] || continue
  case "$(cat "$device/class")" in
    0x03*)
      count=$((count + 1))
      printf 'PCI=%s vendor=%s device=%s class=%s driver=%s\n' \
        "${device##*/}" "$(cat "$device/vendor")" "$(cat "$device/device")" \
        "$(cat "$device/class")" "$(readlink "$device/driver" || true)"
      ;;
  esac
done
printf 'NVIDIA display/3D controller count: %s\n' "$count"
printf '\nLoaded GPU-related modules:\n'
awk '$1 ~ /^(nvidia|nouveau)/ {print}' /proc/modules
printf '\nNVIDIA driver version:\n'
if [ -r /proc/driver/nvidia/version ]; then cat /proc/driver/nvidia/version; else printf 'Not present\n'; fi
printf '\nGPU memory and driver query:\n'
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,pci.bus_id,memory.total,driver_version --format=csv
else
  printf 'nvidia-smi not installed on host; memory and runtime checks remain pending\n'
fi
printf '\nSecure Boot:\n'
if [ ! -d /sys/firmware/efi ]; then
  printf 'No EFI firmware interface exposed; guest Secure Boot not applicable, hypervisor firmware state not inspected\n'
elif command -v mokutil >/dev/null; then
  mokutil --sb-state
else
  printf 'UEFI detected; mokutil unavailable, Secure Boot state unverified\n'
fi
