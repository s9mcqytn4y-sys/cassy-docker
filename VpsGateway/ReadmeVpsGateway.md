# Hostinger VPS 24/7 Gateway + Tailscale + Cloudflare Tunnel Guide

Stack ini memisahkan jalur runtime agar demo/staging Cassy tidak mati saat laptop Windows 11 dimatikan (`HTTP 530` dari Cloudflare Tunnel).

## 1. Alokasi Port Anti-Bentrok (Windows 11 + VPS)
| Komponen | Port | Binding | Catatan |
|---|---|---|---|
| Cassy Go API (`CassyBackend`) | `8080` | `127.0.0.1` | Diproksi Caddy / Nginx / Cloudflare Tunnel |
| Cassy WhatsApp Bridge | `8090` | `127.0.0.1` | Internal API only |
| Cassy Web PWA (`Next.js`) | `3000` | `127.0.0.1` | Diproksi Caddy / Nginx |
| Redis 8 (Auth + `/r/{shortCode}`) | `6379` | `127.0.0.1` | Jangan pernah expose ke `0.0.0.0` |
| Hermes Proxy / API Server | `8642` | `127.0.0.1` | Bebas bentrok dengan SaaS ports |
| Hermes Dashboard Web | `9119` | `127.0.0.1` | Akses via Tailscale SSH/tunnel |
| n8n Workflow Engine | `5678` | `127.0.0.1` | Webhook SCAMPER & CI digest |
| Local Ollama (Windows 11) | `11434` | `127.0.0.1` | Model offline `qwen3:1.7b` |

## 2. Langkah Deploy Hostinger VPS
1. Buat `.env.vps-gateway` dari `.env` lokal Anda (`N8N_ENCRYPTION_KEY`, router API keys, `WHATSAPP_ENABLED`, dll. Jangan pernah commit berkas `.env*`).
2. Hubungkan Windows 11 dan Hostinger VPS via Tailscale mesh (`tailscale up --ssh`).
3. Jalankan stack gateway:
   ```bash
   docker compose -f docker-compose.vps-gateway.yml --env-file .env.vps-gateway up -d
   ```
4. Arahkan `cloudflared` tunnel di VPS ke `http://127.0.0.1:8080` (`/api/*`) dan `http://127.0.0.1:3000` (`/*`) sehingga `demo.abbdullaziz.online` aktif 24/7 dan `VARS.VPS_STRICT_UPTIME=true` bisa diaktifkan di GitHub Actions.

## 3. SCAMPER `/agentflow` Cron Hooks
- **S (CI Failure Digest)**: Hermes memantau `gh run list --status failure` tiap jam dan meringkas root cause via Groq/Cerebras gratis.
- **C (Release Pipeline)**: Webhook `n8n` menerima event merge PR `CassyClient`, mengambil screenshot `ui-v2.5.0`, dan menyiapkan checklist ASO Google Play.
- **P (Nightly Audit)**: Hermes menjalankan audit `values/strings.xml` + `values-en/strings.xml` dan `tokens:verify` secara terjadwal lewat chain 9-router fallback.
- **R (Slow Query Feedback Loop)**: Alert error `5xx` atau query Postgres > 200ms otomatis membuka draft branch diagnostik read-only.
