# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Tests for the upgrade module."""

import unittest
from unittest.mock import MagicMock

import ops
from inspector import ClusterInspector
from lightkube.models.core_v1 import Node
from lightkube.models.meta_v1 import ObjectMeta
from literals import UPGRADE_RELATION
from upgrade import K8sDependenciesModel, K8sUpgrade

from charms.data_platform_libs.v0.upgrade import ClusterNotReadyError


class TestK8sUpgrade(unittest.TestCase):
    """Tests for the K8sUpgrade class."""

    def setUp(self):
        """Set up common test fixtures."""
        self.charm = MagicMock()
        self.charm.is_worker = False
        self.node_manager = MagicMock(spec=ClusterInspector)
        self.upgrade = K8sUpgrade(
            self.charm,
            cluster_inspector=self.node_manager,
            relation_name="upgrade",
            substrate="vm",
            dependency_model=K8sDependenciesModel(
                **{
                    "k8s_charm": {
                        "dependencies": {"k8s-worker": ">50"},
                        "name": "k8s",
                        "upgrade_supported": ">90",
                        "version": "100",
                    },
                    "k8s_service": {
                        "dependencies": {"k8s-worker": "^1.30, < 1.32"},
                        "name": "k8s",
                        "upgrade_supported": "^1.30, < 1.32",
                        "version": "1.31.1",
                    },
                }
            ),
        )

    def test_pre_upgrade_check_worker_success(self):
        """Test pre_upgrade_check succeeds for worker nodes."""
        self.charm.is_worker = True
        self.node_manager.get_nodes.return_value = []
        self.node_manager.verify_pods_running.return_value = None

        self.upgrade.pre_upgrade_check()

        self.node_manager.get_nodes.assert_not_called()
        self.node_manager.verify_pods_running.assert_not_called()

    def test_pre_upgrade_check_control_plane_success(self):
        """Test pre_upgrade_check succeeds for control plane nodes."""
        self.charm.is_worker = False
        self.node_manager.get_nodes.return_value = []
        self.node_manager.verify_pods_running.return_value = None

        self.upgrade.pre_upgrade_check()

        self.node_manager.get_nodes.assert_called_once_with()

    def test_pre_upgrade_check_unready_nodes(self):
        """Test pre_upgrade_check fails when nodes are not ready."""
        self.node_manager.get_nodes.return_value = [
            Node(metadata=ObjectMeta(name="k8s-1")),
            Node(metadata=ObjectMeta(name="k8s-2")),
            Node(metadata=ObjectMeta(name="k8s-3")),
        ]

        with self.assertRaises(ClusterNotReadyError):
            self.upgrade.pre_upgrade_check()

    def test_pre_upgrade_check_cluster_inspector_error(self):
        """Test pre_upgrade_check handles ClusterInspectorError."""
        self.node_manager.get_nodes.side_effect = ClusterInspector.ClusterInspectorError(
            "test error"
        )

        with self.assertRaises(ClusterNotReadyError):
            self.upgrade.pre_upgrade_check()

    def test_pre_upgrade_check_pods_not_ready(self):
        """Test pre_upgrade_check fails when pods are not ready."""
        self.node_manager.get_nodes.return_value = None
        self.node_manager.verify_pods_running.return_value = "kube-system/pod-1"

        with self.assertRaises(ClusterNotReadyError):
            self.upgrade.pre_upgrade_check()

    def test_build_upgrade_stack_no_relation(self):
        """Test build_upgrade_stack when no cluster relation exists."""
        self.charm.unit.name = "k8s/0"
        self.charm.model.get_relation.return_value = None

        result = self.upgrade.build_upgrade_stack()

        self.assertEqual(result, [0])
        self.charm.model.get_relation.assert_called_once_with(UPGRADE_RELATION)

    def test_build_upgrade_stack_with_relation(self):
        """Test build_upgrade_stack with cluster relation."""
        self.charm.unit.name = "k8s/0"
        relation = MagicMock()
        unit_1 = MagicMock()
        unit_1.name = "k8s/1"
        unit_2 = MagicMock()
        unit_2.name = "k8s/2"
        relation.units = {unit_1, unit_2}
        self.charm.model.get_relation.return_value = relation

        result = self.upgrade.build_upgrade_stack()

        self.assertEqual(sorted(result), [0, 1, 2])
        self.charm.model.get_relation.assert_called_once_with(UPGRADE_RELATION)

    def test_verify_worker_versions_compatible(self):
        """Test _verify_worker_versions returns True when worker versions is compatible."""
        unit_1 = MagicMock(spec=ops.Unit)
        unit_1.name = "k8s-worker/0"
        unit_2 = MagicMock(spec=ops.Unit)
        unit_2.name = "k8s-worker/1"
        self.charm.get_worker_versions.return_value = {"1.31.0": [unit_1], "1.31.5": [unit_2]}

        result = self.upgrade._verify_worker_versions()

        self.assertTrue(result)

    def test_verify_worker_versions_incompatible(self):
        """Test _verify_worker_versions returns False when worker versions is incompatible."""
        unit_1 = MagicMock(spec=ops.Unit)
        unit_1.name = "k8s-worker/0"
        unit_2 = MagicMock(spec=ops.Unit)
        unit_2.name = "k8s-worker/1"
        self.charm.get_worker_versions.return_value = {"1.32.0": [unit_1], "1.33.0": [unit_2]}

        result = self.upgrade._verify_worker_versions()

        self.assertFalse(result)
