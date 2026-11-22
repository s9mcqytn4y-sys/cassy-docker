# CassyDocker Agent Instructions

Single source of agent instructions for `s9mcqytn4y-sys/cassy-docker` (`C:\Projects\CassyWorkspace\Docker`). `CLAUDE.md` and `GEMINI.md` import this file.

## Scope

Infrastructure-only repository for **Cassy by AzureDevID**: Docker Compose stacks (`Core/`), Nginx reverse proxies & maintenance pages (`Nginx/`), PostgreSQL 18 triple-role initialization (`Postgres/`), Prometheus/Grafana Alloy rules (`Monitoring/`), offsite backup cron (`Backup/`), and standalone Hostinger VPS Gateway services (`VpsGateway/`).

Application source code does NOT live here: Go backend lives in `CassyBackend`, and Web/Android/iOS clients live in `CassyClient`.

## Non-Negotiable Rules

- **Naming convention**: Directory, documentation, and script filenames strictly use `PascalCase` (`DockerComposeDev.yml`, `ReadmeVpsGateway.md`, `InitCassyRoles.sh`, `ComposeControl.ps1`), except standard entry dotfiles (`.gitignore`, `.editorconfig`, `.gitattributes`) and upstream config identifiers (`alert-rules.yml`, `config.alloy`).
- **Formatting**: Shell scripts (`*.sh`) must use `2` spaces and `LF` line endings with `set -eu`; PowerShell (`*.ps1`) uses `Verb-Noun` `PascalCase` functions (`4` spaces, UTF-8, `camelCase` locals); YAML/Compose/Markdown use `2` spaces and `LF`.
- **Least-privilege DB roles**: PostgreSQL runtime always runs via non-owner `cassy_app` (`NOBYPASSRLS`). Never weaken `Postgres/InitCassyRoles.sh` to grant superuser or `BYPASSRLS`.
- **Network isolation**: Keep local development and VPS Gateway subnets isolated (`CassyEdgeNet`, `CassyDataNet`, `CassyMeshNet` on `172.29.20.0/24`) so they never collide with SaaS containers or local workstation ports.
- **No secrets in git**: Never commit `.env`, `.env.vps-gateway`, certificates, or API tokens.
- **Active demo domains**: Live demo runs on `https://pos.abbdullaziz.online` (PWA + Nginx proxy) and `https://api.abbdullaziz.online` (API); `demo.abbdullaziz.online` is retired. Ensure only one Cloudflare tunnel connector is active (`cassy-demo-tunnel-1`, with Windows `Cloudflared` service stopped/manual).
- **No emoji or em dash**: Keep docs, compose comments, and CI logs clean.

## Verification Before Commit

```bash
docker compose -f Core/DockerComposeDev.yml config -q
docker compose -f Core/DockerComposeDemo.yml config -q
docker compose -f Core/DockerComposeProd.yml config -q
docker compose -f Core/DockerComposeProd.yml -f Core/DockerComposeDemoVps.yml config -q
sh -n Postgres/InitCassyRoles.sh
```
