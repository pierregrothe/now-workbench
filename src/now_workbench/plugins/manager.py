"""Plugin and module manager for ServiceNow instances."""

from typing import TYPE_CHECKING

import httpx

from now_workbench.db.models import InstanceRecord
from now_workbench.plugins.models import PluginEvaluationResult, PluginRecord

if TYPE_CHECKING:
    from now_workbench.db.repository import DatabaseRepository

KNOWN_PLUGIN_NAMES: dict[str, str] = {
    "com.glide.now.assist": "Now Assist Platform Core",
    "com.snc.itsm": "IT Service Management Core",
    "com.snc.csm": "Customer Service Management",
    "com.glide.polaris": "Polaris Next Experience Theme",
    "com.snc.generative_ai": "Generative AI Controller",
    "com.snc.virtual_agent": "Virtual Agent Conversation Engine",
    "com.snc.fluent_sdk": "Declarative Fluent SDK Runtime",
}


class PluginManager:
    """Evaluates and installs ServiceNow plugins/modules on target instances."""

    def __init__(
        self,
        repo: DatabaseRepository,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.repo = repo
        self._transport = transport

    def _query_plugin_active(self, instance: InstanceRecord, plugin_id: str) -> tuple[bool, str]:
        """Ask the instance whether a plugin is active (never claims on failure)."""
        url = f"{instance.url.rstrip('/')}/api/now/table/v_plugin"
        params = {"sysparm_query": f"id={plugin_id}", "sysparm_fields": "id,name,active"}
        auth = (instance.username, instance.password) if instance.auth_type == "basic" else None
        try:
            with httpx.Client(transport=self._transport, timeout=10.0) as client:
                res = client.get(
                    url, params=params, auth=auth, headers={"Accept": "application/json"}
                )
            if res.status_code != 200:
                return False, f"HTTP {res.status_code} from the instance"
            rows = res.json().get("result", [])
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            return False, f"could not query the instance: {exc}"
        active = any(str(r.get("active", "")).lower() == "true" for r in rows)
        return active, "" if active else "plugin not found or not active"

    def evaluate_plugins(
        self,
        instance: InstanceRecord,
        required_plugins: list[str],
        fake_mode: bool = False,
    ) -> PluginEvaluationResult:
        """Evaluate which required plugins are already installed versus missing."""
        recorded = {p.plugin_id for p in self.repo.list_instance_plugins(instance.id)}

        installed: list[str] = []
        missing: list[str] = []
        for pid in required_plugins:
            clean_id = pid.strip()
            if not clean_id:
                continue
            if clean_id in recorded:
                installed.append(clean_id)
            else:
                missing.append(clean_id)

        return PluginEvaluationResult(
            instance_id=instance.id,
            required=required_plugins,
            installed=installed,
            missing=missing,
            all_satisfied=len(missing) == 0,
        )

    def install_plugin(
        self,
        instance: InstanceRecord,
        plugin_id: str,
        plugin_name: str | None = None,
        fake_mode: bool = False,
    ) -> tuple[bool, str]:
        """Install or activate a required plugin/module on the target instance."""
        clean_id = plugin_id.strip()
        name = plugin_name or KNOWN_PLUGIN_NAMES.get(clean_id, f"Plugin {clean_id}")

        simulated = fake_mode or instance.url.startswith("fake://")
        if not simulated:
            active, reason = self._query_plugin_active(instance, clean_id)
            if not active:
                return (
                    False,
                    f"Plugin '{clean_id}' ({name}) is not active on {instance.name} ({reason}); "
                    "activate it on the instance, then retry.",
                )
        self.repo.add_instance_plugin(
            instance_id=instance.id,
            plugin_id=clean_id,
            plugin_name=name,
            status="active",
        )
        if simulated:
            return (
                True,
                f"Plugin '{clean_id}' ({name}) activation simulated on {instance.name}; "
                "nothing was changed on the instance.",
            )
        return True, f"Plugin '{clean_id}' ({name}) already active on {instance.name}."

    def install_required_plugins(
        self,
        instance: InstanceRecord,
        required_plugins: list[str],
        fake_mode: bool = False,
    ) -> tuple[list[PluginRecord], list[str]]:
        """Activate all missing plugins required by a demonstration recipe."""
        installed_records: list[PluginRecord] = []
        messages: list[str] = []

        eval_res = self.evaluate_plugins(instance, required_plugins, fake_mode=fake_mode)
        for pid in eval_res.missing:
            name = KNOWN_PLUGIN_NAMES.get(pid, f"Plugin {pid}")
            ok, msg = self.install_plugin(instance, pid, plugin_name=name, fake_mode=fake_mode)
            messages.append(msg)
            if ok:
                installed_records.append(
                    PluginRecord(
                        instance_id=instance.id,
                        plugin_id=pid,
                        plugin_name=name,
                        status="active",
                    )
                )

        return installed_records, messages
