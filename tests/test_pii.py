from pitchops.comments.pii import author_hash, redact


def test_author_hash_stable_and_peppered() -> None:
    a = author_hash(b"k1", "UCabc")
    assert a == author_hash(b"k1", "UCabc") and a != author_hash(b"k2", "UCabc") and len(a or "") == 64
    assert "UCabc" not in (a or "") and author_hash(b"k", None) is None


def test_redact_contacts() -> None:
    s, n = redact("Call me +971 50 123 4567 or 0501234567, mail a.b@x.com, wa.me/971501234567 @john.doe")
    assert "971" not in s and "050" not in s and "@x.com" not in s and "john" not in s
    assert s.count("[phone]") == 2 and "[email]" in s and "[url]" in s and "[handle]" in s and n == 5


def test_redact_emirates_id_and_url() -> None:
    s, n = redact("my id 784-1990-1234567-1 see https://instagram.com/someone")
    assert s == "my id [id] see [url]" and n == 2


def test_keeps_prices_and_years() -> None:
    s, n = redact("Is AED 1,200,000 for 2 BR in 2026 a good price? 8% ROI")
    assert n == 0 and s.startswith("Is AED 1,200,000")
