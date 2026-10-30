"""Tests for workbench Typer CLI commands."""

import uuid
from pathlib import Path

from typer.testing import CliRunner

from now_workbench.cli import app
from now_workbench.db import DatabaseRepository, init_db
from now_workbench.db.models import InstanceCreate, SeedOperationRecord, SeedRecordItem
from now_workbench.properties import PropertyEngine, PropertySnapshot

runner = CliRunner(env={"COLUMNS": "250", "REMEDIATION_TIMEOUT": "1"})


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "now-workbench version" in result.stdout


def test_cli_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Health Check" in result.stdout
    assert "Node.js" in result.stdout


def test_cli_doctor_fix() -> None:
    result = runner.invoke(app, ["doctor", "--fix", "--mode", "user"])
    assert result.exit_code == 0
    assert "Health Check" in result.stdout


def test_cli_demo_commands(tmp_path: Path) -> None:
    # 1. demo list
    res_list = runner.invoke(app, ["demo", "list"])
    assert res_list.exit_code == 0
    assert "sample-ai-assistant" in res_list.stdout

    # 2. demo inspect valid
    res_inspect = runner.invoke(app, ["demo", "inspect", "sample-ai-assistant"])
    assert res_inspect.exit_code == 0
    assert "sample-ai-assistant" in res_inspect.stdout

    # 3. demo inspect invalid
    res_inspect_bad = runner.invoke(app, ["demo", "inspect", "non-existent-bundle"])
    assert res_inspect_bad.exit_code == 1
    assert "not found" in res_inspect_bad.stdout

    # 4. demo export
    out_zip = tmp_path / "export_test.zip"
    res_export = runner.invoke(
        app, ["demo", "export", "sample-ai-assistant", "--output", str(out_zip)]
    )
    assert res_export.exit_code == 0
    assert out_zip.exists()

    # 5. demo export invalid
    res_export_bad = runner.invoke(app, ["demo", "export", "non-existent-bundle"])
    assert res_export_bad.exit_code == 1

    # 6. demo seed in fake mode
    res_seed = runner.invoke(app, ["demo", "seed", "sample-ai-assistant", "--fake"])
    assert res_seed.exit_code == 0
    assert "Created" in res_seed.stdout

    # 7. demo seed invalid bundle
    res_seed_bad = runner.invoke(app, ["demo", "seed", "non-existent-bundle", "--fake"])
    assert res_seed_bad.exit_code == 1

    # 8. demo seed-history
    res_hist = runner.invoke(app, ["demo", "seed-history"])
    assert res_hist.exit_code == 0
    assert "Audit History" in res_hist.stdout

    # 9. demo rollback invalid op
    res_rb_bad = runner.invoke(app, ["demo", "rollback", "op-does-not-exist", "--fake"])
    assert res_rb_bad.exit_code == 1


def test_cli_instance_commands() -> None:
    # 1. instance list
    res_list = runner.invoke(app, ["instance", "list"])
    assert res_list.exit_code == 0
    assert "Registered ServiceNow Instances" in res_list.stdout

    # 2. instance list --check
    res_check = runner.invoke(app, ["instance", "list", "--check"])
    assert res_check.exit_code == 0

    # 3. instance add
    res_add = runner.invoke(
        app,
        [
            "instance",
            "add",
            "CLI Added Instance",
            "fake://clitest.service-now.com",
            "--id",
            "cli-fake-inst",
            "--username",
            "cliuser",
            "--password",
            "clipassword",
            "--release",
            "Zurich",
            "--default",
        ],
    )
    assert res_add.exit_code == 0
    assert "Registered" in res_add.stdout

    # 4. instance activate valid
    res_act = runner.invoke(app, ["instance", "activate", "cli-fake-inst"])
    assert res_act.exit_code == 0
    assert "ACTIVE" in res_act.stdout

    # 5. instance activate invalid
    res_act_bad = runner.invoke(app, ["instance", "activate", "non-existent-id"])
    assert res_act_bad.exit_code == 1

    # 6. instance test specific valid
    res_test_spec = runner.invoke(app, ["instance", "test", "cli-fake-inst"])
    assert res_test_spec.exit_code == 0
    assert "Testing ServiceNow Instance Authentication" in res_test_spec.stdout
    assert "Authenticated" in res_test_spec.stdout

    # 7. instance test invalid
    res_test_bad = runner.invoke(app, ["instance", "test", "non-existent-id"])
    assert res_test_bad.exit_code == 1

    # 8. instance rename valid
    res_rename = runner.invoke(app, ["instance", "rename", "cli-fake-inst", "CLI Renamed Instance"])
    assert res_rename.exit_code == 0
    assert "CLI Renamed Instance" in res_rename.stdout

    # 9. instance rename invalid
    res_rename_bad = runner.invoke(app, ["instance", "rename", "missing-id", "New Name"])
    assert res_rename_bad.exit_code == 1

    # 10. instance delete valid
    res_del = runner.invoke(app, ["instance", "delete", "cli-fake-inst"])
    assert res_del.exit_code == 0
    assert "deleted" in res_del.stdout

    # 11. instance delete invalid
    res_del_bad = runner.invoke(app, ["instance", "delete", "missing-id"])
    assert res_del_bad.exit_code == 1


