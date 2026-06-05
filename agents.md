# Agent Instructions

> [!IMPORTANT]
> Whenever you need to commit changes in this repository, **DO NOT** use standard `git commit` commands directly.
> You must always use the custom commit script [commit.sh](file:///Users/salauddin/Projects/workspace/assessments/Virtual-Tumor-Board/commit.sh) located in the root directory.

## Git Repository Initialization
The repository is initialized with `git init`. If for any reason the repository needs to be re-initialized:
```bash
git init
```

## How to Commit Changes

The script [commit.sh](file:///Users/salauddin/Projects/workspace/assessments/Virtual-Tumor-Board/commit.sh) automatically stages all files (`git add .`), configures the required author identity, performs the commit, and then restores the original author configuration.

To commit, run the script from the root directory with your commit message as an argument:

```bash
./commit.sh "your commit message"
```

If you do not provide a commit message, it will default to `"chore: commit by reddirani"`.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
