#!/bin/sh
''''exec python -u "$0" ${1+"$@"} # '''

import os
import sys
import time
import json
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
TENCENTCLOUD_REGISTRY = "ccr.ccs.tencentyun.com"


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


def run_submission_in_docker(submission_path, registry):
    if registry not in ["dockerhub", "tencentcloud"]:
        err(f"Invalid registry {registry}")
        sys.exit(6)
    ok(f"Use docker registry [{registry}]")

    need_root = True if os.system("docker ps 1>/dev/null 2>&1") else False

    def _shell(command, capture_output=True, print_command=True):
        if command.startswith("docker") and need_root:
            command = "sudo " + command
        if print_command:
            print(command)
        r = subprocess.run(command, shell=True, capture_output=capture_output)
        if not capture_output: return r.returncode
        if r.returncode != 0:
            # grep return 1 when no lines matching
            if r.returncode == 1 and "grep" in command:
                pass
            else:
                raise CalledProcessError(r.returncode, r.args, r.stdout,
                                         r.stderr)
        return r.stdout.decode().strip()

    # check if should pull manually
    manual_pull = False
    if registry != "dockerhub":
        with open("Dockerfile", "r") as fp:
            lines = fp.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith(
                        "FROM") and line.split()[-1] == f"{IMAGE}:latest":
                    manual_pull = True
                    break

    if manual_pull:
        if registry == "tencentcloud":
            ok(f"Try pull image from {TENCENTCLOUD_REGISTRY}")
            if _shell(f"docker pull {TENCENTCLOUD_REGISTRY}/{IMAGE}:latest",
                      capture_output=False):
                err(f"Pull image failed.")
                sys.exit(10)
            _shell(
                f"docker tag {TENCENTCLOUD_REGISTRY}/{IMAGE}:latest {IMAGE}:latest",
                capture_output=False)
            manual_pull = True
        else:
            assert 0, f"Invalid registry {registry}"

    ok(f"Try build image {IMAGE}:local ...")
    if manual_pull:
        if _shell(f"docker build -t {IMAGE}:local -f Dockerfile .",
                  capture_output=False):
            err("Build failed.")
            sys.exit(10)
    else:
        if _shell(f"docker build --pull -t {IMAGE}:local -f Dockerfile .",
                  capture_output=False):
            err("Build failed.")
            sys.exit(10)
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


def rollout(submission_path: str, startby: Optional[str], registry: str):
    from ijcai2022nmmo import CompetitionConfig

    class Config(CompetitionConfig):
        PATH_MAPS = 'maps/medium/evaluation'

    if startby:
        if startby == "docker":
            ok(f"Try run submission in docker container ...")
            container_id = run_submission_in_docker(submission_path, registry)
            ok(f"Submission is running in container {container_id}")
        elif startby == "process":
            ok(f"Try run submission in subprocess ...")
            p = run_submission_in_process(submission_path)
            ok(f"Submission is running in process {p.pid}")
        else:
            err(f"startby should be either docker or process")
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
        ro.run()
    except:
        raise
    finally:
        if startby:
            team.stop()


class Toolkit:
    def test(
        self,
        startby: Optional[str] = None,
        registry: str = "dockerhub",
    ):
        assert startby is None or isinstance(startby, str)
        assert isinstance(registry, str)

        submission = "my-submission"
        try:
            subm.check(submission)
        except Exception as e:
            traceback.print_exc()
            err(str(e))
            sys.exit(5)
        ok(f"Testing {submission} ...")

        from art import text2art
        try:
            rollout(submission, startby, registry)
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

    def check_aicrowd_json(self):
        with open("aicrowd.json", "r") as fp:
            config: dict = json.load(fp)

        if config.get("challenge_id") != "ijcai-2022-the-neural-mmo-challenge":
            err(f"[challenge_id] in aicrowd.json should be ijcai-2022-the-neural-mmo-challenge"
                )
            sys.exit(3)

        if not config.get("authors"):
            err(f'[authors] in aicrowd.json should be set as aicrowd username(s). Like ["tomz", "maryz"]'
                )
            sys.exit(4)

    def aicrowd_setup(self):
        from aicrowd.contexts.config import CLIConfig
        c = CLIConfig()
        c.load(None)
        if not c.get("aicrowd_api_key"):
            warn("AICrowd config not found. Trying ``aicrowd login``.")
            r = subprocess.run("aicrowd login",
                               shell=True,
                               capture_output=False)
            if r.returncode:
                err("aicrowd_setup failed.")
        ok("aicrowd_setup done.")

    def submit(
        self,
        submission_id,
        skip_test: bool = False,
        startby: Optional[str] = None,
        registry: str = "dockerhub",
    ):
        assert isinstance(skip_test, bool)
        assert startby is None or isinstance(startby, str)
        assert isinstance(registry, str)

        self.aicrowd_setup()

        self.check_aicrowd_json()

        if not skip_test:
            self.test(startby, registry)

        r = subprocess.run(f"bash .submit.sh '{submission_id}'",
                           shell=True,
                           capture_output=False)
        if r.returncode:
            err("bash .submit.sh failed.")
            sys.exit(1)


if __name__ == "__main__":
    import fire
    fire.Fire(Toolkit)
