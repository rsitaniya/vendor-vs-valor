# BUILD research

15 verified claims.

## m13
- Keycloak's open-source viability is backed by active maintenance from Red Hat. (SUPPORTED)
  > "Keycloak is maintained by Red Hat, which was acquired by IBM" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)

## m14
- The SuperTokens Core service can be deployed directly as a Docker container. (SUPPORTED)
  > "The core service can be deployed using a Docker image" — [Self-host SuperTokens | SuperTokens Docs](https://supertokens.com/docs/deployment/self-host-supertokens)
- SuperTokens requires PostgreSQL version 13.0 or higher for database storage. (SUPPORTED)
  > "The supported database is PostgreSQL. The minimum required version is 13.0." — [Self-host SuperTokens | SuperTokens Docs](https://supertokens.com/docs/deployment/self-host-supertokens)

## m3
- Self-hosting Logto on a VPS typically incurs hosting expenses ranging from $5 to $20 per month. (SUPPORTED)
  > "You only pay for your VPS hosting (typically $5-20/month)" — [Logto - Self-Hosted Deployment | Server Compass](https://servercompass.app/templates/logto)
- Self-hosting Logto requires a minimum baseline of 512MB RAM. (SUPPORTED)
  > "Logto requires a minimum of 512MB RAM." — [Logto - Self-Hosted Deployment | Server Compass](https://servercompass.app/templates/logto)
- The minimum hardware allocation for a SuperTokens Core container includes 256 MB of RAM. (SUPPORTED)
  > "RAM | 256 MB" — [Deploy SuperTokens | Open Source Auth0, AWS Cognito, Okta Alternative](https://railway.com/deploy/supertokens)
- Running the Keycloak authentication server requires a minimum of 512MB of RAM. (SUPPORTED) _[stale_cost]_
  > "At least 512M of RAM" — [keycloak-documentation](https://wjw465150.gitbooks.io/keycloak-documentation/content/server_installation/topics/installation/system-requirements.html)
- Keycloak requires a minimum allocation of 1GB of disk space to deploy successfully. (SUPPORTED) _[stale_cost]_
  > "At least 1G of diskspace" — [keycloak-documentation](https://wjw465150.gitbooks.io/keycloak-documentation/content/server_installation/topics/installation/system-requirements.html)
- At idle, Logto's self-hosted application process consumes approximately 512 MB of RAM. (SUPPORTED)
  > "At idle it consumes around 512 MB of RAM" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
- Production deployments of Keycloak are recommended to have between 2 and 4 GB of RAM. (SUPPORTED)
  > "production recommendations are 2 to 4 GB" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
- Adding Logto to a pre-existing self-hosted deployment platform such as Coolify requires roughly $6 to $10 monthly in VPS resource costs. (SUPPORTED)
  > "adding Logto to the stack costs you roughly $6-10 extra per month" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
- Enabling multi-tenancy inside a self-hosted SuperTokens setup connected to a physical Postgres instance requires a paid feature add-on. (SUPPORTED) _[stale_cost]_
  > "you will have to enable the multi tenancy paid feature" — [jackson-supertokens-express/README.md at main · supertokens/jackson-supertokens-express](https://github.com/supertokens/jackson-supertokens-express/blob/main/README.md)

## m6
- Integrating Logto is estimated to require about 15 minutes, whereas configuring Keycloak demands 1 to 2 hours of setup time. (PARTIAL) _[partial_evidence]_
  > "Setup time | 15 minutes | 1–2 hours |" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
- Adopting prebuilt authentication platforms like Logto can shrink integration time from several weeks of custom work to 15 minutes. (SUPPORTED)
  > "From weeks of development to 15 minutes of setup" — [Build a multi-tenant SaaS application: A complete guide from design to implementation · Logto blog](https://blog.logto.io/build-multi-tenant-saas-application)

## m9
- SuperTokens operates as a stateless service, persisting all user authentication details directly in PostgreSQL. (SUPPORTED)
  > "SuperTokens Core is stateless; all auth data lives in Postgres" — [Deploy SuperTokens | Open Source Auth0, AWS Cognito, Okta Alternative](https://railway.com/deploy/supertokens)

## Dimension coverage
- ✗ m1 Strategic differentiation / moat — 0 claim(s)
- ✗ m2 Proprietary-data generation — 0 claim(s)
- ✓ m3 Total cost — build ★ — 9 claim(s)
- ✗ m4 Total cost — maintenance (the bloat curve) — 0 claim(s)
- ✓ m6 Time-to-value ★ — 2 claim(s)
- ✗ m7 Resource & talent availability — 0 claim(s)
- ✗ m8 Reversibility / switching cost — 0 claim(s)
- ✓ m9 Data ownership / sensitivity / compliance — 1 claim(s)
- ✗ m10 Customization need vs. availability — 0 claim(s)
- ✗ m11 Focus / core-value alignment ★ — 0 claim(s)
- ✓ m13 Vendor viability / lock-in risk ★ — 1 claim(s)
- ✓ m14 Integration complexity ★ — 2 claim(s)

## Coverage gaps
- thin content: https://www.youtube.com/watch?v=Fz_csjJAxUI
- fetch failed: https://medium.com/@mercicodes/implementing-user-authentication-in-react-with-supertokens-fb91a29b338 (HTTPStatusError)
- thin content: https://www.keycloak.org/high-availability/concepts-memory-and-cpu-sizing
- fetch failed: https://www.baeldung.com/spring-boot-keycloak (HTTPStatusError)
- fetch failed: https://logto.medium.com/build-a-multi-tenant-saas-application-a-complete-guide-from-design-to-implementation-d109d041f253 (HTTPStatusError)
- fetch failed: https://logto.medium.com/how-to-use-logto-for-your-encore-application-bad7e6a05fd4 (HTTPStatusError)
- no evidence for priority dimension m11 (Focus / core-value alignment)