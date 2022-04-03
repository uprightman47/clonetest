#!/bin/sh
''''exec python -u "$0" ${1+"$@"} # '''

import os
import sys
import time
import tempfile
import traceback
import termcolor
import threading
import subprocess
import multiprocessing as mp
from subprocess import CalledProcessError
from typing import List, Optional
from pathlib import Path

from ijcai2022nmmo import submission as subm

IMAGE = "ijcai2022nmmo/submission-runtime"
CONTAINER = "ijcai2022-nmmo-runner"
PORT = 12343


def run_team_server(submission_path: str):
    subm.check(submission_path)
    team_klass, init_params = subm.parse_submission(submission_path)
    print(f"Start TeamServer for {team_klass.__name__}")
    from ijcai2022nmmo import TeamServer
    server = TeamServer("0.0.0.0", PORT, team_klass, init_params)
    server.run()


def run_submission_in_process(submission_path) -> mp.Process:
    mp.set_start_method("fork", force=True)

    def run_server():
        run_team_server(submission_path)

    p = mp.Process(target=run_server, daemon=True)
    p.start()
    return p


def run_submission_in_docker(submission_path):
    need_root = True if os.system("docker ps 1>/dev/null 2>&1") else False

    def _shell(command, capture_output=True, print_command=True):
        if command.startswith("docker") and need_root:
            command = "sudo " + command
        if print_command:
            print(command)
        r = subprocess.run(command, shell=True, capture_output=capture_output)
        if not capture_output: return
        if r.returncode != 0:
            # grep return 1 when no lines matching
            if r.returncode == 1 and "grep" in command:
                pass
            else:
                raise CalledProcessError(r.returncode, r.args, r.stdout,
                                         r.stderr)
        return r.stdout.decode().strip()
    ok(f"Try build image {IMAGE}:local ...")
    _shell(f"docker build -t {IMAGE}:local -f Dockerfile .", capture_output=False)
    if _shell(f'docker ps -a | grep -w "{CONTAINER}"') != "":
        _shell(f"docker stop {CONTAINER}")
        _shell(f"docker rm {CONTAINER}")
    cwd = Path(__file__).parent.resolve().as_posix()
    command = f"python tool.py run_team_server --submission={submission_path}"
    container_id = _shell(
        f"docker run -it -d --name {CONTAINER} -v {cwd}:/home/aicrowd -p {PORT}:{PORT} {IMAGE}:local {command}"
    )

    threading.Thread(target=_shell,
                     args=(f"docker logs -f {container_id}", False),
                     daemon=True).start()

    def _check_container_alive():
        while 1:
            ret = _shell(
                f"docker inspect {container_id} --format='{{{{.State.ExitCode}}}}'",
                print_command=False)
            if ret != "0":
                err(f"Container {container_id} exit unexpectedly")
                os._exit(1)
            time.sleep(1)

    threading.Thread(target=_check_container_alive, daemon=True).start()

    return container_id


def ok(msg: str):
    print(termcolor.colored(msg, "green", attrs=['bold']))


def warn(msg: str):
    print(termcolor.colored(msg, "yellow", attrs=['bold']))


def err(msg: str):
    print(termcolor.colored(msg, "red", attrs=['bold']))


def rollout(submission_path: str,
            n_episode: int = 1,
            render: bool = False,
            remote: Optional[str] = None):
    from ijcai2022nmmo import CompetitionConfig

    class Config(CompetitionConfig):
        PATH_MAPS = 'maps/medium/evaluation'

    if remote:
        if remote == "docker":
            ok(f"Try run submission in docker container ...")
            container_id = run_submission_in_docker(submission_path)
            ok(f"Submission is running in container {container_id}")
        elif remote == "process":
            ok(f"Try run submission in subprocess ...")
            p = run_submission_in_process(submission_path)
            ok(f"Submission is running in process {p.pid}")
        else:
            err(f"remote should be either docker or process")
            sys.exit(1)

        from ijcai2022nmmo import ProxyTeam
        team = ProxyTeam("my-submission", Config(), "127.0.0.1", PORT)
    else:
        team = subm.get_team_from_submission(submission_path, f"my-submission",
                                             Config())

    try:
        from ijcai2022nmmo import RollOut, scripted
        ro = RollOut(
            Config(),
            [
                scripted.RandomTeam(f"random-{i}", Config())
                for i in range(CompetitionConfig.NPOP - 1)
            ] + [team],
            True,
        )
        ro.run(n_episode=n_episode, render=render)
    except:
        raise
    finally:
        if remote:
            team.stop()


class Toolkit:
    def test(self,
             submission: str = "my-submission",
             n_episode: int = 1,
             render: bool = False,
             remote: Optional[str] = None):
        from art import text2art
        subm.check(submission)
        ok(f"Testing {submission} ...")
        try:
            rollout(submission, n_episode, render, remote)
        except:
            traceback.print_exc()
            err(text2art("TEST FAIL", "sub-zero"))
            sys.exit(1)
        else:
            ok(text2art("TEST PASS", "sub-zero"))

    def run_team_server(self, submission: str):
        run_team_server(submission)

    def check_requirements(
        self,
        submission: str,
        strict: bool = False,
        default_packages_path: str = "docker/requirements.txt",
    ):
        if not os.path.exists(default_packages_path):
            err(f"The default package list {default_packages_path} not exist")
            sys.exit(1)

        subm.check(submission)
        with tempfile.TemporaryDirectory() as tmpdir:
            subm_reqm_path = os.path.join(tmpdir, 'requirements.txt')
            p = subprocess.Popen(
                f"pipreqs --savepath {subm_reqm_path} {submission}",
                shell=True)
            ret = p.wait()
            if ret:
                err("Check requirements failed!")
                sys.exit(2)

            def _package(x: str) -> str:
                return x.split("=")[0]

            def _version(x: str) -> str:
                return x.split("=")[-1]

            def _read_requirements(path: str) -> List[str]:
                with open(path, "r") as fp:
                    requirements = fp.read().splitlines()
                requirements = [
                    reqm for reqm in requirements
                    if reqm and not reqm.startswith("#")
                ]
                if not strict:
                    requirements = [_package(x) for x in requirements]
                return requirements

            subm_requirements = _read_requirements(subm_reqm_path)
            default_packages = _read_requirements(default_packages_path)
            mapping = {_package(x): x for x in default_packages}

            fault = False
            for reqm in subm_requirements:
                if reqm not in default_packages:
                    fault = True
                    if not strict:
                        err(f"Package[{reqm}] is not in competition env")
                    else:
                        package = _package(reqm)
                        if package in mapping:
                            local_version = _version(reqm)
                            competition_version = _version(mapping[package])
                            warn(
                                f"Package[{package}] version conflicts, local[{local_version}] vs competiton[{competition_version}]"
                            )
                        else:
                            err(f"Package[{reqm}] is not in competition env")

            if not fault:
                ok("Check requirements passed! Good luck!")


if __name__ == "__main__":
    import fire
    fire.Fire(Toolkit)