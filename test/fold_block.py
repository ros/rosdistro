import itertools
import os


class BaseCiCfg:
    _block_id_gen = itertools.count(1)

    def __init__(self):
        self.block_id = next(self._block_id_gen)

    @classmethod
    def is_ci(cls) -> bool:
        raise NotImplementedError("Use BaseCiCfg only as fallback")

    def get_message(self, msg: str = "") -> str:
        return msg

    def _get_message_folded(self, msg: str = "") -> str:
        if msg:
            msg += ", "
        msg += "see folded block '%s' above for details" % self.get_block_name()
        return msg

    def get_block_name(self) -> str:
        return "block%d" % self.block_id

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        pass


class GithubActionsCiCfg(BaseCiCfg):
    @classmethod
    def is_ci(cls) -> bool:
        return os.environ.get("GITHUB_ACTIONS") == "true"

    def get_message(self, msg=""):
        return self._get_message_folded(msg)

    def __enter__(self):
        print("\n::group::%s" % self.get_block_name())
        return self

    def __exit__(self, type, value, traceback):
        print("\n::endgroup::")


# determine CI system, and set as Fold
for cls_ in BaseCiCfg.__subclasses__():
    if cls_.is_ci():
        Fold = cls_
        break
else:
    Fold = BaseCiCfg
