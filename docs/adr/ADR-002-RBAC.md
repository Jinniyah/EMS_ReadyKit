# ADR-002: Role-Based Access Control (RBAC) Model

**Status:** Accepted  
**Date:** 2026-04-11  
**Decision Owner:** EMS ReadyKit Project  

**Related Artifacts:**
- `docs/architecture.md`
- `docs/adr/ADR-001-Architecture.md`
- `Requirements.md`
- Terraform module: `modules/identity_rbac`

---

## Context

EMS ReadyKit models a small Fire & EMS organization operating under:
- Limited staffing
- High accountability
- Clear operational roles
- Low tolerance for unauthorized access

The system manages **operational inventory and readiness data** (not patient data), but still requires:
- Strong access control
- Clear separation of duties
- Auditability of sensitive workflows (e.g., controlled substances)

Additionally, the project must demonstrate:
- Least-privilege authorization
- Realistic public-sector identity patterns
- Clean separation between platform-level and application-level enforcement

---

## Decision

Adopt a **group-based RBAC model** using **Azure Active Directory groups** for coarse-grained authorization, combined with **application-level authorization logic** for fine-grained operational scope enforcement.

Key decisions:
- No user-level role assignments in Azure
- Roles are assigned exclusively to Azure AD groups
- Azure enforces *who can access the system*
- The application enforces *what they can do* and *which station/vehicles they affect*

---

## Defined Roles

### Administrator
**Scope:** Global

**Responsibilities:**
- System configuration
- Policy visibility
- Global read access across all stations
- Infrastructure and platform oversight

**Platform enforcement:**
- Azure RBAC at subscription or management group scope

---

### Supervisor
**Scope:** Single Station

**Responsibilities:**
- View station-wide compliance
- Review alerts (low stock, expirations)
- Investigate discrepancies
- Limited administrative actions within station

**Platform enforcement:**
- Azure RBAC scoped to the station resource group

**Application enforcement:**
- Access restricted to assigned station data

---

### Responder
**Scope:** Vehicle-level (via application logic)

**Responsibilities:**
- Perform daily inventory checks
- Update inventory for assigned vehicles
- Complete controlled substance checks (where applicable)

**Platform enforcement:**
- Authenticated access only

**Application enforcement:**
- Vehicle and station access validated per request
- No cross-station or administrative access

---

## Authorization Enforcement Model

### Platform Layer (Azure)
Used for:
- Authentication
- Coarse-grained access boundaries
- Infrastructure isolation

Characteristics:
- Azure AD groups
- Role assignments via Terraform
- No direct user assignments
- No per-vehicle infrastructure isolation

---

### Application Layer
Used for:
- Station and vehicle scoping
- Workflow-specific permissions
- Business rule enforcement

Examples:
- A responder cannot submit a daily check for a vehicle outside their station
- A supervisor cannot view or act on another station’s inventory
- Only ALS workflows may trigger controlled substance checks

---

## Alternatives Considered

### User-Level Role Assignments
**Rejected**

User-based role assignments:
- Do not scale operationally
- Are difficult to audit
- Violate least-privilege best practices

Group-based assignments reflect real enterprise and public-sector identity management.

---

### Platform-Only RBAC Enforcement
**Rejected**

Azure RBAC alone cannot enforce:
- Vehicle-level access
- Workflow-specific business rules
- Domain-level invariants

Application-layer authorization is required.

---

### Fine-Grained Azure RBAC per Vehicle
**Rejected**

Per-vehicle Azure RBAC:
- Increases operational overhead
- Provides negligible security benefit
- Breaks cost and simplicity goals

Vehicles are modeled as **data scope**, not infrastructure tenants.

---

## Consequences

### Positive
- Clear separation of concerns
- Least-privilege by default
- Terraform-enforced consistency
- Matches real public-sector patterns
- Clean audit posture

### Tradeoffs
- Requires disciplined application authorization logic
- Some permissions are enforced outside of Azure RBAC

These tradeoffs are intentional and appropriate for the project scope.

---

## Rationale

This RBAC model:
- Mirrors real EMS organizational structure
- Balances platform security with application flexibility
- Avoids false precision and over-engineering
- Demonstrates mature authorization design

The combination of:
- **Group-based platform RBAC**, and
- **Domain-aware application authorization**

provides strong security guarantees without unnecessary complexity.

---

## Related ADRs

- ADR-001: Overall System Architecture
- ADR-003: Logging and Audit Strategy
- ADR-004: Terraform Module Structure

---

**Decision affirmed and approved.**