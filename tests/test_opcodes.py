from openzk.opcodes import OPCODES


def test_known_opcodes_present() -> None:
    assert OPCODES["DownloadUserPhoto"] == 0x271a
    assert OPCODES["GetUserFace"] == 0x0096
    assert OPCODES["GetPhotoByName"] == 0x07de
    assert OPCODES["GetPhotoCount"] == 0x07dd
    assert OPCODES["GetPhotoNamesByTime"] == 0x07e0
    assert OPCODES["DownloadPicture"] == 0x272d
