"""Tests for instance registry, templates, and admin diagnostics API endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from now_workbench.api.app import create_app


def test_api_instances_and_admin_diagnostics() -> None:
    """Verify instance registration, activation, and admin diagnostics."""
    app = create_app()
    client = TestClient(app)

    # 1. Admin diagnostics
    diag_resp = client.get("/api/admin/diagnostics")
    assert diag_resp.status_code == 200
    diag_data = diag_resp.json()
    assert diag_data["app_version"] == "0.2.0"
    assert "toolchain" in diag_data

    # 2. List instances
    list_resp = client.get("/api/instances")
    assert list_resp.status_code == 200
    instances = list_resp.json()
    assert len(instances) >= 1

    # 3. Register a new instance
    create_resp = client.post(
        "/api/instances",
        json={
            "id": "acme-dev-subprod",
            "name": "Acme Sub-Production",
            "url": "https://acmedev.service-now.com",
            "username": "admin",
            "password": "pwd",
            "auth_type": "basic",
            "is_default": False,
        },
    )
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["id"] == "acme-dev-subprod"

    # 4. Activate instance
    activate_resp = client.post("/api/instances/acme-dev-subprod/activate")
    assert activate_resp.status_code == 200
    assert activate_resp.json()["active_instance_id"] == "acme-dev-subprod"

    # 5. Test instance endpoint (handles offline / unreachable gracefully)
    test_resp = client.post("/api/instances/acme-dev-subprod/test")
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert "status" in test_data
    assert "http_code" in test_data

    # 6. Update instance (rename and update authentication)
    update_resp = client.put(
        "/api/instances/acme-dev-subprod",
        json={
            "name": "Acme Renamed Demo",
            "username": "demo_admin",
            "password": "new_secure_pwd",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Acme Renamed Demo"
    assert updated["username"] == "demo_admin"
    # The release is detected from the instance (ADR-014) and cannot be set by clients.
    rejected = client.put("/api/instances/acme-dev-subprod", json={"release": "Xanadu"})
    assert rejected.status_code == 422

    # Query by name works seamlessly
    query_by_name = client.get("/api/instances")
    names = [i["name"] for i in query_by_name.json()]
    assert "Acme Renamed Demo" in names

    # 7. Delete instance
    del_resp = client.delete("/api/instances/acme-dev-subprod")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_instance_id"] == "acme-dev-subprod"

    # 404 on deleting non-existent instance
    del_404 = client.delete("/api/instances/non-existent-inst")
    assert del_404.status_code == 404

    # 404 on updating non-existent instance
    put_404 = client.put(
        "/api/instances/non-existent-inst",
        json={"name": "Ghost"},
    )
    assert put_404.status_code == 404


def test_api_template_endpoints() -> None:
    """Verify listing and instantiating customization templates."""
    app = create_app()
    client = TestClient(app)

    # 1. List templates
    tmpl_resp = client.get("/api/templates")
    assert tmpl_resp.status_code == 200
    templates = tmpl_resp.json()
    assert len(templates) >= 1
    tmpl_id = templates[0]["id"]

    # 2. Instantiate template
    inst_resp = client.post(
        f"/api/templates/{tmpl_id}/instantiate",
        json={
            "target_bundle_id": "cust-pfizer-triage",
            "customer_name": "Pfizer Health",
            "primary_color": "#005ea2",
            "secondary_color": "#1b8567",
            "logo_url": "https://example.com/logo.png",
            "assignment_group": "HealthDesk Tier 1",
        },
    )
    assert inst_resp.status_code == 200
    inst_data = inst_resp.json()
    assert inst_data["bundle_id"] == "cust-pfizer-triage"
    assert inst_data["customer_name"] == "Pfizer Health"

    # 3. Template not found 404
    bad_tmpl = client.get("/api/templates/non-existent-template")
    assert bad_tmpl.status_code == 404

    # 4. Instantiate non-existent template 404
    bad_inst = client.post(
        "/api/templates/non-existent-template/instantiate",
        json={
            "target_bundle_id": "test",
            "customer_name": "X",
        },
    )
    assert bad_inst.status_code == 404


def test_api_demos_and_error_routes() -> None:
    """Verify demo bundle inspection, export, import error handling, and 404 routes."""
    app = create_app()
    client = TestClient(app)

    # 1. Inspect bundle valid & invalid
    resp_ok = client.get("/api/demos/sample-ai-assistant")
    assert resp_ok.status_code == 200
    assert resp_ok.json()["manifest"]["id"] == "sample-ai-assistant"

    resp_404 = client.get("/api/demos/bundle-404")
    assert resp_404.status_code == 404

    # 2. Export valid & invalid
    exp_ok = client.get("/api/demos/sample-ai-assistant/export")
    assert exp_ok.status_code == 200
    assert "zip" in exp_ok.headers.get("content-type", "").lower()

    exp_bad = client.get("/api/demos/bundle-404/export")
    assert exp_bad.status_code == 400

    # 3. Build valid with fake runner & 404 bundle
    b_ok = client.post("/api/demos/sample-ai-assistant/build", json={"stream_logs": False})
    assert b_ok.status_code == 200

    b_404 = client.post("/api/demos/bundle-404/build", json={"stream_logs": False})
    assert b_404.status_code == 404

    # 4. Deploy valid & 404 bundle
    d_ok = client.post("/api/demos/sample-ai-assistant/deploy", json={"stream_logs": True})
    assert d_ok.status_code == 200

    d_404 = client.post("/api/demos/bundle-404/deploy", json={"stream_logs": True})
    assert d_404.status_code == 404

    # 5. Seed & rollback 404/400
    s_404 = client.post("/api/demos/bundle-404/seed", json={"fake_mode": True})
    assert s_404.status_code == 404

    rb_404 = client.post("/api/demos/seed/op-404/rollback?fake_mode=true")
    assert rb_404.status_code == 400

    # 6. Activate & test non-existent instances 404
    act_404 = client.post("/api/instances/inst-404/activate")
    assert act_404.status_code == 404

    t_404 = client.post("/api/instances/inst-404/test")
    assert t_404.status_code == 404

    # 7. Seed with invalid instance ID returns 400
    bad_inst_seed = client.post(
        "/api/demos/sample-ai-assistant/seed",
        json={"instance_id": "non-existent-id"},
    )
    assert bad_inst_seed.status_code == 400

    # 8. Template instantiate failure returns 400
    from now_workbench.db import TemplateRecord, db_session

    with db_session() as repo:
        repo.save_template(
            TemplateRecord(
                id="bad-base-template",
                name="Bad Base",
                description="desc",
                base_bundle_id="non-existent-base-bundle",
            )
        )
    bad_base_res = client.post(
        "/api/templates/bad-base-template/instantiate",
        json={"target_bundle_id": "t", "customer_name": "C"},
    )
    assert bad_base_res.status_code == 400


def test_verify_instance_authentication_responses() -> None:
    """Verify live authentication probing across HTTP 200, 401, 500, and network error."""
    import httpx

    from now_workbench.connectivity import verify_instance_authentication
    from now_workbench.db.models import InstanceRecord

    inst = InstanceRecord(
        id="test-inst",
        name="Test",
        url="https://test.service-now.com",
        username="admin",
        password="pwd",
    )

    # 1. 200 Authenticated
    cl_200 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    status, msg, code = verify_instance_authentication(inst, client=cl_200)
    assert status == "authenticated"
    assert code == 200

    # 2. 401 Auth Failed
    cl_401 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    status, msg, code = verify_instance_authentication(inst, client=cl_401)
    assert status == "auth_failed"
    assert code == 401

    # 3. 500 Error
    cl_500 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    status, msg, code = verify_instance_authentication(inst, client=cl_500)
    assert status == "error"
    assert code == 500

    # 4. Connection Exception
    def throw_err(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network unreachable")

    cl_err = httpx.Client(transport=httpx.MockTransport(throw_err))
    status, msg, code = verify_instance_authentication(inst, client=cl_err)
    assert status == "unreachable"
    assert code == 0


def test_api_runbook_endpoints() -> None:
    """Verify demo walkthrough runbook retrieval and stage verification API routes."""
    app = create_app()
    client = TestClient(app)

    # 1. Valid runbook retrieval
    resp = client.get("/api/demos/sample-ai-assistant/runbook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bundle_id"] == "sample-ai-assistant"
    assert len(data["stages"]) == 3
    assert len(data["personas"]) == 1
    assert data["personas"][0]["name"] == "Beth Anglin"

    # 2. Non-existent bundle runbook 404
    resp_404 = client.get("/api/demos/non-existent-bundle-404/runbook")
    assert resp_404.status_code == 404

    # 3. Stage verification in simulation mode
    resp_v1 = client.post(
        "/api/demos/sample-ai-assistant/runbook/verify-stage",
        json={"step_number": 1, "fake_mode": True},
    )
    assert resp_v1.status_code == 200
    v1_data = resp_v1.json()
    assert v1_data["success"] is True
    assert v1_data["step_number"] == 1

    # 4. Stage not found in runbook 404
    resp_bad_stage = client.post(
        "/api/demos/sample-ai-assistant/runbook/verify-stage",
        json={"step_number": 999, "fake_mode": True},
    )
    assert resp_bad_stage.status_code == 404

    # 5. Non-existent bundle verify stage 404
    resp_bad_bundle = client.post(
        "/api/demos/non-existent-bundle-404/runbook/verify-stage",
        json={"step_number": 1, "fake_mode": True},
    )
    assert resp_bad_bundle.status_code == 404
    assert "Stage 999 not found" in resp_bad_stage.json()["detail"]

    # 5. Target instance not found 400
    resp_bad_inst = client.post(
        "/api/demos/sample-ai-assistant/runbook/verify-stage",
        json={"step_number": 1, "instance_id": "non-existent-inst-id", "fake_mode": True},
    )
    assert resp_bad_inst.status_code == 400

    # 6. Bundle without walkthrough guide returns 404
    import shutil
    from pathlib import Path

    no_wt_dir = Path("bundles/test-bundle-no-wt")
    no_wt_dir.mkdir(parents=True, exist_ok=True)
    (no_wt_dir / "manifest.json").write_text(
        '{"id":"test-bundle-no-wt","name":"No WT","version":"1.0"}', encoding="utf-8"
    )
    try:
        resp_no_wt = client.get("/api/demos/test-bundle-no-wt/runbook")
        assert resp_no_wt.status_code == 404
        assert "not found" in resp_no_wt.json()["detail"]

        resp_v_no_wt = client.post(
            "/api/demos/test-bundle-no-wt/runbook/verify-stage",
            json={"step_number": 1, "fake_mode": True},
        )
        assert resp_v_no_wt.status_code == 404
    finally:
        shutil.rmtree(no_wt_dir, ignore_errors=True)


def test_api_property_and_reset_endpoints() -> None:
    """Verify demo properties inspection, apply, restore, and unified reset API endpoints."""
    app = create_app()
    client = TestClient(app)

    # 1. GET properties for existing demo
    resp_props = client.get("/api/demos/sample-ai-assistant/properties")
    assert resp_props.status_code == 200
    data = resp_props.json()
    assert data["bundle_id"] == "sample-ai-assistant"
    assert "properties" in data

    # 2. GET properties 404 for missing bundle
    assert client.get("/api/demos/missing-bundle-999/properties").status_code == 404

    # 3. POST apply properties in fake mode
    resp_apply = client.post(
        "/api/demos/sample-ai-assistant/properties/apply",
        json={"fake_mode": True},
    )
    assert resp_apply.status_code == 200
    apply_data = resp_apply.json()
    assert apply_data["success"] is True

    # 4. POST apply 404 missing bundle and 400 bad instance
    assert (
        client.post(
            "/api/demos/missing-bundle-999/properties/apply",
            json={"fake_mode": True},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/demos/sample-ai-assistant/properties/apply",
            json={"instance_id": "bad-inst-999", "fake_mode": True},
        ).status_code
        == 400
    )

    # 5. POST restore properties in fake mode
    resp_restore = client.post(
        "/api/demos/sample-ai-assistant/properties/restore",
        json={"fake_mode": True},
    )
    assert resp_restore.status_code == 200
    restore_data = resp_restore.json()
    assert restore_data["success"] is True

    # 6. POST restore 404 missing bundle and 400 bad instance
    assert (
        client.post(
            "/api/demos/missing-bundle-999/properties/restore",
            json={"fake_mode": True},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/demos/sample-ai-assistant/properties/restore",
            json={"instance_id": "bad-inst-999", "fake_mode": True},
        ).status_code
        == 400
    )

    # 7. POST unified reset in fake mode
    resp_reset = client.post(
        "/api/demos/sample-ai-assistant/reset",
        json={"fake_mode": True},
    )
    assert resp_reset.status_code == 200
    reset_data = resp_reset.json()
    assert reset_data["success"] is True
    assert reset_data["bundle_id"] == "sample-ai-assistant"

    # 8. POST reset 404 missing bundle and 400 bad instance
    assert (
        client.post(
            "/api/demos/missing-bundle-999/reset",
            json={"fake_mode": True},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/demos/sample-ai-assistant/reset",
            json={"instance_id": "bad-inst-999", "fake_mode": True},
        ).status_code
        == 400
    )


def test_api_fluent_endpoints() -> None:
    """Verify demo bundle Fluent schema retrieval and diff API endpoints."""
    app = create_app()
    client = TestClient(app)

    # 1. GET fluent schemas for sample-ai-assistant
    resp = client.get("/api/demos/sample-ai-assistant/fluent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["bundle_id"] == "sample-ai-assistant"
    assert len(data["tables"]) >= 1
    table_names = [t["name"] for t in data["tables"]]
    assert "x_demo_ai_routing_log" in table_names

    # 2. GET fluent schemas 404 for missing bundle
    assert client.get("/api/demos/missing-bundle-999/fluent").status_code == 404

    # 3. POST fluent diff comparing bundle with itself
    resp_diff = client.post(
        "/api/demos/sample-ai-assistant/fluent/diff",
        json={"target_bundle_id": "sample-ai-assistant"},
    )
    assert resp_diff.status_code == 200
    diff_data = resp_diff.json()
    assert diff_data["identical"] is True
    assert diff_data["added_tables"] == []

    # 4. POST fluent diff 404 for missing source bundle
    assert (
        client.post(
            "/api/demos/missing-bundle-source/fluent/diff",
            json={"target_bundle_id": "sample-ai-assistant"},
        ).status_code
        == 404
    )

    # 5. POST fluent diff 404 for missing compare bundle
    assert (
        client.post(
            "/api/demos/sample-ai-assistant/fluent/diff",
            json={"target_bundle_id": "missing-bundle-target"},
        ).status_code
        == 404
    )


def test_api_threads_and_messages_endpoints(tmp_path: Path) -> None:
    """Verify conversational thread creation, default thread seeding, and contextual replies."""
    import os

    old_db = os.environ.get("WORKBENCH_DB_PATH")
    try:
        db_file = tmp_path / "threads_test.db"
        os.environ["WORKBENCH_DB_PATH"] = str(db_file)

        app = create_app()
        client = TestClient(app)

        # 1. GET /api/threads seeds default-thread when empty
        t_resp = client.get("/api/threads")
        assert t_resp.status_code == 200
        threads = t_resp.json()
        assert len(threads) == 1
        assert threads[0]["id"] == "default-thread"

        # Calling GET /api/threads again returns existing thread without duplicating
        t_resp2 = client.get("/api/threads")
        assert len(t_resp2.json()) == 1

        # 2. Create custom thread
        c_resp = client.post("/api/threads", json={"id": "custom-thread", "title": "Custom Chat"})
        assert c_resp.status_code == 200
        assert c_resp.json()["id"] == "custom-thread"

        # 3. GET messages for non-existent thread -> 404, POST message -> 404
        assert client.get("/api/threads/missing-999/messages").status_code == 404
        assert (
            client.post(
                "/api/threads/missing-999/messages",
                json={"content": "hello"},
            ).status_code
            == 404
        )

        # 4. Test auto-seeding default-thread on fresh DB when calling GET/POST messages directly
        db_file2 = tmp_path / "threads_direct.db"
        os.environ["WORKBENCH_DB_PATH"] = str(db_file2)
        direct_msgs = client.get("/api/threads/default-thread/messages")
        assert direct_msgs.status_code == 200
        assert len(direct_msgs.json()) == 1

        db_file3 = tmp_path / "threads_post_direct.db"
        os.environ["WORKBENCH_DB_PATH"] = str(db_file3)
        post_direct = client.post(
            "/api/threads/default-thread/messages",
            json={"content": "Customize customer brand template"},
        )
        assert post_direct.status_code == 200
        msgs = post_direct.json()
        assert any(m["widget_type"] == "template_form" for m in msgs)

        # 5. Contextual replies for instance, fluent, general, and non-user role
        r_inst = client.post(
            "/api/threads/default-thread/messages",
            json={"content": "Switch target instance"},
        )
        assert r_inst.status_code == 200
        assert r_inst.json()[-1]["widget_type"] == "instance_selector"

        r_fluent = client.post(
            "/api/threads/default-thread/messages",
            json={"content": "Inspect fluent table schema"},
        )
        assert r_fluent.status_code == 200
        assert "Fluent Schema" in r_fluent.json()[-1]["content"]

        r_gen = client.post(
            "/api/threads/default-thread/messages",
            json={"content": "Run demo verification"},
        )
        assert r_gen.status_code == 200
        assert "Acknowledged" in r_gen.json()[-1]["content"]

        r_sys = client.post(
            "/api/threads/default-thread/messages",
            json={"content": "System note", "role": "system"},
        )
        assert r_sys.status_code == 200
        assert r_sys.json()[-1]["role"] == "system"

        # 6. Archive, unarchive, get, and delete conversation thread + context limit
        new_t = client.post(
            "/api/threads",
            json={"id": "otto-conv-1", "title": "New Otto Conversation"},
        )
        assert new_t.status_code == 200
        assert new_t.json()["archived"] is False

        # First user message auto-titles a generic thread and stores generative tiles
        m_res = client.post(
            "/api/threads/otto-conv-1/messages",
            json={"content": "how many instande I have"},
        )
        assert m_res.status_code == 200
        m_list = m_res.json()
        assert len(m_list) == 2
        assert m_list[-1]["widget_data"]["tiles"][0]["type"] == "instance-kpi"

        t_meta = client.get("/api/threads/otto-conv-1")
        assert t_meta.status_code == 200
        assert t_meta.json()["title"] == "how many instande I have"
        assert t_meta.json()["message_count"] == 2

        # Archive conversation
        arch_res = client.put("/api/threads/otto-conv-1", json={"archived": True})
        assert arch_res.status_code == 200
        assert arch_res.json()["archived"] is True

        active_only = client.get("/api/threads?include_archived=false").json()
        assert all(t["id"] != "otto-conv-1" for t in active_only)

        # Fill up to 20 messages (9 more user+assistant pairs = 18 more messages -> total 20)
        for idx in range(9):
            fill_res = client.post(
                "/api/threads/otto-conv-1/messages",
                json={"content": f"Follow up question {idx}"},
            )
            assert fill_res.status_code == 200

        # 21st message exceeds context limit (MAX_THREAD_CONTEXT_MESSAGES = 20) -> 400
        over_limit = client.post(
            "/api/threads/otto-conv-1/messages",
            json={"content": "One message past the 20-message limit"},
        )
        assert over_limit.status_code == 400
        assert "context limit reached" in over_limit.json()["detail"].lower()

        # Delete conversation permanently
        del_res = client.delete("/api/threads/otto-conv-1")
        assert del_res.status_code == 200
        assert del_res.json()["deleted_thread_id"] == "otto-conv-1"
        assert client.get("/api/threads/otto-conv-1").status_code == 404
        assert client.delete("/api/threads/otto-conv-1").status_code == 404
        assert client.put("/api/threads/otto-conv-1", json={"archived": False}).status_code == 404
    finally:
        if old_db is None:
            os.environ.pop("WORKBENCH_DB_PATH", None)
        else:
            os.environ["WORKBENCH_DB_PATH"] = old_db
