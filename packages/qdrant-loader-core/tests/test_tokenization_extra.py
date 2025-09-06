from importlib import import_module


def test_tiktoken_counter_handles_encode_error(monkeypatch):
    mod = import_module("qdrant_loader_core.llm.tokenization")
    TiktokenTokenCounter = mod.TiktokenTokenCounter

    class _Enc:
        def encode(self, text):  # type: ignore[no-untyped-def]
            raise ValueError("boom")

    if getattr(mod, "tiktoken", None) is not None:
        monkeypatch.setattr(mod.tiktoken, "get_encoding", lambda _: _Enc())
        counter = TiktokenTokenCounter("cl100k_base")
        # Falls back to char count on encode failure
        assert counter.count("hello") == 5
    else:
        # When tiktoken is missing, constructor sets _encoding=None and falls back
        counter = TiktokenTokenCounter("any")
        assert counter.count("hello") == 5
