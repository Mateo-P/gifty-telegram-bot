# gifty-telegram-bot

This is the gifty telegram bot.

## Development

### Local Setup

You'll need the following installed on your machine:

- docker
- git-lfs
- python 3.11
- poetry 1.8


Install python dependencies: `poetry install`

Add package to project: `poetry install <package_name>`

Copy .env: `cp .env.example .env`

(Ask a team member for .env variables for now. replacement is TBD)

Setup pre-commit: `pre-commit install`

### Docker Setup

**If building on arm64 architecture (eg. Apple M1), set `export DOCKER_DEFAULT_PLATFORM=linux/amd64`**
- `docker compose build`

Run the api: `docker compose up -d`

Remember to run `docker compose down` if you make any changes to compose, deps,
docker, or env files.


### Linting

`pre-commit run --all-files`

(`pre-commit` should be installed at the user level rather than in the project,
so `poetry run` isn't necessary)

To update the packages used by pre-commit:
`pre-commit autoupdate`
