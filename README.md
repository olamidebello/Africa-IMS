# AIMS — Africa Identity Management System

**One Identity. A World of Possibilities.**

Original multi-tenant identity intake and case-management platform for `identity.africandroid.world`. The requested `jobs.africandroid.world` deployment conflicts with Africa Jobs; this playbook explicitly protects that host.

## Included

User registration and login; service catalog; draft/save/submit applications; PDF/image uploads; tracking and review timeline; record correction/copy and appeal intake; appointments and cancellation; secure support messages; password change; operator password recovery. Staff review queues, reasons and evidence requests; tenant admin staff management, role updates and audit view; super admin tenant creation and workspace switching. Separate person accounts, applications, evidence, appointments, decisions/status and audit records. Tenant authorization is enforced in database queries, not just navigation.

Eleven configurable intake services cover identity, SS-5 support, benefits, naturalization, birth, marriage, death, passport, corrections, copies, and appeals. These are summarized intake schemas, **not complete official government forms**. No agency integration, government issuance, benefit payment, background check, biometrics, payment processing, or Field Nation marketplace/payment functionality is claimed. Real agency submission, form-edition validation and authorized signing remain future integrations. The Android app is a signed browser launcher, not a native offline identity application.

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
AIMS_SECURE=0 .venv/bin/python scripts/admin.py create
AIMS_SECURE=0 .venv/bin/python app.py
```

Visit http://127.0.0.1:18840. No default administrator password is committed. Use the operator command to create one. `scripts/admin.py reset` recovers an account via a trusted shell. Self-service email recovery requires a configured, verified mail provider and is not enabled.

## Deploy to Olamidepanel

Set DNS A for `identity.africandroid.world` to the hosting server's IPv4 address. Remove conflicting AAAA if IPv6 is not served. On the server:

```bash
git clone https://github.com/olamidebello/Africa-IMS.git /opt/aims
cd /opt/aims
ansible-playbook -i localhost, -c local ansible/deploy.yml
sudo -u aims env AIMS_DATA=/var/lib/aims /opt/aims/.venv/bin/python /opt/aims/scripts/admin.py create
```

AIMS binds loopback port 18840. HTTPS is required for secure cookies. The playbook preserves existing virtual hosts and issued certificate configuration on rerun. Certbot must succeed before public sign-in works. Service data lives outside the checkout in `/var/lib/aims`. Back up this directory encrypted, including the session key. Test restores and configure retention, privacy contacts and incident handling before accepting real sensitive identity records. Uploaded documents are permission-protected, not encrypted at rest by this application; use host disk encryption and encrypted backups. Malware scanning and third-party verification are not yet connected.

## Android and store

1. Generate a private Android release keystore outside Git. Preserve it securely for updates.
2. Configure GitHub Actions secrets: `AIMS_KEYSTORE_BASE64`, `AIMS_STORE_PASSWORD`, `AIMS_KEY_ALIAS`, `AIMS_KEY_PASSWORD`.
3. Run **Build AIMS Android**. It builds with SDK 35 and publishes a signed APK as a repository release.
4. Download the release to the host and run `scripts/publish-apk.sh signed-AIMS.apk /actual/store/catalog.json /actual/store/downloads` after confirming the store uses the supported `apps` array schema.
5. `/download` serves the APK only after publication. Until then the UI explicitly reports that the release is pending.

The store filesystem and credentials have not been assumed. No automatic catalog write happens until the operator provides real paths and a signed artifact.

## Validation

`python -m unittest discover -s tests -v` checks tenant isolation, role boundaries, CSRF, upload access, and application transitions. `node --check static/app.js` verifies JavaScript syntax. Production hosting, DNS/TLS, Android signing and store publication require their respective live environments.
