"""Launch one immediate v067 import/open/solve chain."""

import os


def launch_head_only_solve_v067():
    os.environ["GAHYEON_IDENTITY_SOLVE_VERSION"] = "v067"
    os.environ["GAHYEON_IDENTITY_SOLVE_WAIT_TICKS"] = "1"
    os.environ["GAHYEON_IDENTITY_SOLVE_IMMEDIATE"] = "1"
    from gahyeon_solve_head_only_identity_v059 import start_head_only_identity_v059

    start_head_only_identity_v059()


launch_head_only_solve_v067()
