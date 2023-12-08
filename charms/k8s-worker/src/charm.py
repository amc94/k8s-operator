#!/usr/bin/env python3

# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

# Learn more at: https://juju.is/docs/sdk

"""K8s-worker Charm.

A machine charm which operates a Kubernetes worker.

This charm installs and operates a Kubernetes worker via the k8s snap. It exposes
relations to co-operate with other kubernetes components.
"""


import logging

import ops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


class K8sWorkerCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Construct.

        Args:
            args: Arguments passed to the CharmBase parent constructor.
        """
        super().__init__(*args)
        self.framework.observe(self.on.update_status, self._on_update_status)

    def _on_update_status(self, _event: ops.UpdateStatusEvent):
        """Handle update-status event.

        Args:
            _event: event triggering the handler.
        """
        self.unit.status = ops.ActiveStatus("Ready")


if __name__ == "__main__":  # pragma: nocover
    ops.main.main(K8sWorkerCharm)
