# Strategy — recommendation: Buy

**Recommendation:** buy

Licensing a managed identity provider like Descope maximizes deployment speed and eliminates infrastructure overhead, perfectly fitting the strict two-week timeline and 2-person team constraints. By leveraging startup programs, the company can secure essential multi-tenancy and RBAC features at zero initial cost without sacrificing their four-month runway.

## Decisive factors
- **Speed of Implementation** — The strict two-week hard stop completely eliminates custom builds, heavily favoring off-the-shelf SaaS platforms that deploy in minutes.
- **Runway Preservation** — Descope's startup plan secures required enterprise features for zero initial cost in the first year, protecting the startup's critical four-month runway.
- **Out-of-the-box Alignment** — The immediate native availability of B2B multi-tenancy and RBAC via SaaS perfectly resolves the core problem without requiring extra self-hosted orchestration.

## Path dossiers

### Build
**Pros:** —
**Cons:**
- Custom development of an authentication system requires several weeks of engineering work, heavily violating the strict two-week timeline constraint. [73166a]
**Key risks:**
- Dedicating weeks to a non-differentiating foundational requirement consumes critical runway for the two-person bootstrapped team. [73166a]
**Reversibility:** Abandoning a custom build sacrifices several weeks of intensive engineering effort that could have been spent on core IP. [73166a]
**Evidence:**
  - [73166a] "From weeks of development to 15 minutes of setup" — [Build a multi-tenant SaaS application: A complete guide from design to implementation · Logto blog](https://blog.logto.io/build-multi-tenant-saas-application)

### Buy
**Pros:**
- Descope natively supports the required role-based access control and B2B multi-tenancy features out-of-the-box. [4eeec6], [68ceb3]
- Early-stage startups can apply for Descope's Hello World Startup Plan to access the Pro Tier free of charge for one year. [d6373a]
- Descope's free forever plan supports up to 7,500 monthly active users and up to 10 tenants without upfront cost. [4e35cf], [2679e7]
- FusionAuth Cloud provides a managed commercial alternative starting at $37 per month. [f444f2]
**Cons:**
- Following the expiration of startup benefits, Descope's Pro tier sharply increases to $249 per month with annual billing. [0c21c2]
- Descope charges overage fees of $0.05 per monthly active user on its paid plans. [048a1a]
**Key risks:**
- The free plan's limit of 10 tenants may quickly become a bottleneck for a multi-tenant B2B SaaS platform if the startup plan is not granted. [2679e7]
**Reversibility:** Migrating away from Descope involves friction, as accessing hashed passwords requires submitting a support request, though basic user export to CSV is natively available. [fb8a60], [00f8a1]
**Evidence:**
  - [4eeec6] "Role-Based Access Control (RBAC)" — [Pricing | Descope](https://www.descope.com/pricing)
  - [68ceb3] "Descope allows a single user to be associated with multiple tenants." — [Business to Business (B2B) | Descope Documentation](https://docs.descope.com/b2b/multi-tenancy)
  - [d6373a] "Apply for our Hello World Startup Plan to get Descope's Pro Tier free" _[stale_cost]_ — [Pricing | Descope](https://www.descope.com/pricing)
  - [4e35cf] "7,500 Monthly active users (MAUs)" _[stale_cost]_ — [Pricing | Descope](https://www.descope.com/pricing)
  - [2679e7] "Free Forever ($0): 7,500 MAUs, 10 tenants" — [DevTune - The developer tool growth platform for the AI-dev era.](https://devtune.ai/verticals/agent-authentication-identity-for-ai/descope/pricing)
  - [f444f2] "FusionAuth’s cloud plans start at $37/month" _[price_conflict]_ — [Auth0 vs FusionAuth (2025): Pricing, Hosting, Use Cases](https://supertokens.com/blog/auth0-vs-fusionauth)
  - [0c21c2] "The Pro tier is $249/month (billed annually)" _[price_conflict]_ — [Descope Pricing – The Complete Guide](https://supertokens.com/blog/descope-pricing)
  - [048a1a] "Overages are charged at $0.05 per MAU" _[partial_evidence, price_conflict]_ — [Descope Pricing – The Complete Guide](https://supertokens.com/blog/descope-pricing)
  - [fb8a60] "Hashed passwords are only available upon request to support" — [Descope: Drag & drop customer identity platform for any app – Auth0Alternatives](https://www.auth0alternatives.com/descope)
  - [00f8a1] "Users can be exported via the console to a CSV file" — [Descope: Drag & drop customer identity platform for any app – Auth0Alternatives](https://www.auth0alternatives.com/descope)

### Buy-then-extend
**Pros:**
- Descope provides robust API primitives for RBAC and B2B multi-tenancy that can be extended if advanced customized logic becomes necessary. [4eeec6], [68ceb3]
**Cons:**
- Descope limits the base free tier to 10 tenants, constraining multi-tenant extensibility limits without upgrading to the $249/month Pro tier. [2679e7], [0c21c2]
**Key risks:**
- Building a custom differentiating layer over a commercial API may unnecessarily complicate a purely enabling requirement that should only take minutes to deploy via a fully prebuilt solution. [73166a]
**Reversibility:** Inherits deep vendor lock-in risks, heavily relying on Descope's support team to release hashed passwords during an exit or migration. [fb8a60]
**Evidence:**
  - [4eeec6] "Role-Based Access Control (RBAC)" — [Pricing | Descope](https://www.descope.com/pricing)
  - [68ceb3] "Descope allows a single user to be associated with multiple tenants." — [Business to Business (B2B) | Descope Documentation](https://docs.descope.com/b2b/multi-tenancy)
  - [2679e7] "Free Forever ($0): 7,500 MAUs, 10 tenants" — [DevTune - The developer tool growth platform for the AI-dev era.](https://devtune.ai/verticals/agent-authentication-identity-for-ai/descope/pricing)
  - [0c21c2] "The Pro tier is $249/month (billed annually)" _[price_conflict]_ — [Descope Pricing – The Complete Guide](https://supertokens.com/blog/descope-pricing)
  - [73166a] "From weeks of development to 15 minutes of setup" — [Build a multi-tenant SaaS application: A complete guide from design to implementation · Logto blog](https://blog.logto.io/build-multi-tenant-saas-application)
  - [fb8a60] "Hashed passwords are only available upon request to support" — [Descope: Drag & drop customer identity platform for any app – Auth0Alternatives](https://www.auth0alternatives.com/descope)

### Adopt & self-host
**Pros:**
- Prebuilt authentication platforms like Logto reduce integration time from weeks to just 15 minutes. [73166a], [d4aac2]
- Self-hosting Logto on a VPS or Coolify is highly cost-effective, incurring only $5 to $20 in monthly resource expenses. [ef78b5], [8cb033]
- Logto and SuperTokens require minimal hardware, functioning smoothly on 256MB to 512MB of RAM. [ac0229], [70b87d], [a9d6e0]
- FusionAuth Community provides a fully free-to-use self-hosted plan backed by ongoing maintenance and feature additions. [275a3a], [207844]
**Cons:**
- Self-hosting SuperTokens requires purchasing a paid feature add-on to enable multi-tenancy, contradicting the low-cost constraint. [7aa94c]
- Keycloak deployments require up to 2 hours of setup and demand significantly heavier resources, including 2 to 4 GB of RAM and 1GB of disk space. [d4aac2], [1b90e2], [012d19]
**Key risks:**
- Although established tools like Keycloak are backed by Red Hat, their high resource requirements could introduce unwanted operational burden for a two-person team. [1b90e2], [4ac080]
**Reversibility:** Excellent reversibility and data ownership are maintained as SuperTokens and FusionAuth store authentication details directly in your own managed PostgreSQL database. [a2cbe3], [e090e5], [d5d6c3]
**Evidence:**
  - [73166a] "From weeks of development to 15 minutes of setup" — [Build a multi-tenant SaaS application: A complete guide from design to implementation · Logto blog](https://blog.logto.io/build-multi-tenant-saas-application)
  - [d4aac2] "Setup time | 15 minutes | 1–2 hours |" _[partial_evidence]_ — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [ef78b5] "You only pay for your VPS hosting (typically $5-20/month)" _[price_conflict]_ — [Logto - Self-Hosted Deployment | Server Compass](https://servercompass.app/templates/logto)
  - [8cb033] "adding Logto to the stack costs you roughly $6-10 extra per month" _[price_conflict]_ — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [ac0229] "Logto requires a minimum of 512MB RAM." — [Logto - Self-Hosted Deployment | Server Compass](https://servercompass.app/templates/logto)
  - [70b87d] "RAM | 256 MB" — [Deploy SuperTokens | Open Source Auth0, AWS Cognito, Okta Alternative](https://railway.com/deploy/supertokens)
  - [a9d6e0] "At idle it consumes around 512 MB of RAM" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [275a3a] "Self-host FusionAuth on your own infrastructure for free." — [FusionAuth Pricing | Free and Flexible Plans for Your Authentication Needs](https://fusionauth.io/pricing)
  - [207844] "FusionAuth will always have a powerful, full featured free-to-use Community plan." _[stale_cost]_ — [Plans and Features | FusionAuth Docs](https://fusionauth.io/docs/get-started/core-concepts/plans-features)
  - [7aa94c] "you will have to enable the multi tenancy paid feature" _[stale_cost]_ — [jackson-supertokens-express/README.md at main · supertokens/jackson-supertokens-express](https://github.com/supertokens/jackson-supertokens-express/blob/main/README.md)
  - [1b90e2] "production recommendations are 2 to 4 GB" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [012d19] "At least 1G of diskspace" _[stale_cost]_ — [keycloak-documentation](https://wjw465150.gitbooks.io/keycloak-documentation/content/server_installation/topics/installation/system-requirements.html)
  - [4ac080] "Keycloak is maintained by Red Hat, which was acquired by IBM" — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [a2cbe3] "SuperTokens Core is stateless; all auth data lives in Postgres" — [Deploy SuperTokens | Open Source Auth0, AWS Cognito, Okta Alternative](https://railway.com/deploy/supertokens)
  - [e090e5] "run it together with a MySQL or PostgreSQL server" — [Plans and Features | FusionAuth Docs](https://fusionauth.io/docs/get-started/core-concepts/plans-features)
  - [d5d6c3] "The supported database is PostgreSQL. The minimum required version is 13.0." — [Self-host SuperTokens | SuperTokens Docs](https://supertokens.com/docs/deployment/self-host-supertokens)

## Challenger's counter-recommendation: Adopt & self-host
_The engine's own second-best and the challenger independently converged on this path._
**Wins when:**
- Strict long-term cost control and avoidance of SaaS vendor lock-in are prioritized over the zero-maintenance convenience of a fully managed service.
- The team prefers to maximize their existing Railway and PostgreSQL infrastructure rather than adding third-party dependencies with potential data portability hurdles.

While a managed identity provider minimizes maintenance, adopting and self-hosting a prebuilt solution like FusionAuth or Logto prevents vendor lock-in and protects a tight four-month runway from future subscription costs. The startup's existing Railway and Postgres stack perfectly supports self-hosting FusionAuth's Community Edition for free [275a3a, e090e5]. Alternatively, a self-hosted Logto instance can be integrated in roughly 15 minutes [73166a] with negligible hosting resource costs of around $6 to $10 monthly [8cb033]. This approach easily satisfies the strict two-week timeline while shielding the bootstrapped company from a managed provider's steep paid tiers [0c21c2], future overage fees [048a1a], and data portability restrictions like gated access to hashed user passwords [fb8a60].
  - [275a3a] "Self-host FusionAuth on your own infrastructure for free." — [FusionAuth Pricing | Free and Flexible Plans for Your Authentication Needs](https://fusionauth.io/pricing)
  - [e090e5] "run it together with a MySQL or PostgreSQL server" — [Plans and Features | FusionAuth Docs](https://fusionauth.io/docs/get-started/core-concepts/plans-features)
  - [73166a] "From weeks of development to 15 minutes of setup" — [Build a multi-tenant SaaS application: A complete guide from design to implementation · Logto blog](https://blog.logto.io/build-multi-tenant-saas-application)
  - [8cb033] "adding Logto to the stack costs you roughly $6-10 extra per month" _[price_conflict]_ — [Logto vs Keycloak: Modern DX vs Enterprise Power 2026](https://ossalt.com/guides/logto-vs-keycloak-2026)
  - [0c21c2] "The Pro tier is $249/month (billed annually)" _[price_conflict]_ — [Descope Pricing – The Complete Guide](https://supertokens.com/blog/descope-pricing)
  - [048a1a] "Overages are charged at $0.05 per MAU" _[partial_evidence, price_conflict]_ — [Descope Pricing – The Complete Guide](https://supertokens.com/blog/descope-pricing)
  - [fb8a60] "Hashed passwords are only available upon request to support" — [Descope: Drag & drop customer identity platform for any app – Auth0Alternatives](https://www.auth0alternatives.com/descope)

## Open questions
- Will Descope automatically grant the early-stage Startup Plan given the bootstrapped nature of the company, or is there an approval delay that threatens the two-week timeline?
- If the startup scales past the 10-tenant free limit and does not secure the startup plan, can they afford the $249/mo upgrade on their current runway?
