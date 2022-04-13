![ijcai2022nmmo-banner](https://i.ibb.co/9pPdQT6/NMMO-KV-LOGO.jpg )

# Table of contents
- [Competition procedure](#competition-procedure)
- [Quick start](#quick-start)
    * [Install](#install)
    * [Make your first submission](#make-your-first-submission)
- [Submit your own agents](#submit-your-own-agents)
    * [Repository structure](#1-repository-structure)
    * [Custom runtime configuration](#2-custome-runtime-configuration)
    * [Implement `submission.py`](#3-implement-submissionpy)
    * [Submit](#4-submit)
- [Baseline](#baselines)
- [Local Evaluation](#local-evaluation)
- [Important links](#important-links)
- [Contributors](#contributors)


# Competition procedure

The Neural MMO Challenge is an opportunity for researchers and machine learning enthusiasts to test their skills by designing and building agents that can survive and thrive together in a massively multiagent environment full of potential adversaries.

In this challenge, you will train your models locally and then upload them to AIcrowd (via git) to be evaluated.

**The following is a high level description of how this process works.**

![procedure](https://www.linkpicture.com/q/IJCAI-2022-NMMO-userflow-1.png)

1. **Sign up** to join the competition [on the AIcrowd website](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge) and click [**Participate**](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge) on the homepage.
2. **Clone** this repo and start developing your solution.
3. **Design and build** your agents that can compete in Neural MMO environment and create your submission as described in [Make your own submission](#make-your-own-submission) section.
4. [**Submit**](#-submission) your agents to [AIcrowd Gitlab](https://gitlab.aicrowd.com) for evaluation.


# Quick Start

## Install

Clone this starter kit repository.

```bash
git clone http://gitlab.aicrowd.com/neural-mmo/ijcai2022-nmmo-starter-kit.git
conda create -n ijcai2022-nmmo python==3.9
conda activate ijcai2022-nmmo
cd ./ijcai2022-nmmo-starter-kit
```

Install necessary dependencies, `git-lfs` is for submitting large files by git (use `brew` for mac users) and `ijcai2022nmmo` is a Neural MMO environment wrapper prepared for IJCAI 2022 Competition.

```
apt install git-lfs
pip install git+https://github.com/IJCAI2022-NMMO/ijcai2022nmmo.git
pip install -r requirements_tool.txt
```

### Make your first submission

```bash
python tool.py submit "my-first-submission"
```
See your submission on [Submissions](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge/submissions) and 
check your rank on [Leaderboard](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge/leaderboards) in a few minutes.

# Submit your own agents

### 1. Repository structure

```
- my-submission/            # Directory containing your submission.
    | - submission.py       # Entrypoint of your submission.
- submission-runtime        # Directory containing default Dockerfile and requirements.txt. 
- Dokcerfile                # Dockerfile for your submission. 
- requirements.txt          # Python requirements for your submission.
- .submit.sh                # Hepler script for submit.
- tool.py                   # Hepler script for validate locally and submit.
- aicrowd.json              # Json for submit.
```
### 2. Custome runtime configuration
The default runtime is provided in `submission-runtime/`. We also accept submissions with custom runtimes. The configuration files include `requirements.txt` and `Dockerfile`.

### 3. Implement `submission.py`

Here is an example of submission:
```python
from nmmo.io import action

from ijcai2022nmmo import Team

class YourTeam(Team):
    def __init__(self, team_id: str, config=None, **kwargs):

    def act(self, observations):
        actions = {}
        for player_idx, obs in observations.items():
            actions[player_idx] = {}
        return actions

class Submission:
    team_klass = YourTeam
    init_params = {}
```

Note that [`YourTeam`]() class which must inherit [`Team`]() class and [`act`]() method should be implemented and we will call the function `act` for evaluation. An example with random agents is provided in `my-submission/submission.py` for your reference.

### 4. Validate locally and Submit to AICrowd

We provide `tool.py` to validate and submit your submission.

1. To locally validate your repo before submission.
```bash
python tool.py test
```

2. To submit your submission to AIcrowd gitlab.

```bash
python tool.py submit <unique-submission-name>
```

<!-- The `startby` parameter determines how to validate your submission locally
-  `--startby=process`: check your submission in *process* mode.
-  `--startby=docker`: check your submission in *docker* mode. -->

<!-- We strongly recommend that you use *docker* mode to validate your submission, as this is the mode used on the competition server. -->

Note that if your submission passes the local test but fail to submit, it is most likely that the local enviornment does not match the `dockerfile`. Please test and submit in *docker* mode.

```bash
python tool.py test --startby=docker
```

or

```bash
python tool.py submit <unique-submission-name> --startby=docker
```

If you can see the following output, congratulations! Now you can check your submission.

``` bash
          #///(            )///#
         ////      ///      ////
        /////   //////////   ////
        /////////////////////////
     /// /////////////////////// ///
   ///////////////////////////////////
  /////////////////////////////////////
    )////////////////////////////////(
     /////                      /////
   (///////   ///       ///    //////)
  ///////////    ///////     //////////
(///////////////////////////////////////)
          /////           /////
            /////////////////
               ///////////
```
# Baselines

We provide a variety of baseline agents, please refer to [ijcai2022-nmmo-baselines](https://gitlab.aicrowd.com/neural-mmo/ijcai2022-nmmo-baselines) repository.


# Local evaluation
To do local evaluation, we provide `Rollout` for easier debug, here is an example. The environment is same with the online evaluation environment in PvE Stage 1.

```python
class YourTeam(Team):
    def act(self, observations):
        actions = {}
        for player_idx, obs in observations.items():
            actions[player_idx] = {}
        return actions


def local_evalution():
    config = CompetitionConfig()
    your_team = YourTeam(team_id="my_team", env_config=config)
    all_teams = [scripted.CombatTeam(f"combat-{i}", config) for i in range(3)] + \
        [scripted.ForageTeam(f"forage-{i}", config) for i in range(5)] + \
        [scripted.RandomTeam(f"random-{i}", config) for i in range(7)] + \
        [your_team]
    ro = RollOut(config, all_teams, True)
    ro.run()
```

# FAQ

#### 1. Are there any hardware or time constraints?

During evaluation, your submission will be allocated with **1 CPU core and 1G memory**. Each step, your Agent Team must give decision within **600ms**.

#### 2. Are there any file size limit for submission?

Your submission should not be larger than 300MB.

#### 4. How can I speed up docker image pull?

For participants in China, you can pull image from tencentcloud
```bash
python tool.py submit <unique-submission-name> --startby=docker --registry=tencentcloud
```

#### 5. How do windows users participate the competition?

For participants using windows, we strongly recommend you to install `wsl`.

#### 6. How can I render/save replay locally?

Please refer to [Neural MMO Environment Tutorial](https://www.aicrowd.com/showcase/neural-mmo-environment-tutorial) for an instruction about how to render locally.

#### 5. `Error: Pack Exceeds Maximum Allowed Size`?

Try dividing your whole commit into multiple smaller commits.




# Important links

- Challenge information
   * [Challenge page](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge)
   * [Leaderboard](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge/leaderboards)
 - Community
    * [Neural MMO discord server](https://discord.gg/neX6e4Kc)
    * [Challenge discussion forum](https://www.aicrowd.com/challenges/ijcai-2022-the-neural-mmo-challenge/discussion)
    * QQ群号: 1011878149
- Neural MMO resources
    * [Neural MMO documentation](https://neuralmmo.github.io/build/html/rst/landing.html)
    * [Neural MMO GitHub repository](https://github.com/NeuralMMO/environment/tree/ijcai-competition)
    * [Neural MMO Environment Tutorial](https://www.aicrowd.com/showcase/neural-mmo-environment-tutorial)
    

# Contributors
- Parametrix.ai
- Joseph Suarez
- AIcrowd




