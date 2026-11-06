# Deploying now-workbench on srv01chambly

The workbench runs as one container on srv01chambly and is reached only through Cloudflare at
`workbench.<your-domain>`. Cloudflare Access signs people in with Apple or Google; the
workbench then checks their role. Design: ADR-016 (sign-in), ADR-017 (deployment and setup).

## 1. Cloudflare (dashboard)

1. **Zero Trust > Settings > Authentication:** add **Google** and **Apple** as login methods.
2. **Access > Applications > Add > Self-hosted:** domain `workbench.<your-domain>`. Policy:
   *Allow*, include the emails of the people who should reach it (you first). Save, then copy
   the application's **AUD tag**. Your team domain is `<team>.cloudflareaccess.com`.
3. **Networks > Tunnels:** in the tunnel srv01chambly already runs, add a **public hostname**
   `workbench.<your-domain>` with service `http://localhost:8080`.
   If cloudflared runs as a container rather than on the host, `localhost` is the cloudflared
   container itself: put both containers on one Docker network and use
   `http://now-workbench:8080` instead.

## 2. Server

```bash
# From this repository, on your Mac
tar czf - --exclude=node_modules --exclude=.venv --exclude=data --exclude=.e2e \
    --exclude=web/dist --exclude=.git . | ssh srv01chambly 'mkdir -p /opt/docker/now-workbench && tar xzf - -C /opt/docker/now-workbench'

# On srv01chambly
cd /opt/docker/now-workbench
cp .env.example .env && nano .env      # team domain + AUD tag
docker compose up -d --build
docker logs now-workbench               # look for FIRST-RUN SETUP CODE
```

The container refuses to start if the two Access values are missing.

## 3. First run

Open `https://workbench.<your-domain>`, sign in with Apple or Google, and enter the setup code
from the log in the dialog. You become **Administrator** and **Solution Consultant**. Then:

- **Settings > Claude and Otto:** paste the Claude API key (stored encrypted, never in files).
- **Settings > ServiceNow instances:** register your instances (passwords stored encrypted).
- **Settings > Team:** add the other people and their roles. Use the email their Apple or Google
  account reports to Cloudflare (Apple "Hide My Email" gives a relay address). Also add them
  to the Access policy, or Cloudflare will not let them reach the page.

Five wrong codes replace the code with a new one in the log; restarting the container before
setup also prints a new one. Once an administrator exists there is no setup code any more.

## Secrets and backups

| What | Where | Back up with |
| --- | --- | --- |
| Database (instances, sealed passwords and Claude key, team, conversations) | volume `workbench-data` | `docker exec now-workbench workbench backup > workbench-$(date +%F).db` |
| Master key (decrypts the sealed values) | volume `workbench-keys` | `docker run --rm -v now-workbench_workbench-keys:/k:ro busybox cat /k/master.key` into your password manager, once |
| Bundles you created | volume `workbench-bundles` | `docker run --rm -v now-workbench_workbench-bundles:/b:ro busybox tar cz -C /b . > bundles.tgz` |

Keep the key and the database backups apart: either one alone reveals no credential. Losing
the key makes the stored passwords and Claude key unrecoverable (re-enter them in the UI).

## Updating

Copy the new source as in step 2, then `docker compose up -d --build`. Volumes are kept, and
schema migrations run at startup.
