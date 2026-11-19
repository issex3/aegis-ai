# Risk Management Policy

| | |
|---|---|
| Document status | DRAFT — requires management approval |
| Related criteria | CC3.1, CC3.2 |

## Method

Risks are identified from the repository assessment in `security/SOC2_GAP_ASSESSMENT.md`, from dependency and secret scanning, and from incidents. Each risk is given a severity (Critical, High, Medium, Low) based on likelihood and impact to customer confidentiality or service availability.

## Treatment

- **Mitigate** in code or infrastructure where a real control can be built.
- **Accept** only in writing, with an owner and review date (example: registration returning 409 for an existing email).
- **Transfer** via contracts and insurance is a management decision, not implemented in the product.
- **Avoid** by refusing features that require unsafe execution (customer code in the control plane).

## Current register (summary)

The live register is the gap assessment and the control matrix. Highest residual risks after the current engineering pass:

1. Execution still shares the control plane (SEC-015).
2. No independently tested backups (SEC-023).
3. No managed identity provider, SIEM, or KMS in this environment.
4. No git hosting or branch protection until a repository is created on a managed host (SEC-024).

A formal risk committee, scoring workshop, and board pack have **not** taken place.

## Review

At least annually, and when architecture or a critical finding changes. Management must confirm residual risk acceptance before Type I.
