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

Production AIMS uses the dedicated Unix socket `/run/aims/aims.sock`; local development uses port 18840. HTTPS is required for secure cookies. The playbook preserves existing virtual hosts and issued certificate configuration on rerun. Certbot must succeed before public sign-in works. Service data lives outside the checkout in `/var/lib/aims`. Back up this directory encrypted, including the session key. Test restores and configure retention, privacy contacts and incident handling before accepting real sensitive identity records. Uploaded documents are permission-protected, not encrypted at rest by this application; use host disk encryption and encrypted backups. Malware scanning and third-party verification are not yet connected.

## Android and store

1. Generate a private Android release keystore outside Git. Preserve it securely for updates.
2. Configure GitHub Actions secrets: `AIMS_KEYSTORE_BASE64`, `AIMS_STORE_PASSWORD`, `AIMS_KEY_ALIAS`, `AIMS_KEY_PASSWORD`.
3. Run **Build AIMS Android**. It builds with SDK 35 and publishes a signed APK as a repository release.
4. Download the release to the host and run `scripts/publish-apk.sh signed-AIMS.apk /actual/store/catalog.json /actual/store/downloads` after confirming the store uses the supported `apps` array schema.
5. `/download` serves the APK only after publication. Until then the UI explicitly reports that the release is pending.

The store filesystem and credentials have not been assumed. No automatic catalog write happens until the operator provides real paths and a signed artifact.

## Validation

`python -m unittest discover -s tests -v` checks tenant isolation, role boundaries, CSRF, upload access, and application transitions. `node --check static/app.js` verifies JavaScript syntax. Production hosting, DNS/TLS, Android signing and store publication require their respective live environments.


## Languages and currencies

The **Language & currency** navigation is available to guests, users and administrators. New accounts and fresh browsers default to Nigerian Pidgin (`pcm`) and proposed Afira (`AFR`, `Ⱥ`, 100 cents per unit). Signed-in preferences persist per user in the database; guest preferences persist in browser storage. Existing databases receive an additive, idempotent column migration.

`static/regions.json` contains 175 African language/community language choices and 47 currency options, including current African national/shared currencies, selected territory currencies and Afira. This expandable catalog is not an exhaustive census of Africa’s thousands of languages. Pidgin translates core navigation, common actions, fields and messages; English is available. Other language choices explicitly use English fallback until reviewed translations are supplied. Detailed help, some errors and legal content remain English. No external translation service receives identity records.

Afira: **Ah-FEE-rah**, **One Africa. Shared Prosperity.** Proposed platform currency; not an ISO-issued legal tender designation. Preview: `Ⱥ10 · Ⱥ250 · Ⱥ1,000`. Selecting currency does not convert amounts, invent exchange rates or activate payments. Currency metadata reference: ISO 4217 maintenance agency SIX (https://www.six-group.com/en/products-services/financial-information/data-standards.html). Current codes include SLE, MRU, STN and ZWG. `AIMSLocale.formatMoney()` applies catalog precision, including zero-decimal and three-decimal currencies.


### Repair an HTTP 401 readiness response on port 18840

A 401 response from a `BaseHTTP` server does not match this Flask/Gunicorn application's unauthenticated `/api/health` endpoint. Another process or an older service may own that port. The deployment now binds AIMS to a dedicated systemd runtime socket, updates only the AIMS Nginx upstream while retaining certificates, and verifies both HTTP 200 and the `AIMS` service identity. It does not stop or kill an unrelated listener on 18840. On failure it prints service status and recent logs. Existing data and administrator credentials are retained.
