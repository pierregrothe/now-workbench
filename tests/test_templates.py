"""Tests for the reusable customer customization template engine."""

import json
from pathlib import Path

from now_workbench.domains.templates.engine import TemplateEngine
from now_workbench.domains.templates.models import TemplateInstantiationRequest


def test_template_instantiation_with_placeholders(tmp_path: Path) -> None:
    """Test replacing customer placeholders across manifest, Fluent, and seed files."""
    bundles_dir = tmp_path / "bundles"
    output_dir = tmp_path / "workspaces"
    bundles_dir.mkdir()
    output_dir.mkdir()

    base_bundle = bundles_dir / "sample-template"
    base_bundle.mkdir()
    (base_bundle / "fluent").mkdir()
    (base_bundle / "seed").mkdir()

    # Base manifest
    (base_bundle / "manifest.json").write_text(
        json.dumps(
            {
                "id": "sample-template",
                "name": "Incident Triage for {{customer_name}}",
                "version": "1.0.0",
                "description": "Customized for {{customer_name}}.",
                "sn_release": "Zurich",
                "required_plugins": ["com.snc.itsm"],
                "tags": ["ITSM"],
            }
        ),
        encoding="utf-8",
    )

    # Base Fluent file
    (base_bundle / "fluent" / "app.now.ts").write_text(
        "// Custom routing for {{customer_name}}\n"
        "export const route = { group: '{{assignment_group}}', color: '{{primary_color}}' };\n",
        encoding="utf-8",
    )

    # Base Seed record
    (base_bundle / "seed" / "incidents.json").write_text(
        json.dumps([{"short_description": "Network latency at {{customer_name}} HQ"}]),
        encoding="utf-8",
    )

    engine = TemplateEngine(bundles_dir=bundles_dir, output_dir=output_dir)
    result_path = engine.instantiate(
        base_bundle_id="sample-template",
        request=TemplateInstantiationRequest(
            target_bundle_id="nike-incident-router",
            customer_name="Nike Corporation",
            primary_color="#111827",
            assignment_group="Nike Tier 1 Operations",
        ),
    )

    assert result_path.exists()
    assert result_path.name == "nike-incident-router"

    # Verify manifest
    manifest = json.loads((result_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["id"] == "nike-incident-router"
    assert "Nike Corporation" in manifest["name"]

    # Verify Fluent code
    fluent_content = (result_path / "fluent" / "app.now.ts").read_text(encoding="utf-8")
    assert "Nike Corporation" in fluent_content
    assert "Nike Tier 1 Operations" in fluent_content
    assert "#111827" in fluent_content

    # Verify Seed data
    seed_data = json.loads((result_path / "seed" / "incidents.json").read_text(encoding="utf-8"))
    assert seed_data[0]["short_description"] == "Network latency at Nike Corporation HQ"


def test_reference_template_bundle() -> None:
    """Verify the reference enterprise customer service AI template bundle."""
    from now_workbench.domains.bundles.manager import BundleManager
    from now_workbench.platform.config.settings import settings

    mgr = BundleManager(storage_dir=settings.bundles_dir)
    tmpl_dir = settings.bundles_dir / "template-customer-service-ai"
    assert tmpl_dir.exists()

    info = mgr.inspect_bundle(tmpl_dir)
    assert info.manifest.id == "template-customer-service-ai"
    assert len(info.fluent_files) >= 1
    assert len(info.seed_files) >= 1
    assert info.has_walkthrough is True


def test_template_missing_base_bundle(tmp_path: Path) -> None:
    """Verify FileNotFoundError when base bundle does not exist."""
    import pytest

    engine = TemplateEngine(bundles_dir=tmp_path, output_dir=tmp_path)
    req = TemplateInstantiationRequest(target_bundle_id="target", customer_name="Customer")
    with pytest.raises(FileNotFoundError, match="Base bundle 'missing' not found"):
        engine.instantiate("missing", req)


def test_template_unparseable_manifest_handled(tmp_path: Path) -> None:
    """Verify that unparseable manifest.json passes without crashing during placeholder pass."""
    base = tmp_path / "bad-manifest-bundle"
    base.mkdir()
    (base / "manifest.json").write_text("invalid json manifest {{customer_name}}", encoding="utf-8")
    engine = TemplateEngine(bundles_dir=tmp_path, output_dir=tmp_path / "out")
    req = TemplateInstantiationRequest(target_bundle_id="target-bad", customer_name="Customer Corp")
    res = engine.instantiate("bad-manifest-bundle", req)
    assert (res / "manifest.json").exists()
    assert "Customer Corp" in (res / "manifest.json").read_text(encoding="utf-8")
