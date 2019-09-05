# Contributing

Thank you for considering contributing to Dragonchain!

User feedback is critical to producing the best possible product.
Please use our
[GitHub issues](https://github.com/dragonchain/dragonchain/issues) tracker
to report bugs or request features.

We accept community contributions, but cannot accept every PR. To ensure your
changes are accepted, we recommend first creating an issue and following up
with your PR after discussing details with the team.

## Using the issue tracker

The issue tracker is the preferred channel for [bug reports](#bug-reports),
[features requests](#feature-requests) and
[submitting pull requests](#pull-requests),
but please respect the following restrictions:

- Please **do not** use the issue tracker for personal support requests (use
  [Stack Overflow](https://stackoverflow.com) or email
  support@dragonchain.com.

- Please **do not** derail or troll issues. Keep the discussion on topic and
  respect the opinions of others.

## Bug reports

A bug is a _demonstrable problem_ that is caused by the code in the repository.
Good bug reports are extremely helpful - thank you!

Guidelines for bug reports:

1. **Use the GitHub issue search** -- check if the issue has already been
   reported.

1. **Check if the issue has been fixed** -- try to reproduce it using the
   latest `master` branch in the repository.

1. **Isolate the problem** -- try as much as possible to isolate the individual
   issue that is occurring, and provide relevant details on the issue.

A good bug report shouldn't leave gaps or require others to ask for more
information. Be as detailed as possible in your report. What is your
environment? What are the steps to reproduce the issue? What runtime and OS
experience the problem? What did you expect to be the outcome? All these
details will help when we find and fix bugs.

Example:

> Short and descriptive example bug report title
>
> A summary of the issue and the OS in which it occurs. If
> suitable, include the steps required to reproduce the bug.
>
> 1. This is the first step
> 1. This is the second step
> 1. Further steps, etc.
>
> Any other information you want to share that is relevant to the issue being
> reported. This might include the lines of code that you have identified as
> causing the bug, and potential solutions (and your opinions on their
> merits).

## Feature requests

Feature requests are welcome. But take a moment to find out whether your idea
fits with the scope and aims of the project. It's up to _you_ to make a strong
case to convince the project's developers of the merits of this feature. Please
provide as much detail and context as possible.

## Pull requests

Good pull requests - patches, improvements, new features - are a fantastic
help. They should remain focused in scope and avoid containing unrelated
commits.

**Please ask first** before embarking on any significant pull request (e.g.
implementing features, refactoring code, porting to a different language),
otherwise you risk spending a lot of time working on something that the
project's developers might not want to merge into the project.

Please adhere to the [coding conventions](#coding-conventions) as best as
possible.

Follow this process if you'd like your work considered for inclusion in the
project:

1. [Fork the project](https://github.com/dragonchain/dragonchain/fork),
   clone your fork, and configure the remotes:

   ```sh
   # Clone your fork of the repo into the current directory
   git clone https://github.com/<your_github_username>/dragonchain
   # Navigate to the newly cloned directory
   cd dragonchain
   # Assign the original repo to a remote called "upstream"
   git remote add upstream https://github.com/dragonchain/dragonchain
   ```

1. If you cloned a while ago, get the latest changes from upstream:

   ```sh
   git checkout master
   git pull upstream master
   ```

1. Create a new topic branch (off the main project's master branch) to
   contain your feature, change, or fix:

   ```sh
   git checkout -b <topic-branch-name>
   ```

1. Commit your changes in logical chunks. Please adhere to good
   [git commit message guidelines](http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)
   or your code is unlikely be merged into the main project. Use Git's
   [interactive rebase](https://help.github.com/articles/interactive-rebase)
   feature to tidy up your commits before making them public.

1. Add tests and documentation for your new or changed code.

1. Update the changelog with your changes.

1. Locally merge (or rebase) the upstream development branch into your topic
   branch:

   ```sh
   git pull [--rebase] upstream master
   ```

1. Ensure that all checks pass. Running `./tools.sh full-test` from the
   root of the repository will run all PR checks locally.

1. Push your topic branch up to your fork:

   ```sh
   git push origin <topic-branch-name>
   ```

1. [Open a Pull Request](https://help.github.com/articles/using-pull-requests/)
   with a clear title and description.

## Coding Conventions

We use tools to automatically enforce general coding style/guidelines
across our codebase. These tools can be installed into python with pip using
the dev_requirements.txt file and ran using the `tools.sh` script.

These automatic linting and formatting rules do not cover all cases of styling.
When in doubt, adhere to the
[Google python style guide](https://google.github.io/styleguide/pyguide.html)
and follow the conventions of the surrounding code.

Additionally, because we use [mypy](http://mypy-lang.org/) for static python
type checking, ensure that your code has appropriate
[PEP 484](https://www.python.org/dev/peps/pep-0484/)
in-line type hints. This helps catch typing bugs and while using Python's
dynamic typing.

## License

By contributing, you agree that your contributions will be licensed under the
Apache License, Version 2.0.

## Bounty Programs

Want to make some money for helping the project?

We have project, bug, and security bounty programs which we invite anyone to participate in.
Details for these programs can be found here:

- [Bug and Security Bounty Program](https://dragonchain.com/bug-and-security-bounty)
- [Project Bounty Program](https://dragonchain.com/strategic-projects-bounty)
