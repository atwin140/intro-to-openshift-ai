#!/usr/bin/env python3
"""Safety regression tests using a fake oc backend; never connects to a cluster."""
import argparse
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reset_lab', Path(__file__).resolve().parents[1] / 'scripts/reset-lab.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def args(**changes):
    result = dict(stage='project', expected_cluster_id='test-cluster', context='test', execute=False,
                  confirm=None, ack_dedicated_lab=False, timeout=30)
    result.update(changes)
    return argparse.Namespace(**result)


class FakeReset(m.Reset):
    def __init__(self, options, objects=None, lists=None):
        self.objects = objects or {}
        self.lists = lists or {}
        self.mutations = []
        super().__init__(options)

    def raw(self, command, prefix=None):
        if command == ['whoami', '--show-server']:
            return 'https://test.invalid:6443'
        if command[:2] == ['auth', 'can-i']:
            return 'yes'
        if command[0] in {'delete', 'patch'}:
            self.mutations.append(command)
            if command[0] == 'delete':
                ns = command[command.index('-n') + 1] if '-n' in command else None
                self.objects.pop((command[1], command[2], ns), None)
            return ''
        raise AssertionError(f'Unexpected command: {command}')

    def get(self, resource, name, ns=None):
        if resource == 'clusterversion':
            return {'spec': {'clusterID': 'test-cluster'}}
        return self.objects.get((resource, name, ns))

    def items(self, resource, ns=None):
        return self.lists.get((resource, ns), [])


