# Agent instructions

## Writing

- Use simple, clear English in docs, comments, UI text, and project updates.
- Use short sentences and familiar words. Keep technical terms when they add precision, and explain unfamiliar terms on first use.

## README

- Treat `README.md` as the first page teammates and hackathon reviewers will read. Start with the problem, what the project does, and what works today.
- Check the README with every change. Update it in the same change when features, setup commands, prerequisites, demo steps, or project status change.
- Keep it short and verify commands before publishing. Put detailed design notes and future plans in separate docs. Label planned features clearly.

## Project scope

- Follow the agreed build plan once it exists. Keep changes within the requested scope.
- Use fictional data for the hackathon prototype. Keep credentials out of Git.
- Follow the P0 stop line in the agreed plan. Ask before starting later roadmap work or deploying to the cloud.

## Coding standards

- Follow DRY (Don't Repeat Yourself). Before writing new logic, look for an existing helper, class, or pattern in the codebase and reuse it. Do not copy and paste the same logic into more than one place.
- When the same logic is needed in two places, extract it into one shared function and call it from both.
- When you must repeat a shape because two parts stay deliberately parallel (for example, two sibling modules), keep them consistent and say why in a short comment.

## Branches and pull requests

- Before implementing a stage, create a feature branch from the latest `main`, or continue on the existing branch for that stage. Use a clear name like `feat/stage-1-1-reservations`.
- Commit and push stage changes on the feature branch. Keep direct commits and pushes to `main` out of stage work.
- Open a pull request into `main` and get a teammate to review it before merging. Include the stage number and the checks you ran.

## Git commits

- Use Conventional Commits for commits made with AI assistance. Use the format `type(scope): short summary`. The scope is optional.
- Use types such as `feat`, `fix`, `docs`, `test`, and `chore`. Write the summary as a short action.
- Example: `chore: scaffold campus asset concierge`.
- Review the staged changes before committing. Run checks that fit the change before pushing.
