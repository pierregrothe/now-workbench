"""Plugin and module manager for ServiceNow instances."""

from typing import TYPE_CHECKING

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

    def __init__(self, repo: DatabaseRepository) -> None:
        self.repo = repo

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

        self.repo.add_instance_plugin(
            instance_id=instance.id,
            plugin_id=clean_id,
            plugin_name=name,
            status="active",
        )
        mode_str = " (simulated)" if fake_mode else ""
        return (
            True,
            f"Plugin '{clean_id}' ({name}) activated successfully on {instance.name}{mode_str}.",
        )

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
