from importlib import import_module


def test_char_count_token_counter():
    module = import_module("qdrant_loader_core.llm.tokenization")
    CharCountTokenCounter = module.CharCountTokenCounter
    counter = CharCountTokenCounter()
    assert counter.count("") == 0
    assert counter.count("abc") == 3
    assert counter.count("hello world") == 11


def test_tiktoken_counter_graceful_fallback(monkeypatch):
    module = import_module("qdrant_loader_core.llm.tokenization")
    TiktokenTokenCounter = module.TiktokenTokenCounter

    # Simulate missing tiktoken encoding
    class _Enc:
        def encode(self, text):  # type: ignore[no-untyped-def]
            return [1] * len(text)

    # If tiktoken is present, patch get_encoding; else counter will fallback to char count
    if getattr(module, "tiktoken", None) is not None:
        monkeypatch.setattr(module.tiktoken, "get_encoding", lambda _: _Enc())
        counter = TiktokenTokenCounter("cl100k_base")
        assert counter.count("abc") == 3
    else:
        counter = TiktokenTokenCounter("cl100k_base")
        assert counter.count("abc") == 3  # falls back to char count
