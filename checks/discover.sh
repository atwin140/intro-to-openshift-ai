#!/usr/bin/env bash
# OAI-00. Reads cluster state; does not install or configure resources.
set -u
export LC_ALL=C
read_errors=0

if ! command -v oc >/dev/null 2>&1; then
  printf '%s\n' 'oc is not available. Use the OpenShift CLI for your cluster.' >&2
  exit 1
fi

# Bound each request. API absence is reported separately from failed reads.
oc() {
  command oc --request-timeout=30s "$@"
}

run() {
  printf '\n###'
  printf ' %q' "$@"
  printf '\n'
  "$@"
  local result=$?
  if [ "$result" -ne 0 ]; then
    read_errors=$((read_errors + 1))
    printf 'CHECK INCOMPLETE: exit %s; preserve the error for review.\n' "$result" >&2
  fi
  return 0
}

if ! oc whoami; then
  printf '%s\n' 'Stop: authenticate to the intended lab cluster, then rerun.' >&2
  exit 1
fi

run oc config current-context
run oc version
run oc auth can-i '*' '*' --all-namespaces
run oc get clusterversion version -o 'jsonpath={.status.desired.version}{"\n"}{range .status.history[*]}{.version}{"\t"}{.state}{"\t"}{.completionTime}{"\n"}{end}{range .status.conditions[*]}{.type}{"="}{.status}{"\t"}{.message}{"\n"}{end}'
run oc get clusteroperators
run oc get machineconfigpools
run oc get nodes -o wide
run oc get nodes -o 'custom-columns=NAME:.metadata.name,CPU:.status.capacity.cpu,CPU_ALLOC:.status.allocatable.cpu,MEMORY:.status.capacity.memory,MEM_ALLOC:.status.allocatable.memory,ARCH:.status.nodeInfo.architecture,OS:.status.nodeInfo.osImage,KERNEL:.status.nodeInfo.kernelVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion,UNSCHEDULABLE:.spec.unschedulable'
run oc get nodes -o 'go-template={{range .items}}{{.metadata.name}}{{"\n  GPU capacity="}}{{index .status.capacity "nvidia.com/gpu"}}{{" allocatable="}}{{index .status.allocatable "nvidia.com/gpu"}}{{"\n  taints="}}{{.spec.taints}}{{"\n"}}{{range $k, $v := .metadata.labels}}{{printf "  %s=%s\n" $k $v}}{{end}}{{end}}'
run oc get storageclasses -o yaml
run oc get csidrivers
run oc get pvc -A -o 'custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,PHASE:.status.phase,CLASS:.spec.storageClassName,REQUEST:.spec.resources.requests.storage,CAPACITY:.status.capacity.storage,ACCESS:.spec.accessModes'

# Discover extension APIs before attempting optional resource reads.
if ! resource_names=$(oc api-resources --verbs=list -o name); then
  printf '%s\n' 'Stop: API discovery failed. Return the error and preceding output.' >&2
  exit 1
fi

has_resource() {
  printf '%s\n' "$resource_names" | command grep -Fqx -- "$1"
}

for kind in clusterserviceversions.operators.coreos.com subscriptions.operators.coreos.com catalogsources.operators.coreos.com; do
  if has_resource "$kind"; then
    case "$kind" in
      clusterserviceversions.*)
        # OLM copies CSVs to other namespaces; those are not extra installations.
        run oc get "$kind" -A -l '!olm.copiedFrom' -o 'custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,VERSION:.spec.version,PHASE:.status.phase' ;;
      subscriptions.*)
        run oc get "$kind" -A -o 'custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name,PACKAGE:.spec.name,CHANNEL:.spec.channel,SOURCE:.spec.source,APPROVAL:.spec.installPlanApproval,INSTALLED:.status.installedCSV' ;;
      *) run oc get "$kind" -A ;;
    esac
  else
    printf '\nAPI not served: %s\n' "$kind"
  fi
done

# Known API names are checked against discovery, not presumed installed.
for kind in \
  datascienceclusters.datasciencecluster.opendatahub.io \
  dscinitializations.dscinitialization.opendatahub.io \
  clusterpolicies.nvidia.com \
  nodefeaturediscoveries.nfd.openshift.io \
  clusterextensions.olm.operatorframework.io; do
  if has_resource "$kind"; then
    run oc get "$kind" -A -o yaml
  else
    printf '\nAPI not served: %s\n' "$kind"
  fi
done

for group in serving.kserve.io nfd.openshift.io nvidia.com; do
  run oc api-resources --api-group="$group"
done

if has_resource packagemanifests.packages.operators.coreos.com; then
  printf '\n### Relevant catalog packages; empty output is not an installation result\n'
  if packages=$(oc get packagemanifests -n openshift-marketplace -o 'custom-columns=NAME:.metadata.name,CATALOG:.status.catalogSource,DEFAULT_CHANNEL:.status.defaultChannel'); then
    printf '%s\n' "$packages" | command grep -Ei '(^NAME[[:space:]]|nvidia|gpu|(^|[[:space:]])nfd([[:space:]]|$)|node.feature|rhods|openshift.ai)' || true
  else
    read_errors=$((read_errors + 1))
    printf '%s\n' 'CHECK INCOMPLETE: package inventory failed.' >&2
  fi
fi

printf '\nDiscovery collection finished with %s failed reads.\n' "$read_errors"
printf '%s\n' 'This is a collection result, not a cluster-health or compatibility verdict.'
if [ "$read_errors" -ne 0 ]; then
  exit 1
fi
