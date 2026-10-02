"""Launch v071 with warning-only conform results preserved as QA findings."""

import os


def launch_head_only_solve_v071():
    os.environ["GAHYEON_IDENTITY_SOLVE_VERSION"] = "v071"
    os.environ["GAHYEON_IDENTITY_SOLVE_WAIT_TICKS"] = "1"
    os.environ["GAHYEON_IDENTITY_SOLVE_IMMEDIATE"] = "1"
    from gahyeon_solve_head_only_identity_v059 import start_head_only_identity_v059

    start_head_only_identity_v059()


launch_head_only_solve_v071()