def test_cli_template_commands(tmp_path: Path) -> None:
    # 1. template list
    res_list = runner.invoke(app, ["template", "list"])
    assert res_list.exit_code == 0
    assert "Customization Templates" in res_list.stdout

    # 2. template inspect valid
    res_inspect = runner.invoke(app, ["template", "inspect", "agentic-router-template"])
    assert res_inspect.exit_code == 0
    assert "agentic-router-template" in res_inspect.stdout

    # 3. template inspect invalid
    res_inspect_bad = runner.invoke(app, ["template", "inspect", "non-existent-tmpl"])
    assert res_inspect_bad.exit_code == 1

    # 4. template generate valid
    res_gen = runner.invoke(
        app,
        [
            "template",
            "generate",
            "agentic-router-template",
            "cli-generated-bundle",
            "Acme Industries",
            "--primary-color",
            "#10b981",
            "--secondary-color",
            "#3b82f6",
            "--group",
            "Enterprise Desk",
        ],
    )
    assert res_gen.exit_code == 0
    assert "Generated tailored bundle" in res_gen.stdout

    # Clean up generated bundle directory
    generated_path = Path("bundles/cli-generated-bundle")
    if generated_path.exists():
        import shutil

        shutil.rmtree(generated_path)

    # 5. template generate invalid template
    res_gen_bad = runner.invoke(
        app,
        [
            "template",
            "generate",
            "non-existent-tmpl",
            "target-id",
            "Customer X",
        ],
    )
    assert res_gen_bad.exit_code == 1

    # 6. template generate failure during instantiation (e.g. missing base bundle)
    empty_gen_bundles = tmp_path / "empty_gen_bundles"
    empty_gen_bundles.mkdir(parents=True, exist_ok=True)
    res_gen_fail = runner.invoke(
        app,
        [
            "template",
            "generate",
            "agentic-router-template",
            "bad-bundle-dest",
            "Acme",
        ],
        env={"WORKBENCH_BUNDLES_DIR": str(empty_gen_bundles)},
    )
    assert res_gen_fail.exit_code == 1
    assert "failed" in res_gen_fail.stdout


def test_cli_serve_help() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "Start the FastAPI backend server" in result.stdout


def test_cli_serve_execution() -> None:
    """Verify serve command executes uvicorn runner and prints server panel."""
    # Port -1 causes uvicorn to startup, fail socket bind, and shutdown cleanly
    result = runner.invoke(app, ["serve", "--port", "-1"])
    assert result.exit_code == 3
    assert "Starting now-workbench server" in result.stdout


