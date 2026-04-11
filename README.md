# EMS_ReadyKit
Cloud‑native inventory and vehicle readiness platform demonstrating Terraform‑managed Azure infrastructure, RBAC, audit logging, and operational observability in a regulated domain.

## Executive Summary

Emergency response organizations rely on consistent vehicle readiness, accurate inventory, and timely replacement of expiring or depleted supplies. Small township Fire and EMS departments often manage this through manual processes that are time-consuming, difficult to audit, and prone to error.
EMS ReadyKit is a cloud-based inventory and readiness system designed to demonstrate how a township Fire and EMS department could track vehicle inventory, ensure daily readiness checks, manage medical supply expirations, and maintain audit-ready records using modern cloud infrastructure.
This project is a technical demonstration only. It is not connected to real departmental systems and does not contain patient information.
 
 ---

## Operational Context

This project is modeled after a small township fire and EMS department,
using publicly available information about Newberg Township Fire & EMS
as the operational setting.


1 Station
2 Ambulances
3 Fire Trucks

Vehicles are permanently assigned to the station and operate as independent inventory locations for daily readiness checks.
Vehicle identifiers and inventory data used in this project are illustrative only.

## Goals and Objectives

# Primary Goals

Improve visibility into vehicle readiness
Reduce risk of expired or missing supplies
Provide daily and monthly compliance reporting
Maintain audit-ready inventory records
Demonstrate secure, cost-conscious cloud architecture

# Non-Goals

No patient care documentation
No billing or ePCR integration
No live operational deployment
No claims of regulatory certification or compliance

## System Scope

#  In Scope

Vehicle-based inventory tracking
Daily vehicle inventory checks
Expiration and low-stock alerts
Controlled substance accountability (ambulances only)
Audit logging of inventory actions
Cloud monitoring and security observability

# Out of Scope

Patient-identifiable information (PHI)
Patient care reports
Dispatch or CAD integration
Financial or vendor ordering systems

## Organizational Model
 # Station
The system supports one or more stations.
This deployment includes one station.

Each station:

Owns vehicles
Manages a central supply room
Receives compliance and readiness reports

# Vehicles
Vehicles are assigned to a station and operate as independent inventory locations.

Vehicle Type | Quantity | Notes
Ambulance |  2 | Includes controlled substances
Fire Truck | 3 | Medical + rescue inventory only

## Evidence Matrix
Terraform modules → iac/modules/*
Monitoring/logging → docs/evidence/*
Governance → policy module + compliance screenshots
Documentation → ADRs + runbook


## Security Monitoring Extension

This project extends the Azure Landing Zone with a centralized
security monitoring capability using Security Onion.

### Goals
- Validate that cloud network and host telemetry is observable
- Detect simulated attack activity
- Demonstrate security-operational readiness

### Architecture
(diagram here)

### Data Sources
- Azure NSG / VNet flow logs
- Linux VM authentication logs

### Detection Validation
- TryHackMe port scan → alert observed
- SSH brute force → authentication alerts

### Lessons Learned
- Log volume considerations
- Signal vs noise
- Cost / performance tradeoffs
