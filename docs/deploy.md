# Deploying now-workbench on srv01chambly

The workbench runs as two containers on srv01chambly (the app and its dedicated tunnel) and is
reached only through Cloudflare at `workbench.grothe.ca`. Cloudflare Access signs people in with Apple or Google; the
workbench then checks their role. Design: ADR-016 (sign-in), ADR-017 (deployment and setup).

## 1. Cloudflare (done 2026-11-06)

Configured in the dashboard, isolated from the homelab apps:

- **Login methods:** Google and One-time PIN (email code). The app accepts only these two.
- **Policy "Now Workbench users":** a dedicated reusable policy (Allow, emails). It starts with
  `grothepierre@gmail.com` and `pierre@grothe.ca`. No other app uses it, and the workbench uses
  no other policy, so testers added here reach nothing else.
- **Application "Now Workbench":** self-hosted, `workbench.grothe.ca`, session 24 h. Team domain
  `dark-morning-3aea.cloudflareaccess.com`; its AUD tag is in `.env.example`.
- **Tunnel "workbench":** dedicated (the `homelab` tunnel is untouched), route
  `workbench.grothe.ca` -> `http://now-workbench:8080`. Its connector is the `cloudflared`
  container in `docker-compose.yml`.

## 2. Server (srv01chambly)

```bash
# From this repository, on your Mac
tar czf - --exclude=node_modules --exclude=.venv --exclude=data --exclude=.e2e \
    --exclude=web/dist --exclude=.git --exclude=.env . | ssh srv01chambly 'mkdir -p /opt/docker/now-workbench && tar xzf - -C /opt/docker/now-workbench'

# On srv01chambly
cd /opt/docker/now-workbench
cp .env.example .env && chmod 600 .env
nano .env            # paste the tunnel token: Networking > Tunnels > workbench > Overview
sudo cp deploy/workbench-firewall.sh /usr/local/sbin/
sudo cp deploy/workbench-firewall.service /etc/systemd/system/
docker compose up -d --build
sudo systemctl daemon-reload && sudo systemctl enable --now workbench-firewall
docker logs now-workbench   # look for FIRST-RUN SETUP CODE
```

No port opens on srv01chambly: the tunnel container reaches the workbench over the private
`br-workbench` network. The firewall rules stop that network from reaching your LAN and other
containers (DOCKER-USER: 10/8, 172.16/12, 192.168/16, link-local, CGNAT) and the host itself
(INPUT), while the internet stays reachable for Claude, ServiceNow and Cloudflare. The
containers use public DNS (1.1.1.1) because the LAN resolver is blocked. Check with
`sudo iptables -S DOCKER-USER` and `sudo iptables -S INPUT | grep br-workbench`.

### Home network DNS

The home DNS servers (BIND on the NAS) answer every `*.grothe.ca` name with srv01chambly, where
Caddy serves the homelab apps directly. The workbench must not be served that way (it would skip
Cloudflare Access, and the app refuses traffic without an Access token), so home devices must
resolve this one name the way the internet does. Preferred: a forward zone in BIND, more specific
than the wildcard, so it follows any change Cloudflare makes:

```
zone "workbench.grothe.ca" {
    type forward;
    forward only;
    forwarders { 1.1.1.1; 1.0.0.1; };
};
```

Simpler but static: `workbench IN A 172.64.80.1` and
`workbench IN AAAA 2606:4700:130:436c:6f75:6466:6c61:7265` (Cloudflare's addresses for the zone
on 2026-11-06; update them if Cloudflare changes them).

Outside users are unaffected; without it, devices at home get a TLS error for this name.

## 3. First run

Open `https://workbench.grothe.ca`, sign in with Google or an email code, and enter the setup
code from the log in the dialog. You become **Administrator** and **Solution Consultant**. Then:

- **Claude API key:** either put it in `/opt/docker/now-workbench/.env` as
  `WORKBENCH_ANTHROPIC_API_KEY=...` and run `docker compose up -d` (it then wins and shows
  read-only in Settings), or paste it in **Settings > Claude and Otto** (stored encrypted).
- **Settings > ServiceNow instances:** register your instances (passwords stored encrypted).

Five wrong codes replace the code with a new one in the log; restarting the container before
setup also prints a new one. Once an administrator exists there is no setup code any more.

## Adding a tester

Two places, both needed:

1. Cloudflare: Access controls > Policies > **Now Workbench users** > add their email. They can
   sign in with Google or with an email code.
2. Workbench: Settings > **Team** > add the same email, role **Solution Consultant** (they can
   use Otto, synthesis and capture, but cannot see or change credentials or the Claude key).

Testers use your Claude key; their usage is billed to your account.

## Secrets and backups

| What | Where | Back up with |
| --- | --- | --- |
| Database (instances, sealed passwords and Claude key, team, conversations) | volume `workbench-data` | `docker exec now-workbench workbench backup > workbench-$(date +%F).db` |
| Master key (decrypts the sealed values) | volume `workbench-keys` | `docker run --rm -v now-workbench_workbench-keys:/k:ro busybox cat /k/master.key` into your password manager, once |
| Bundles you created | volume `workbench-bundles` | `docker run --rm -v now-workbench_workbench-bundles:/b:ro busybox tar cz -C /b . > bundles.tgz` |

Keep the key and the database backups apart: either one alone reveals no credential. Losing
the key makes the stored passwords and Claude key unrecoverable (re-enter them in the UI).

### Off-site backups to S3 (optional)

Fill the `WORKBENCH_BACKUP_S3_*` lines in `.env` (bucket, region, endpoint for R2/MinIO/B2,
prefix, access key and its secret), run `docker compose up -d`, then:

```bash
docker exec now-workbench workbench backup --s3
# Backup uploaded: s3://<bucket>/now-workbench/workbench-20261107T020000Z.db (... bytes)
```

Use a key that can write to that bucket only, and keep the master key out of the bucket.
Expire old snapshots with a bucket lifecycle rule; the workbench never deletes. To run it
nightly, add a host cron entry, for example
`0 2 * * * docker exec now-workbench workbench backup --s3 >> ~/workbench-backup.log 2>&1`.

Telemetry (Claude usage and action runs) is purged after `WORKBENCH_TELEMETRY_RETENTION_DAYS`
(365 by default, at least 60), at startup and every day.

## Updating

Copy the new source as in step 2 (it never overwrites `.env`), then `docker compose up -d --build`. Volumes are kept, and
schema migrations run at startup.
