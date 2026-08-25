import pytest

from app.services.encryption_service import encrypt_file
from app.services.fragmentation_service import (
    FragmentationError,
    fragment_file,
    list_fragments,
    reconstruct_file,
)
from app.services.file_service import resolve_path


def test_fragment_file_splits_into_requested_count(db_session):
    encrypted = encrypt_file(db_session, "payload.bin", b"A" * 1000)
    fragments = fragment_file(db_session, encrypted.id, 4)

    assert len(fragments) == 4
    assert {f.fragment_index for f in fragments} == {0, 1, 2, 3}
    assert all(f.total_fragments == 4 for f in fragments)
    assert all(f.transfer_id == fragments[0].transfer_id for f in fragments)
    assert sum(f.size for f in fragments) == resolve_path(encrypted.storage_path).stat().st_size


def test_fragment_and_reconstruct_matches_encrypted_file(db_session):
    encrypted = encrypt_file(db_session, "payload.bin", b"reconstruct-me" * 37)
    encrypted_bytes = resolve_path(encrypted.storage_path).read_bytes()

    fragments = fragment_file(db_session, encrypted.id, 5)
    reconstructed = reconstruct_file(db_session, fragments[0].transfer_id)

    assert reconstructed == encrypted_bytes


def test_reconstruct_detects_corrupted_fragment(db_session):
    encrypted = encrypt_file(db_session, "payload.bin", b"B" * 500)
    fragments = fragment_file(db_session, encrypted.id, 3)

    path = resolve_path(fragments[1].storage_path)
    corrupted = bytearray(path.read_bytes())
    corrupted[0] ^= 0xFF
    path.write_bytes(bytes(corrupted))

    with pytest.raises(FragmentationError):
        reconstruct_file(db_session, fragments[0].transfer_id)


def test_reconstruct_detects_missing_fragment(db_session):
    encrypted = encrypt_file(db_session, "payload.bin", b"C" * 500)
    fragments = fragment_file(db_session, encrypted.id, 3)

    db_session.delete(fragments[1])
    db_session.commit()

    with pytest.raises(FragmentationError):
        reconstruct_file(db_session, fragments[0].transfer_id)


def test_fragment_count_cannot_exceed_file_size(db_session):
    # AES-GCM adds 12 bytes of nonce + 16 bytes of tag, so a 1-byte original
    # still yields a 29-byte encrypted payload; request more fragments than that.
    encrypted = encrypt_file(db_session, "tiny.bin", b"A")
    with pytest.raises(ValueError):
        fragment_file(db_session, encrypted.id, 50)


def test_fragment_unknown_file_raises(db_session):
    with pytest.raises(FragmentationError):
        fragment_file(db_session, "does-not-exist", 3)


def test_list_fragments_ordered_by_index(db_session):
    encrypted = encrypt_file(db_session, "payload.bin", b"D" * 300)
    created = fragment_file(db_session, encrypted.id, 6)

    fetched = list_fragments(db_session, created[0].transfer_id)
    assert [f.fragment_index for f in fetched] == [0, 1, 2, 3, 4, 5]
