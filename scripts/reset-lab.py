#!/usr/bin/env python3
"""Preview-first, staged reset for this lab. Never exports credentials."""
import argparse
import json
import subprocess
import sys
import time

PROJECT = 'intro-openshift-ai'
TEST_PROJECT = 'intro-ai-gpu-checks'
BINDING = PROJECT + '-model-server-auth-delegator'
CRDS = {
    'isvc': 'inferenceservices.serving.kserve.io',
    'dsc': 'datascienceclusters.datasciencecluster.opendatahub.io',
    'cp': 'clusterpolicies.nvidia.com',
    'nfd': 'nodefeaturediscoveries.nfd.openshift.io',
}


class Stop(RuntimeError):
    pass


class Reset:
    def __init__(self, args):
        self.args = args
        if not args.execute and (args.confirm is not None or args.ack_dedicated_lab):
            raise Stop('Confirmation flags were supplied without --execute. Nothing changed. '
                       'Add --execute to perform the reset, or omit --confirm and '
                       '--ack-dedicated-lab for a read-only preview.')
        # Freeze the selected context rather than following subsequent context switches.
        context = args.context or self.raw(['config', 'current-context'], prefix=['oc']).strip()
        self.prefix = ['oc', '--context', context, '--request-timeout=30s']
        self.server = self.raw(['whoami', '--show-server']).strip()
        self.cluster_id = self.get('clusterversion', 'version')['spec']['clusterID']
        self.apis = {x['metadata']['name'] for x in self.items('customresourcedefinitions')}
        print(f'Context: {context}\nAPI: {self.server}\nCluster ID: {self.cluster_id}')
        print(f'Stage: {args.stage}; mode: {"EXECUTE" if args.execute else "PREVIEW (read-only)"}')
        if self.cluster_id != args.expected_cluster_id:
            raise Stop('Cluster ID mismatch. No changes made.')
        if self.raw(['auth', 'can-i', '*', '*', '--all-namespaces']).strip() != 'yes':
            raise Stop('This reset requires an authenticated cluster administrator.')
        if args.execute and args.confirm != f'RESET-{args.stage.upper()}':
            raise Stop('Execution requires the exact stage confirmation described in --help.')
        if args.execute and not args.ack_dedicated_lab:
            raise Stop('Confirm dedicated scope and paused external reconciliation with --ack-dedicated-lab.')

    def raw(self, args, prefix=None):
        result = subprocess.run((prefix or self.prefix) + args, text=True, capture_output=True)
        if result.returncode:
            # Do not echo server responses, logs, or possible auth-plugin output.
            raise Stop(f'oc operation failed ({result.returncode}): {args[0]}. Inspect with your normal CLI.')
        return result.stdout

    def get(self, resource, name, ns=None):
        args = ['get', resource, name, '--ignore-not-found', '-o', 'json']
        if ns:
            args += ['-n', ns]
        result = self.raw(args).strip()
        return json.loads(result) if result else None

    def items(self, resource, ns=None):
        if '.' in resource and resource not in self.apis_if_loaded():
            return []
        args = ['get', resource, '-o', 'json'] + (['-n', ns] if ns else ['-A'])
        return json.loads(self.raw(args)).get('items', [])

    def apis_if_loaded(self):
        return getattr(self, 'apis', set())

    def guard(self):
        if self.get('clusterversion', 'version')['spec']['clusterID'] != self.cluster_id:
            raise Stop('Cluster identity changed. Stopping.')

    def delete(self, resource, name, ns=None):
        obj = self.get(resource, name, ns)
        if not obj:
            print(f'Already absent: {resource}/{name}')
            return
        print(f'{"Delete" if self.args.execute else "Would delete"}: {resource}/{name}' + (f' in {ns}' if ns else ''))
        if not self.args.execute:
            return
        self.guard()
        args = ['delete', resource, name, '--ignore-not-found', '--wait=true',
                '--cascade=foreground', f'--timeout={self.args.timeout}s']
        if ns:
            args += ['-n', ns]
        self.raw(args)
        if self.get(resource, name, ns):
            raise Stop(f'Deletion incomplete: {resource}/{name}. Do not strip finalizers.')

    def wait_empty(self, resource, ns=None):
        print(f'{"Waiting for" if self.args.execute else "Would wait for"}: no {resource}' + (f' in {ns}' if ns else ''))
        if not self.args.execute:
            return
        deadline = time.monotonic() + self.args.timeout
        while self.items(resource, ns):
            if time.monotonic() >= deadline:
                raise Stop(f'Resources remain: {resource}. Stop and troubleshoot; no forced cleanup.')
            time.sleep(3)

    def require_project_absent(self):
        if self.get('namespace', PROJECT):
            raise Stop('Complete the project stage first; the demo project still exists.')

    def check_argocd(self):
        for app in self.items('applications.argoproj.io'):
            dest = app.get('spec', {}).get('destination', {})
            if dest.get('namespace') in {PROJECT, TEST_PROJECT, 'nvidia-gpu-operator', 'openshift-nfd', 'redhat-ods-applications'}:
                raise Stop('An Argo CD Application targets lab scope. Resolve its ownership before reset.')
        # Apps targeting no namespace, other GitOps systems, or remote Argo controllers
        # cannot be exhaustively discovered. Explicit operator acknowledgement covers these.

    def project(self):
        self.check_argocd()
        binding = self.get('clusterrolebinding', BINDING)
        if binding and not owned_binding(binding):
            raise Stop('The model auth binding has unexpected subjects or role. Manual review required.')
        volumes = []
        for ns in (PROJECT, TEST_PROJECT):
            if not self.get('namespace', ns):
                continue
            print(f'WARNING: ALL content in {ns} will be deleted, including user additions and Secrets.')
            for pvc in self.items('persistentvolumeclaims', ns):
                pvname = pvc.get('spec', {}).get('volumeName')
                if pvname:
                    pv = self.get('persistentvolume', pvname)
                    policy = pv['spec'].get('persistentVolumeReclaimPolicy', 'unknown') if pv else 'unknown'
                    volumes.append((pvname, policy))
                    print(f'Volume: {pvc["metadata"]["name"]} -> {pvname}, reclaim={policy}')
            # Allow KServe to remove dependent resources while its controller is healthy.
            for obj in self.items(CRDS['isvc'], ns):
                self.delete(CRDS['isvc'], obj['metadata']['name'], ns)
            self.delete('namespace', ns)
        # KServe can leave this cluster-scoped binding after namespace deletion.
        self.delete('clusterrolebinding', BINDING)
        for pvname, policy in volumes:
            if self.args.execute and policy == 'Delete':
                deadline = time.monotonic() + self.args.timeout
                while self.get('persistentvolume', pvname):
                    if time.monotonic() >= deadline:
                        raise Stop(f'PV {pvname} remains. Inspect CSI/storage cleanup; do not force-delete.')
                    time.sleep(3)
            elif policy != 'Delete':
                print(f'MANUAL STORAGE CHECK: {pvname} may retain data. No PV is directly deleted by this script.')
        print('Project reset complete; verify storage backend and fresh project setup.' if self.args.execute else 'Planned scope: project content and model storage. Nothing removed.')

    def ai(self):
        self.require_project_absent()
        self.check_argocd()
        if self.items(CRDS['isvc']):
            raise Stop('InferenceServices still exist elsewhere. Shared AI removal is blocked.')
        clusters = self.items(CRDS['dsc'])
        if any(x['metadata']['name'] != 'default-dsc' for x in clusters):
            raise Stop('Unexpected DataScienceCluster found.')
        if not clusters:
            print('DataScienceCluster already absent. Pre-existing AI operator and infrastructure retained.')
            return
        dsc = clusters[0]
        components = dsc.get('spec', {}).get('components', {})
        if any(v.get('managementState') != 'Removed' for k, v in components.items() if k not in {'dashboard', 'kserve'}):
            raise Stop('Other AI components are enabled. This no longer matches the documented lab.')
        print(('Set' if self.args.execute else 'Would set') + ' dashboard and kserve managementState=Removed; wait for component CR cleanup; delete default-dsc.')
        if self.args.execute:
            self.guard()
            patch = {'spec': {'components': {k: {'managementState': 'Removed'} for k in ('dashboard', 'kserve')}}}
            self.raw(['patch', CRDS['dsc'], 'default-dsc', '--type=merge', '-p', json.dumps(patch)])
        for resource in ['kserves.components.platform.opendatahub.io', 'dashboards.components.platform.opendatahub.io']:
            self.wait_empty(resource)
        self.delete(CRDS['dsc'], 'default-dsc')
        print(('AI lab component removal complete.' if self.args.execute else 'Planned scope: AI lab components. Nothing removed.') + ' AI operator, DSCI, gateway and identity configuration retained.')

    def gpu(self):
        self.require_project_absent()
        self.check_argocd()
        if self.items(CRDS['dsc']):
            raise Stop('Complete the ai stage first; a DataScienceCluster still exists.')
        for pod in self.items('pods'):
            ns = pod['metadata']['namespace']
            if ns == 'nvidia-gpu-operator' or pod.get('status', {}).get('phase') in {'Succeeded', 'Failed'}:
                continue
            containers = pod.get('spec', {}).get('containers', []) + pod.get('spec', {}).get('initContainers', [])
            if any(any(k.startswith('nvidia.com/') and str(v) != '0' for k, v in c.get('resources', {}).get(part, {}).items()) for c in containers for part in ('requests', 'limits')):
                raise Stop(f'GPU workload remains in {ns}. GPU teardown blocked.')
        for resource, allowed in [(CRDS['cp'], {'gpu-cluster-policy'}), (CRDS['nfd'], {'nfd-instance'})]:
            for obj in self.items(resource):
                if obj['metadata']['name'] not in allowed or (resource == CRDS['nfd'] and obj['metadata'].get('namespace') != 'openshift-nfd'):
                    raise Stop(f'Unexpected {resource} instance. Manual review required.')
        if self.items('nvidiadrivers.nvidia.com'):
            raise Stop('Separate NvidiaDriver objects exist; not part of this lab.')
        operators = [('nvidia-gpu-operator', 'gpu-operator-certified'), ('openshift-nfd', 'nfd')]
        installed = []
        for ns, name in operators:
            if not self.get('namespace', ns):
                continue
            subs = self.items('subscriptions.operators.coreos.com', ns)
            if any(x['metadata']['name'] != name for x in subs):
                raise Stop(f'Unexpected subscription in {ns}.')
            csvs = [x['metadata']['name'] for x in self.items('clusterserviceversions.operators.coreos.com', ns) if not x['metadata'].get('labels', {}).get('olm.copiedFrom')]
            if any(not x.startswith(name + '.') for x in csvs):
                raise Stop(f'Unexpected installed operator in {ns}.')
            installed.append((ns, name, csvs))
        if CRDS['cp'] in self.apis:
            self.delete(CRDS['cp'], 'gpu-cluster-policy')
            self.wait_empty('daemonsets', 'nvidia-gpu-operator') if self.get('namespace', 'nvidia-gpu-operator') else None
        if CRDS['nfd'] in self.apis:
            self.delete(CRDS['nfd'], 'nfd-instance', 'openshift-nfd')
        for ns, name, csvs in installed:
            self.delete('subscriptions.operators.coreos.com', name, ns)
            for csv in csvs:
                self.delete('clusterserviceversions.operators.coreos.com', csv, ns)
            self.delete('namespace', ns)
        print(('Selected operator resources removed.' if self.args.execute else 'Planned scope: GPU/NFD operator resources. Nothing removed.') + ' CRDs, node labels and host residue require review; this is NOT a factory reset.')


