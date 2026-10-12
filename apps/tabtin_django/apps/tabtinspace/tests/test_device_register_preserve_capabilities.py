"""WS 鉴权自动注册不得用会话能力覆盖真实设备能力。

背景（2026-10-12 协作链路深度审查发现）：Electron 客户端 WS 鉴权握手时，
``_ensure_electron_device_registered`` 曾把 WS 会话订阅能力
（agent.stream / session.collaboration / notifications 等 13 个）作为
capabilities 传给 ``register_device``，而 ``register_device`` 的
update_or_create 会无条件覆盖已有设备的 capabilities —— 客户端 HTTP
注册写入的真实设备能力（terminal_execute / browser / file / git 等）
每次 WS 重连都会被会话能力覆盖，污染 Device.capabilities，并使
Agent 执行快照（execution_context.device_capabilities）携带错误能力。
"""

from __future__ import annotations

import uuid

from django.test import TestCase

from apps.tabtinspace.models import Device
from apps.tabtinspace.tests.fixtures import create_test_organization, create_test_user
from apps.tabtinspace.services.device_service import DeviceService

REAL_DEVICE_CAPABILITIES = [
    "terminal_execute",
    "terminal_read",
    "terminal_write",
    "browser",
    "file",
    "gui",
    "mcp",
    "git",
    "code_search",
]
SESSION_CAPABILITIES = [
    "agent.action",
    "agent.stream",
    "asr.stream",
    "billing.events",
    "context.sync",
    "doc.events",
    "docparse.events",
    "extension.events",
    "notifications",
    "session.collaboration",
    "table.events",
    "tracker.events",
]


class RegisterDevicePreserveCapabilitiesTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.user = create_test_user(prefix="preserve_caps")
        self.organization = create_test_organization(
            owner=self.user,
            prefix="preserve_caps",
        )
        self.fingerprint = f"electron-preserve-{uuid.uuid4().hex[:8]}"
        # 模拟 Electron HTTP 注册：写入真实设备能力。
        Device.objects.create(
            organization=self.organization,
            user=self.user,
            name="Desktop",
            device_type="electron",
            role="control",
            fingerprint=self.fingerprint,
            status="offline",
            capabilities=REAL_DEVICE_CAPABILITIES,
        )

    def _register(self, **overrides):
        kwargs = {
            "organization_id": self.organization.id,
            "fingerprint": self.fingerprint,
            "device_type": "electron",
            "name": "Desktop",
            "os_info": {"os": "win32"},
        }
        kwargs.update(overrides)
        return DeviceService(user=self.user).register_device(**kwargs)

    def test_preserve_capabilities_keeps_real_device_caps_on_reconnect(self):
        """WS 自动注册（preserve_capabilities=True）不得覆盖真实设备能力。"""
        device = self._register(
            capabilities=None,
            preserve_capabilities=True,
        )

        self.assertIsNotNone(device)
        device.refresh_from_db()
        self.assertEqual(
            sorted(device.capabilities or []),
            sorted(REAL_DEVICE_CAPABILITIES),
        )

    def test_default_register_still_overwrites_capabilities(self):
        """HTTP 注册（默认行为）仍以显式传入的能力为准。"""
        device = self._register(
            capabilities=["terminal_execute", "browser"],
        )

        self.assertIsNotNone(device)
        device.refresh_from_db()
        self.assertEqual(
            sorted(device.capabilities or []),
            ["browser", "terminal_execute"],
        )

    def test_preserve_capabilities_new_device_writes_passed_capabilities(self):
        """preserve 模式下新建设备仍写入传入值（None → 空列表）。"""
        new_fp = f"electron-preserve-new-{uuid.uuid4().hex[:8]}"
        device = DeviceService(user=self.user).register_device(
            organization_id=self.organization.id,
            fingerprint=new_fp,
            device_type="electron",
            name="Fresh Desktop",
            os_info={},
            capabilities=None,
            preserve_capabilities=True,
        )

        self.assertIsNotNone(device)
        device.refresh_from_db()
        self.assertEqual(device.capabilities or [], [])

    def test_session_capabilities_do_not_leak_into_device_row(self):
        """端到端：即使误传会话能力 + preserve，真实能力也原样保留。"""
        device = self._register(
            capabilities=SESSION_CAPABILITIES,
            preserve_capabilities=True,
        )

        self.assertIsNotNone(device)
        device.refresh_from_db()
        leaked = set(SESSION_CAPABILITIES) & set(device.capabilities or [])
        self.assertEqual(leaked, set())
        self.assertEqual(
            sorted(device.capabilities or []),
            sorted(REAL_DEVICE_CAPABILITIES),
        )