def test_cli_main_entrypoint() -> None:
    """Verify running the cli module as __main__."""
    import runpy
    import sys

    old_argv = sys.argv
    sys.argv = ["workbench", "--help"]
    try:
        runpy.run_path("src/now_workbench/cli.py", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
    finally:
        sys.argv = old_argv


def test_cli_empty_states_and_branches(tmp_path: Path) -> None:
    """Verify empty database and directory states for demo, instance, and template commands."""
    empty_db = tmp_path / "empty_registry.db"
    env_empty = {"WORKBENCH_DB_PATH": str(empty_db)}

    # 1. demo seed-history with empty database
    res_hist = runner.invoke(app, ["demo", "seed-history"], env=env_empty)
    assert res_hist.exit_code == 0
    assert "No seed operations recorded" in res_hist.stdout

    # 2. demo list with empty bundles dir
    empty_bundles = tmp_path / "empty_bundles"
    empty_bundles.mkdir()
    res_demos = runner.invoke(
        app,
        ["demo", "list"],
        env={"WORKBENCH_BUNDLES_DIR": str(empty_bundles)},
    )
    assert res_demos.exit_code == 0
    assert "No demonstration bundles found" in res_demos.stdout

    # 3. instance list with empty database
    res_inst = runner.invoke(app, ["instance", "list"], env=env_empty)
    assert res_inst.exit_code == 0
    assert "No instances registered" in res_inst.stdout

    # 4. instance test with empty database
    res_test_empty = runner.invoke(app, ["instance", "test"], env=env_empty)
    assert res_test_empty.exit_code == 1
    assert "No instance found to test" in res_test_empty.stdout

    # 5. template list with empty database
    res_tmpl = runner.invoke(app, ["template", "list"], env=env_empty)
    assert res_tmpl.exit_code == 0
    assert "No customization templates registered" in res_tmpl.stdout

    # 6. doctor with empty database and configured API key
    res_doc = runner.invoke(
        app,
        ["doctor"],
        env={
            "WORKBENCH_DB_PATH": str(empty_db),
            "WORKBENCH_ANTHROPIC_API_KEY": "sk-ant-test-key",
        },
    )
    assert res_doc.exit_code == 0
    assert "0 registered" in res_doc.stdout
    assert "Connected" in res_doc.stdout

    # 7. doctor --fix when directories are missing
    res_fix = runner.invoke(
        app,
        ["doctor", "--fix", "--mode", "user"],
        env={
            "WORKBENCH_DATA_DIR": str(tmp_path / "new_data"),
            "WORKBENCH_BUNDLES_DIR": str(tmp_path / "new_bundles"),
        },
    )
    assert res_fix.exit_code == 0
    assert "Created directory" in res_fix.stdout


def test_cli_seed_and_rollback_flow() -> None:
    """Verify demo seed failure and successful rollback with CLI output."""
    # 1. Seed failure when instance cannot be resolved
    res_seed_fail = runner.invoke(
        app,
        ["demo", "seed", "sample-ai-assistant", "--instance", "non-existent-inst-404", "--fake"],
    )
    assert res_seed_fail.exit_code == 1
    assert "Seed operation failed" in res_seed_fail.stdout

    # 2. Successful seed
    res_seed = runner.invoke(app, ["demo", "seed", "sample-ai-assistant", "--fake"])
    assert res_seed.exit_code == 0
    assert "Created" in res_seed.stdout

    # Extract operation ID from database
    from now_workbench.db import DatabaseRepository, init_db

    conn = init_db()
    ops = DatabaseRepository(conn).list_seed_operations()
    assert len(ops) > 0
    latest_op_id = ops[0].id
    conn.close()

    # 3. Rollback success
    res_rb = runner.invoke(app, ["demo", "rollback", latest_op_id, "--fake"])
    assert res_rb.exit_code == 0
    assert "Deleted" in res_rb.stdout

    # 4. Rollback reporting errors (non-fake mode with immediate connection refused)
    import uuid

    from now_workbench.db.models import InstanceCreate, SeedOperationRecord, SeedRecordItem

    err_op_id = f"op-refused-{uuid.uuid4().hex[:8]}"
    err_inst_id = f"inst-refused-{uuid.uuid4().hex[:8]}"

    conn_err = init_db()
    repo_err = DatabaseRepository(conn_err)
    repo_err.add_instance(
        InstanceCreate(
            id=err_inst_id,
            name="Refused Inst",
            url="http://127.0.0.1:1",
            is_default=False,
        )
    )
    err_op = SeedOperationRecord(
        id=err_op_id,
        bundle_id="sample-ai-assistant",
        instance_id=err_inst_id,
        created_records=[SeedRecordItem(table="incident", sys_id="rec-123")],
    )
    repo_err.record_seed_operation(err_op)
    conn_err.close()

    res_rb_err = runner.invoke(app, ["demo", "rollback", err_op_id])
    assert res_rb_err.exit_code == 0
    assert "Deleted 0 seed records" in res_rb_err.stdout


def test_cli_instance_test_all_targets() -> None:
    """Verify testing all registered instances including auth failure and unreachable."""
    # Register test instances with deterministic fake URLs
    runner.invoke(
        app,
        [
            "instance",
            "add",
            "Auth Fail Inst",
            "fake://auth-failed.service-now.com",
            "--id",
            "inst-auth-fail",
        ],
    )
    runner.invoke(
        app,
        [
            "instance",
            "add",
            "Unreach Inst",
            "fake://unreachable.service-now.com",
            "--id",
            "inst-unreach",
        ],
    )

    # Test all registered instances (no ID argument)
    res_test_all = runner.invoke(app, ["instance", "test"])
    assert res_test_all.exit_code == 0
    assert "Auth Fail Inst" in res_test_all.stdout
    assert "Unreach Inst" in res_test_all.stdout


def test_cli_helpers_and_status_formatting() -> None:
    from now_workbench.cli import (
        _format_instance_status,
        _render_doctor_table,
        _render_remediation_summary,
    )
    from now_workbench.db.models import InstanceRecord
    from now_workbench.remediation import RemediationPlan

    # 1. Format status helper across all branches
    inst_auth = InstanceRecord(id="1", name="1", url="u", status="authenticated")
    assert "Authenticated" in _format_instance_status(inst_auth)

    inst_fail = InstanceRecord(id="2", name="2", url="u", status="auth_failed")
    assert "Auth Failed" in _format_instance_status(inst_fail)

    inst_unreach = InstanceRecord(id="3", name="3", url="u", status="unreachable")
    assert "Unreachable" in _format_instance_status(inst_unreach)

    inst_unknown = InstanceRecord(id="4", name="4", url="u", status="unknown")
    assert "Untested" in _format_instance_status(inst_unknown)

    inst_custom = InstanceRecord(id="5", name="5", url="u", status="syncing")
    assert "syncing" in _format_instance_status(inst_custom)

    # 2. Render doctor table with alternate probe flags
    _render_doctor_table(
        {
            "node_available": False,
            "node_path": "",
            "now_sdk_available": True,
            "now_sdk_path": "/bin/now-sdk",
        }
    )

    # 3. Render remediation summary when healthy
    _render_remediation_summary(
        RemediationPlan(
            needs_data_dir=False,
            needs_bundles_dir=False,
            needs_workspace_dir=False,
            needs_env_file=False,
        )
    )

    # 4. Render remediation summary when issues present
    _render_remediation_summary(
        RemediationPlan(
            needs_sdk_install=True,
            needs_data_dir=True,
            needs_bundles_dir=True,
            needs_workspace_dir=True,
            needs_env_file=True,
        )
    )


def test_cli_runbook_commands(tmp_path: Path) -> None:
    """Verify CLI demo runbook inspect and stage verification commands."""
    # 1. Valid runbook inspect
    res_rb = runner.invoke(app, ["demo", "runbook", "sample-ai-assistant"])
    assert res_rb.exit_code == 0
    assert "The Problem State" in res_rb.stdout
    assert "Beth Anglin" in res_rb.stdout
    assert "Talking Points" in res_rb.stdout

    # 2. Non-existent bundle runbook
    res_rb_bad = runner.invoke(app, ["demo", "runbook", "non-existent-bundle-99"])
    assert res_rb_bad.exit_code == 1
    assert "not found" in res_rb_bad.stdout

    # 3. Bundle without guide.md
    bundles_dir = tmp_path / "custom_bundles"
    no_guide = bundles_dir / "bundle-no-guide"
    no_guide.mkdir(parents=True)
    (no_guide / "manifest.json").write_text(
        '{"id":"bundle-no-guide","name":"No Guide","version":"1.0"}', encoding="utf-8"
    )
    res_no_guide = runner.invoke(
        app,
        ["demo", "runbook", "bundle-no-guide"],
        env={"WORKBENCH_BUNDLES_DIR": str(bundles_dir)},
    )
    assert res_no_guide.exit_code == 0
    assert "No walkthrough guide found" in res_no_guide.stdout

    # 4. Stage verification in fake mode
    res_v1 = runner.invoke(app, ["demo", "verify-stage", "sample-ai-assistant", "1", "--fake"])
    assert res_v1.exit_code == 0
    assert "Stage 1 verified" in res_v1.stdout

    # 5. Non-existent stage number
    res_v_bad_stage = runner.invoke(
        app, ["demo", "verify-stage", "sample-ai-assistant", "99", "--fake"]
    )
    assert res_v_bad_stage.exit_code == 1
    assert "Stage 99 not found" in res_v_bad_stage.stdout

    # 6. Non-existent bundle for verify-stage
    res_v_bad_bundle = runner.invoke(
        app, ["demo", "verify-stage", "non-existent-bundle", "1", "--fake"]
    )
    assert res_v_bad_bundle.exit_code == 1

    # 7. Non-existent instance target
    res_v_bad_inst = runner.invoke(
        app,
        [
            "demo",
            "verify-stage",
            "sample-ai-assistant",
            "1",
            "--instance",
            "inst-missing-99",
            "--fake",
        ],
    )
    assert res_v_bad_inst.exit_code == 1
    assert "Target instance not found" in res_v_bad_inst.stdout

    # 8. Bundle without walkthrough guide for verify-stage
    res_v_no_guide = runner.invoke(
        app,
        ["demo", "verify-stage", "bundle-no-guide", "1", "--fake"],
        env={"WORKBENCH_BUNDLES_DIR": str(bundles_dir)},
    )
    assert res_v_no_guide.exit_code == 1
    assert "No walkthrough guide found" in res_v_no_guide.stdout

    # 9. Failure on live instance with refused connection
    import uuid

    refused_id = f"refused-inst-{uuid.uuid4().hex[:8]}"
    conn = init_db()
    repo = DatabaseRepository(conn)
    repo.add_instance(
        InstanceCreate(
            id=refused_id,
            name="Refused Host",
            url="http://127.0.0.1:1",
            is_default=False,
        )
    )
    conn.close()

    res_fail = runner.invoke(
        app,
        ["demo", "verify-stage", "sample-ai-assistant", "2", "--instance", refused_id],
    )
    assert res_fail.exit_code == 1
    assert "FAIL" in res_fail.stdout


def test_cli_properties_and_reset_commands(tmp_path: Path) -> None:
    """Verify workbench demo properties inspect/apply/restore and demo reset CLI commands."""
    runner = CliRunner()
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()

    # 1. Valid bundle with sys_properties.json
    valid_bundle = bundles_dir / "valid-props-demo"
    props_dir = valid_bundle / "properties"
    props_dir.mkdir(parents=True)
    (props_dir / "sys_properties.json").write_text(
        '{"glide.ui.polaris.experience": "true", "x_demo.ai_score": "0.98"}',
        encoding="utf-8",
    )

    # 2. Bundle without properties
    no_props_bundle = bundles_dir / "no-props-demo"
    no_props_bundle.mkdir()

    env = {"WORKBENCH_BUNDLES_DIR": str(bundles_dir)}

    # Inspect valid bundle
    res_inspect = runner.invoke(app, ["demo", "properties", "inspect", "valid-props-demo"], env=env)
    assert res_inspect.exit_code == 0
    assert "glide.ui.polaris.experience" in res_inspect.stdout

    # Inspect bundle without properties
    res_no_props = runner.invoke(app, ["demo", "properties", "inspect", "no-props-demo"], env=env)
    assert res_no_props.exit_code == 0
    assert "No system properties configured" in res_no_props.stdout

    # Inspect missing bundle
    res_missing = runner.invoke(app, ["demo", "properties", "inspect", "missing-demo"], env=env)
    assert res_missing.exit_code == 1
    assert "not found" in res_missing.stdout

    # Apply properties in fake mode
    res_apply = runner.invoke(
        app, ["demo", "properties", "apply", "valid-props-demo", "--fake"], env=env
    )
    assert res_apply.exit_code == 0
    assert "Applied 2 properties" in res_apply.stdout

    # Apply properties with missing bundle
    res_apply_missing = runner.invoke(
        app, ["demo", "properties", "apply", "missing-demo", "--fake"], env=env
    )
    assert res_apply_missing.exit_code == 1

    # Apply properties with invalid instance
    res_apply_bad_inst = runner.invoke(
        app,
        ["demo", "properties", "apply", "valid-props-demo", "--instance", "bad-inst-99", "--fake"],
        env=env,
    )
    assert res_apply_bad_inst.exit_code == 1
    assert "Target instance not found" in res_apply_bad_inst.stdout

    # Restore properties in fake mode
    res_restore = runner.invoke(
        app, ["demo", "properties", "restore", "valid-props-demo", "--fake"], env=env
    )
    assert res_restore.exit_code == 0
    assert "Restored 2 properties" in res_restore.stdout

    # Restore properties with invalid instance
    res_restore_bad_inst = runner.invoke(
        app,
        [
            "demo",
            "properties",
            "restore",
            "valid-props-demo",
            "--instance",
            "bad-inst-99",
            "--fake",
        ],
        env=env,
    )
    assert res_restore_bad_inst.exit_code == 1

    # Inspect using default settings.bundles_dir (no WORKBENCH_BUNDLES_DIR env var)
    res_default_dir = runner.invoke(app, ["demo", "properties", "inspect", "sample-ai-assistant"])
    assert res_default_dir.exit_code == 0

    # Demo reset with active seed records to roll back
    db_conn = init_db()
    db_repo = DatabaseRepository(db_conn)
    default_inst = db_repo.get_default_instance()
    assert default_inst is not None
    unique_op_id = f"seed-op-test-{uuid.uuid4().hex[:8]}"
    db_repo.record_seed_operation(
        SeedOperationRecord(
            id=unique_op_id,
            bundle_id="valid-props-demo",
            instance_id=default_inst.id,
            status="completed",
            created_records=[SeedRecordItem(table="incident", sys_id="test-sys-123")],
        )
    )
    db_conn.close()

    # Demo reset in fake mode
    res_reset = runner.invoke(app, ["demo", "reset", "valid-props-demo", "--fake"], env=env)
    assert res_reset.exit_code == 0
    assert "Reset completed" in res_reset.stdout
    assert "Rolled back seed records: 1" in res_reset.stdout

    # Demo reset missing bundle
    res_reset_missing = runner.invoke(app, ["demo", "reset", "missing-demo", "--fake"], env=env)
    assert res_reset_missing.exit_code == 1

    # Demo reset bad instance
    res_reset_bad_inst = runner.invoke(
        app, ["demo", "reset", "valid-props-demo", "--instance", "bad-inst-99", "--fake"], env=env
    )
    assert res_reset_bad_inst.exit_code == 1

    # Live connection error paths for apply and restore (triggering error branch)
    refused_id = "refused-inst-props"
    conn = init_db()
    repo = DatabaseRepository(conn)
    repo.add_instance(
        InstanceCreate(
            id=refused_id,
            name="Refused Host",
            url="http://127.0.0.1:1",
            is_default=False,
        )
    )
    conn.close()

    res_apply_err = runner.invoke(
        app,
        [
            "demo",
            "properties",
            "apply",
            "valid-props-demo",
            "--instance",
            refused_id,
        ],
        env=env,
    )
    assert res_apply_err.exit_code == 1

    # Pre-save snapshot for refused instance to test live restore error
    snap_engine = PropertyEngine()
    snap_engine.save_snapshot(
        PropertySnapshot(
            bundle_id="valid-props-demo",
            instance_id=refused_id,
            timestamp="2026-10-29T12:00:00Z",
            original_values={"glide.ui.polaris.experience": "false"},
        )
    )
    res_restore_err = runner.invoke(
        app,
        [
            "demo",
            "properties",
            "restore",
            "valid-props-demo",
            "--instance",
            refused_id,
        ],
        env=env,
    )
    assert res_restore_err.exit_code == 1


def test_cli_fluent_commands(tmp_path: Path) -> None:
    """Verify workbench demo fluent inspect and diff CLI commands."""
    runner = CliRunner()
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()

    # 1. Bundle A with Fluent schema
    bundle_a = bundles_dir / "bundle-a"
    (bundle_a / "fluent").mkdir(parents=True)
    ts_a = """
    export const t1 = Table({
        name: 't1',
        label: 'Table 1',
        schema: {
            col_a: Record({ label: 'Col A', mandatory: true }),
        },
    })
    """
    (bundle_a / "fluent" / "app.now.ts").write_text(ts_a, encoding="utf-8")

    # 2. Bundle B with different Fluent schema
    bundle_b = bundles_dir / "bundle-b"
    (bundle_b / "fluent").mkdir(parents=True)
    ts_b = """
    export const t1 = Table({
        name: 't1',
        label: 'Table 1',
        schema: {
            col_a: Record({ label: 'Col A', mandatory: false }),
            col_b: Record({ label: 'Col B' }),
        },
    })
    export const t2 = Table({
        name: 't2',
        label: 'Table 2',
        schema: {},
    })
    """
    (bundle_b / "fluent" / "app.now.ts").write_text(ts_b, encoding="utf-8")

    # 3. Empty bundle without schemas
    bundle_empty = bundles_dir / "bundle-empty"
    bundle_empty.mkdir()

    env = {"WORKBENCH_BUNDLES_DIR": str(bundles_dir)}

    # Inspect bundle A
    res_inspect = runner.invoke(app, ["demo", "fluent", "inspect", "bundle-a"], env=env)
    assert res_inspect.exit_code == 0
    assert "t1" in res_inspect.stdout
    assert "col_a" in res_inspect.stdout

    # Inspect empty bundle
    res_empty = runner.invoke(app, ["demo", "fluent", "inspect", "bundle-empty"], env=env)
    assert res_empty.exit_code == 0
    assert "No Fluent schema" in res_empty.stdout

    # Inspect missing bundle
    res_missing = runner.invoke(app, ["demo", "fluent", "inspect", "missing-bundle"], env=env)
    assert res_missing.exit_code == 1
    assert "not found" in res_missing.stdout

    # Diff identical schemas
    res_diff_same = runner.invoke(app, ["demo", "fluent", "diff", "bundle-a", "bundle-a"], env=env)
    assert res_diff_same.exit_code == 0
    assert "identical" in res_diff_same.stdout

    # Diff different schemas (A -> B: added/modified)
    res_diff = runner.invoke(app, ["demo", "fluent", "diff", "bundle-a", "bundle-b"], env=env)
    assert res_diff.exit_code == 0
    assert "Added Tables" in res_diff.stdout
    assert "Modified Tables" in res_diff.stdout

    # Diff in reverse (B -> A: removed tables)
    res_diff_rev = runner.invoke(app, ["demo", "fluent", "diff", "bundle-b", "bundle-a"], env=env)
    assert res_diff_rev.exit_code == 0
    assert "Removed Tables" in res_diff_rev.stdout

    # Inspect without WORKBENCH_BUNDLES_DIR env to test fallback to settings.bundles_dir
    res_default_env = runner.invoke(app, ["demo", "fluent", "inspect", "sample-ai-assistant"])
    assert res_default_env.exit_code == 0

    # Diff missing bundles
    res_diff_missing_a = runner.invoke(
        app, ["demo", "fluent", "diff", "missing-a", "bundle-b"], env=env
    )
    assert res_diff_missing_a.exit_code == 1

    res_diff_missing_b = runner.invoke(
        app, ["demo", "fluent", "diff", "bundle-a", "missing-b"], env=env
    )
    assert res_diff_missing_b.exit_code == 1
