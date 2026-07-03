# Capability need — user auth and access management

We are a two-person startup (one engineer, one CEO). We are building a B2B SaaS
for small logistics companies — route planning, driver tracking, delivery
confirmation. We are pre-revenue, bootstrapped, about 4 months of runway left.

We need users to be able to log in. Right now we have nothing — no auth at all.
We need the basics: email/password login, maybe Google SSO at some point, and
the ability to have multiple users per company with different roles (admin vs
driver vs dispatcher). We do not have time to build something complex.

Our engineer is full-stack, comfortable with Node.js and React. We are on
Vercel for the frontend and a small Railway-hosted Express API. Postgres database.

Budget is very tight — ideally under $50/month to start. Free tier preferred.
We have maybe two weeks of engineering time to spend on this before we need to
get back to the actual product.

We are not sure whether to use something like Auth0 or Clerk or just roll our
own with JWTs. We have heard self-hosting something like Supabase Auth or
Keycloak is possible but do not know if that is realistic for one engineer.