def namespace():
    return {('namespace', m.PROJECT, None): {'metadata': {'name': m.PROJECT}}}


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)

    def test_preview_has_no_mutations(self):
        reset = FakeReset(args(), namespace())
        reset.project()
        self.assertEqual(reset.mutations, [])

    def test_confirmation_without_execute_rejected(self):
        with self.assertRaisesRegex(m.Stop, 'without --execute'):
            FakeReset(args(stage='gpu', confirm='RESET-GPU', ack_dedicated_lab=True))

    def test_acknowledgement_without_execute_rejected(self):
        with self.assertRaisesRegex(m.Stop, 'without --execute'):
            FakeReset(args(ack_dedicated_lab=True))

    def test_preview_describes_planned_actions(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            reset = FakeReset(args(), namespace())
            reset.project()
        self.assertIn('Would delete: namespace/', output.getvalue())
        self.assertIn('Nothing removed.', output.getvalue())
        self.assertNotIn('Project reset complete', output.getvalue())
        self.assertEqual(reset.mutations, [])

    def test_wrong_cluster_rejected(self):
        with self.assertRaisesRegex(m.Stop, 'mismatch'):
            FakeReset(args(expected_cluster_id='other'))

    def test_execution_requires_stage_confirmation(self):
        with self.assertRaisesRegex(m.Stop, 'confirmation'):
            FakeReset(args(execute=True))

    def test_execution_requires_ownership_acknowledgement(self):
        with self.assertRaisesRegex(m.Stop, 'dedicated'):
            FakeReset(args(execute=True, confirm='RESET-PROJECT'))

    def test_project_execution_is_scoped(self):
        reset = FakeReset(args(execute=True, confirm='RESET-PROJECT', ack_dedicated_lab=True), namespace())
        reset.project()
        self.assertEqual(len(reset.mutations), 1)
        self.assertEqual(reset.mutations[0][:3], ['delete', 'namespace', m.PROJECT])

    def test_ai_requires_project_reset(self):
        reset = FakeReset(args(stage='ai'), namespace())
        with self.assertRaisesRegex(m.Stop, 'project stage'):
            reset.ai()
        self.assertEqual(reset.mutations, [])

    def test_foreign_binding_rejected(self):
        objects = namespace()
        objects[('clusterrolebinding', m.BINDING, None)] = {'subjects': [{'name': 'someone-else'}]}
        reset = FakeReset(args(), objects)
        with self.assertRaisesRegex(m.Stop, 'unexpected subjects'):
            reset.project()

    def test_argocd_owner_blocks(self):
        reset = FakeReset(args(), namespace(), {('applications.argoproj.io', None): [{'spec': {'destination': {'namespace': m.PROJECT}}}]})
        with self.assertRaisesRegex(m.Stop, 'Argo CD'):
            reset.project()

    def test_other_models_block_ai(self):
        reset = FakeReset(args(stage='ai'), lists={(m.CRDS['isvc'], None): [{'metadata': {'name': 'other'}}]})
        with self.assertRaisesRegex(m.Stop, 'elsewhere'):
            reset.ai()

    def test_other_gpu_workload_blocks_gpu(self):
        pod = {'metadata': {'namespace': 'other'}, 'spec': {'containers': [{'resources': {'limits': {'nvidia.com/gpu': 1}}}]}}
        reset = FakeReset(args(stage='gpu'), lists={('pods', None): [pod]})
        with self.assertRaisesRegex(m.Stop, 'GPU workload'):
            reset.gpu()

    def test_other_ai_component_blocks(self):
        dsc = {'metadata': {'name': 'default-dsc'}, 'spec': {'components': {'workbenches': {'managementState': 'Managed'}}}}
        reset = FakeReset(args(stage='ai'), lists={(m.CRDS['dsc'], None): [dsc]})
        with self.assertRaisesRegex(m.Stop, 'Other AI components'):
            reset.ai()

    def test_ai_patch_precedes_dsc_delete(self):
        dsc = {'metadata': {'name': 'default-dsc'}, 'spec': {'components': {'dashboard': {'managementState': 'Managed'}, 'kserve': {'managementState': 'Managed'}}}}
        reset = FakeReset(args(stage='ai', execute=True, confirm='RESET-AI', ack_dedicated_lab=True),
                          {(m.CRDS['dsc'], 'default-dsc', None): dsc}, {(m.CRDS['dsc'], None): [dsc]})
        reset.ai()
        self.assertEqual([c[0] for c in reset.mutations], ['patch', 'delete'])
        self.assertEqual(reset.mutations[-1][1:3], [m.CRDS['dsc'], 'default-dsc'])

    def test_failed_delete_stops_before_next_resource(self):
        class FailedReset(FakeReset):
            def raw(self, command, prefix=None):
                if command[0] == 'delete':
                    self.mutations.append(command)
                    raise m.Stop('simulated API failure')
                return super().raw(command, prefix)
        objects = namespace()
        objects[(m.CRDS['isvc'], 'command-helper', m.PROJECT)] = {'metadata': {'name': 'command-helper'}}
        reset = FailedReset(args(execute=True, confirm='RESET-PROJECT', ack_dedicated_lab=True), objects,
                            {(m.CRDS['isvc'], m.PROJECT): [{'metadata': {'name': 'command-helper'}}]})
        with self.assertRaisesRegex(m.Stop, 'simulated API failure'):
            reset.project()
        self.assertEqual(len(reset.mutations), 1)
        self.assertIn(('namespace', m.PROJECT, None), reset.objects)

    def test_unexpected_gpu_operator_blocks(self):
        reset = FakeReset(args(stage='gpu'),
                          {('namespace', 'nvidia-gpu-operator', None): {'metadata': {'name': 'nvidia-gpu-operator'}}},
                          {('subscriptions.operators.coreos.com', 'nvidia-gpu-operator'): [{'metadata': {'name': 'other'}}]})
        with self.assertRaisesRegex(m.Stop, 'Unexpected subscription'):
            reset.gpu()
        self.assertEqual(reset.mutations, [])

    def test_idempotent_project_reset(self):
        reset = FakeReset(args(execute=True, confirm='RESET-PROJECT', ack_dedicated_lab=True))
        reset.project()
        self.assertEqual(reset.mutations, [])


if __name__ == '__main__':
    unittest.main()
