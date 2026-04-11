
# EMS ReadyKit  
## Cloud Platform & Application Technical Requirements

**Purpose:** Demonstrate cloud engineering, platform design, and operational judgment  
**Status:** Technical Demonstration (Non‑Production)

---


## 1. Purpose

This document defines the technical requirements and design intent for **EMS ReadyKit**, a cloud‑native inventory and vehicle readiness platform modeled for a small Fire & EMS organization.

The system is intentionally scoped to demonstrate:
- Infrastructure‑as‑Code discipline
- Secure, role‑based access control
- Operational observability
- Cost‑aware architectural decision‑making
- Domain modeling under real‑world constraints

This project is **not a live deployment**, does **not process patient data**, and exists solely as a technical portfolio artifact for review.

---

## 2. Problem Statement (Engineering Framing)

Many small public‑sector and regulated organizations operate mission‑critical services with:
- Limited IT staffing
- Manual or spreadsheet‑based processes
- High accountability requirements
- Low tolerance for system failure

From an engineering standpoint, the challenge is:

> **How do you design a secure, auditable, observable system that is simple, affordable, and maintainable—without over‑engineering it?**

EMS ReadyKit addresses this question using modern cloud platform practices applied to a constrained, realistic domain.

---

## 3. Operational Model

The system is modeled for a **single Fire & EMS station** with a **small, fixed fleet**:

- **1 Station**
- **2 Ambulances**
- **3 Fire Trucks**

Vehicles are permanently **assigned to the station** and act as independent operational units for readiness and inventory tracking.

Vehicle identifiers and inventory data are illustrative only.

---

## 4. Design Objectives

### 4.1 Primary Objectives
- Demonstrate **Infrastructure‑as‑Code** (IaC) maturity
- Apply **least‑privilege security** principles
- Build **operationally observable** systems
- Model a real domain with **controlled scope**
- Optimize for **clarity, cost, and reliability**

### 4.2 Explicit Non‑Objectives
- No patient care documentation (PHI)
- No billing, ePCR, or CAD integration
- No regulatory certification claims
- No microservices or unnecessary complexity

These exclusions are **intentional architectural decisions**, not omissions.

---

## 5. Functional Requirements

### FR‑1: Station and Vehicle Model
- The system shall support one or more stations.
- Vehicles shall be assigned to exactly one station.
- This deployment includes one station with five vehicles.

---

### FR‑2: Vehicle‑Centric Inventory Locations
- Each vehicle shall function as its own inventory location.
- A station‑level supply room shall exist for resupply and overflow.

---

### FR‑3: Daily Vehicle Readiness Checks
- Each active vehicle shall require **one completed inventory check per calendar day**.
- A readiness check shall record:
  - Vehicle
  - Timestamp
  - User performing the check
  - Status (`PASS`, `NEEDS_RESTOCK`)

---

### FR‑4: Inventory Item Tracking
The system shall track inventory items by:
- Category (Medication, Consumable, Equipment)
- Location (vehicle or supply room)
- Quantity on hand
- Lot number (where applicable)
- Expiration date (where applicable)

---

### FR‑5: Expiration Management
- The system shall identify items expiring within a configurable threshold.
- Expiring items shall be surfaced to supervisory roles.
- Expiration tracking shall support lot‑level visibility.

---

### FR‑6: Par Levels and Low‑Stock Alerts
- Items may have minimum and maximum (par) levels defined per location.
- When inventory falls below minimum:
  - A low‑stock condition shall be flagged
  - The item shall be marked for restocking

---

### FR‑7: Controlled Substances (Ambulances Only)
- Controlled substances shall apply **only to ambulances**.
- Daily controlled substance checks shall require:
  - Primary signer
  - Secondary signer
- Any discrepancy shall generate a high‑severity audit event.

---

### FR‑8: Audit Logging
The system shall log all material actions, including:
- Inventory changes
- Readiness check completion
- Controlled substance checks
- Administrative configuration changes

Audit events shall include:
- Actor
- Timestamp
- Action
- Affected entity

---

## 6. Security Requirements

### SR‑1: Role‑Based Access Control (RBAC)
The system shall support role‑based access, including:
- **Administrator** — system configuration
- **Supervisor** — station‑level oversight
- **Responder** — vehicle‑level operations

---

### SR‑2: Least Privilege Enforcement
- Users shall only access vehicles associated with their station.
- Permissions shall be scoped by role and responsibility.

---

### SR‑3: Data Sensitivity Boundaries
- The system shall not store or process patient‑identifiable information.
- All data handled is operational inventory metadata only.

---

## 7. Observability & Monitoring Requirements

### MR‑1: Centralized Logging
- Application and audit logs shall be centrally collected.
- Logs shall support search, filtering, and alerting.

---

### MR‑2: Security Observability
- Selected telemetry may be forwarded to a SIEM.
- Monitoring focus includes:
  - Authentication failures
  - Unauthorized access attempts
  - Inventory tampering indicators

---

### MR‑3: Validation
- Controlled test activity may be used to validate logging and alerting.
- No live or production systems are involved.

---

## 8. Architecture Principles

### 8.1 Simplicity First
- Single application
- Single primary datastore
- Minimal moving parts

---

### 8.2 Infrastructure as Code
- Entire environment deployed via Terraform
- No manual cloud configuration
- Environments are reproducible and disposable

---

### 8.3 Cost Discipline
- Right‑sized compute
- Short log retention by default
- Budget alerts enabled
- No premium services without justification

---

## 9. Tradeoffs and Risks (Explicit)

| Decision | Rationale |
|--------|----------|
Single‑region deployment | Reduced complexity and cost |
Monolithic application | Fewer failure modes |
Short log retention | Cost‑controlled demo scope |
Small fleet size | Realistic signal‑to‑noise ratio |

These tradeoffs are intentional and defensible.

---

## 10. What This Project Demonstrates

EMS ReadyKit is not about EMS software.

It demonstrates the ability to:
- Rapidly understand a domain
- Model it accurately
- Apply modern cloud engineering practices
- Balance security, operability, and cost
- Communicate architectural decisions clearly

These skills are directly transferable to:
- Enterprise internal platforms
- Regulated environments
- Public‑sector systems
- Cost‑constrained organizations

---

## 11. Summary

EMS ReadyKit demonstrates:
- ✅ Cloud platform engineering fundamentals  
- ✅ Infrastructure‑as‑Code maturity  
- ✅ Security‑first thinking  
- ✅ Operational awareness  
- ✅ Explicit tradeoff reasoning  

The system is intentionally **small**, **well‑scoped**, and **defensible**.

---

## Required Documentation & Evidence
Architecture diagram
ADRs for:

RBAC model
Policy design
Network baseline


Runbook for deploy/validate/destroy
