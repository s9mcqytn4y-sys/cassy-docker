# CassyDocker

Standalone Docker, Nginx, PostgreSQL 18 Triple-Role, and VPS Gateway infrastructure repository for **Cassy by AzureDevID**.

## Layout (PascalCase Standard)
- `Core/`: `DockerComposeDev.yml`, `DockerComposeDemo.yml`, `DockerComposeDemoVps.yml`, `DockerComposeProd.yml`
- `VpsGateway/`: `DockerComposeVpsGateway.yml` (`CassyVpsRedis`, `CassyVpsN8n`, `CassyVpsHermesGateway` on `CassyMeshNet`)
- `Nginx/`: `Nginx.conf`, `NginxDemo.conf`, `NginxProd.conf`, `Maintenance/`
- `Postgres/`: `00-init-roles.sh` (`cassy_migrator`, `cassy_app` `NOBYPASSRLS`, `cassy_backup`)
- `Monitoring/`: Grafana Alloy config & Prometheus alert rules
- `Backup/`: Cron schedules (`CassyBackup.cron`, `CassyBackupDemo.cron`)
- `Scripts/`: `ComposeControl.ps1`

## Container & Network Naming
- Dev: `CassyPostgresDev`, `CassyApiDev`, `CassyNginxDev`, `CassyWaBridgeDev` on `CassyEdgeNet` + `CassyDataNet` (`CassyPgData`)
- Prod: `CassyPostgresProd`, `CassyRedisProd`, `CassyMigrateProd`, `CassyApiProd`, `CassyWebProd`, `CassyNginxProd`, `CassyTunnelProd`, `CassyAlloyProd`
- VPS Gateway: `CassyVpsRedis`, `CassyVpsN8n`, `CassyVpsHermesGateway` on `CassyMeshNet`
