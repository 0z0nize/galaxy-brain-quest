# galaxy-brain-quest

A small automation playground for the **GitHub Galaxy Brain achievement**.

> ⚠️ Educational / personal-use only. This script is meant for unlocking
> the achievement on **your own** profile, in a repository **you own**,
> with the help of a **second account you control**. Do not use it to
> spam discussions in other people's projects — GitHub treats automated
> activity in third-party repositories as abuse.

## What is Galaxy Brain?

Galaxy Brain is a profile badge awarded for having your answers accepted
in GitHub Discussions. The community-observed tiers are:

| Tier    | Accepted answers |
| ------- | ---------------- |
| Default | 2                |
| Bronze  | 8                |
| Silver  | 16               |
| Gold    | 32               |

GitHub does not publish the exact thresholds officially — the feature is
still flagged as public preview in the
[Profile reference docs](https://docs.github.com/en/enterprise-cloud@latest/account-and-profile/reference/profile-reference#earning-achievements).

A key rule: **the answer must be marked as accepted by someone other
than the author of the answer.** That is why a second (helper) account
is required.

## How `galaxy_brain.py` works

The script automates one Q&A cycle per iteration:

1. **Helper account** creates a Q&A discussion in the target repository.
2. **Main account** (the one that should earn the achievement) posts an
   answer via the locally authenticated `gh` CLI.
3. **Helper account** marks that answer as the accepted answer.

Each successful iteration adds **one** accepted answer to the main
account's Galaxy Brain counter. Running with `TARGET_COUNT=32` gets you
all the way to Gold.

## Prerequisites

- Python 3.9+ (uses only the standard library).
- [`gh` CLI](https://cli.github.com/) installed and authenticated as the
  **main account** (the one that will earn the achievement).
- A second GitHub account ("helper") added as a **collaborator** on the
  target repository with at least `push` permission.
- A **Personal Access Token** for the helper account with these scopes:
  - `repo`
  - `write:discussion`
  - `read:discussion`
- The target repository must be:
  - **public** (private contributions only count toward achievements if
    you explicitly opt in under Settings → Public profile),
  - have **Discussions enabled**,
  - contain a category with the slug `q-a` (the default Q&A category).

## Configuration

The script reads its configuration from environment variables:

| Variable        | Required | Description                                                   |
| --------------- | :------: | ------------------------------------------------------------- |
| `HELPER_TOKEN`  |    ✅    | Personal Access Token of the helper account.                  |
| `REPO_OWNER`    |    ✅    | Owner login of the target repository (e.g. `0z0nize`).        |
| `REPO_NAME`     |    ✅    | Repository name (e.g. `galaxy-brain-quest`).                  |
| `TARGET_COUNT`  |    ❌    | How many accepted answers to generate. Default: `32` (Gold).  |

The repository node ID and the Q&A category ID are discovered
automatically through the GraphQL API.

## Usage

```bash
# 1. Authenticate the gh CLI as the MAIN account once.
gh auth login

# 2. Export the helper token and target repo.
export HELPER_TOKEN=ghp_your_helper_token
export REPO_OWNER=your-username
export REPO_NAME=galaxy-brain-quest
export TARGET_COUNT=32

# 3. Run the script.
python3 galaxy_brain.py
```

Expected output:

```
Target: 32 accepted answers in your-username/galaxy-brain-quest
Repository node ID: R_kgDO...
Q&A category ID:    DIC_kw...
# 1  accepted   (1/32)
# 2  accepted   (2/32)
...
#32  accepted   (32/32)

Done: 32/32 accepted answers.
```

The Galaxy Brain badge typically appears on your profile within a few
hours, but GitHub may take up to ~24 hours to re-index achievements.

## Question pool

The script ships with 32 ML / NLP themed seed topics inside `TOPICS`.
Each iteration cycles through them and appends a unique numeric suffix
to the discussion title so every question is distinct. You can edit
`TOPICS` and `ANSWER_TEMPLATE` to use questions and answers from your
own domain — the badge mechanics are identical.

## Safety notes

- **Never commit your `HELPER_TOKEN`.** It is read from the environment
  on purpose. Revoke it on
  [github.com/settings/tokens](https://github.com/settings/tokens) once
  you are done.
- **Use your own repository.** GitHub explicitly considers third-party
  spam (creating noise in repositories you don't own) abusive behavior.
- The achievement feature is in public preview. GitHub may change the
  thresholds, retroactively revoke badges, or update its anti-abuse
  policies at any time.

## License

MIT — do whatever you want, at your own risk.
