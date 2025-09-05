import runpy


def test_main_delegates_to_cli(monkeypatch):
    """Ensure main.main() delegates to cli() without invoking real CLI."""
    called = {"count": 0}

    def fake_cli():
        called["count"] += 1

    # Patch the click command entry so we don't execute the real CLI
    import qdrant_loader_mcp_server.main as main_mod

    monkeypatch.setattr(main_mod, "cli", fake_cli, raising=True)

    # Invoke main and verify our stub was called
    main_mod.main()

    assert called["count"] == 1


def test_package___main___executes_main(monkeypatch):
    """Running the package as a module should call main.main()."""
    called = {"count": 0}

    def fake_main():
        called["count"] += 1

    monkeypatch.setattr(
        "qdrant_loader_mcp_server.main.main", fake_main, raising=True
    )

    # Execute the package's __main__ module
    runpy.run_module("qdrant_loader_mcp_server.__main__", run_name="__main__")

    assert called["count"] == 1