def owned_binding(obj):
    return (obj.get('roleRef') == {'apiGroup': 'rbac.authorization.k8s.io', 'kind': 'ClusterRole', 'name': 'system:auth-delegator'}
            and obj.get('subjects') == [{'kind': 'ServiceAccount', 'name': 'model-server', 'namespace': PROJECT}])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=['project', 'ai', 'gpu'])
    parser.add_argument('--expected-cluster-id', required=True, help='Independently verified ClusterVersion spec.clusterID')
    parser.add_argument('--context', help='Existing authenticated oc context; never pass credentials')
    parser.add_argument('--execute', action='store_true', help='Delete the selected scope; omitted means read-only preview')
    parser.add_argument('--confirm', help='Required for execution: RESET-PROJECT, RESET-AI, or RESET-GPU')
    parser.add_argument('--ack-dedicated-lab', action='store_true', help='Acknowledge scope ownership, data loss and paused external reconciliation')
    parser.add_argument('--timeout', type=int, default=300, help='Seconds per deletion/checkpoint (30–1800)')
    args = parser.parse_args()
    if not 30 <= args.timeout <= 1800:
        parser.error('--timeout must be 30–1800')
    try:
        reset = Reset(args)
        getattr(reset, args.stage)()
        print('Selected stage finished.' if args.execute else 'Preview finished. Nothing changed.')
    except (Stop, KeyError, ValueError) as exc:
        print(f'STOP: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
