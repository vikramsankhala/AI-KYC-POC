<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Please create a delta-only md file for the above

Below is a delta-only Markdown file, treating **V6 (2025‑07‑22)** as baseline and **V7 (2025‑08‑18)** as the changed version.[^1][^2]

```markdown
# Delta: NX PTO V7 vs V6 (RISE QuoteTool)

## Header / Meta

- Quote date changed:
  - V6: 2025-07-22
  - V7: 2025-08-18

- Page count:
  - V6: 7 pages
  - V7: 6 pages

## Domestic S4HANA – DEV additional storage

- V6:
  - Additional Storage – Filesystem, DEV, 20480 GB (“St”), backup FS monthly with daily full + incr, phase 5.

- V7:
  - Additional Storage for S4 DEV – Filesystem, DEV, 10880 GB (“St”), phase 5.
  - Net change: **storage reduced by 9600 GB** and moved to the “Others IaaS” section.

## GRC DEV – additional storage

- V6:
  - Additional Storage – Filesystem, DEV, 5120 GB (“St”), backup FS monthly with daily full + incr, phase 5.

- V7:
  - Additional Storage for GRC DEV – Filesystem, DEV, 768 GB (“St”), phase 5.
  - Net change: **storage reduced by 4352 GB** and moved to the “Others IaaS” section.

## Others / IaaS – migration servers and storage

- V6:
  - Migration Server Domestic – IaaS Basic SBX, 128 GB RAM, 300 GB (“St”) storage, Linux, 95.00 SLA, phase 5.
  - Migration Server Overseas – IaaS Basic SBX2, 128 GB RAM, 300 GB (“St”) storage, Linux, 95.00 SLA, phase 5.

- V7:
  - Migration Server 1 – IaaS Basic SBX, 128 GB RAM, 300 GB (“St”) storage, Linux, 95.00 SLA, phase 5.
  - Migration Server 1 Additional storage – Filesystem SBX, 128 GB (“St”), Linux, phase 5.
  - Migration Server 3 – IaaS Basic SBX3, 128 GB RAM, 300 GB (“St”) storage, Linux, 95.00 SLA, phase 5.
  - Migration Server 3 Additional storage – Filesystem SBX3, 128 GB (“St”), Linux, phase 5.
  - Additional Storage for S4 DEV – Filesystem DEV, 10880 GB (“St”), Linux, phase 5.
  - Additional Storage for GRC DEV – Filesystem DEV, 768 GB (“St”), Linux, phase 5.
  - Structural change: **Domestic/Overseas mapping (SBX/SBX2) in V6 replaced by SBX and SBX3 plus explicit additional storage lines** in V7.

## Unchanged areas (no deltas listed)

- Domestic S4HANA PRD/QAS/DEV system sizes and counts (excluding DEV extra storage).
- Domestic SLT, DS, Cloud Connector.
- Overseas S4HANA PRD2 and SLT PRD2.
- GRC PRD/QAS/DEV system sizes (excluding DEV extra storage).
- SAP Connectivity Service and Supplementary Services (Transit Gateway, Load Balancers, DR host packages).
```

<div align="center">⁂</div>

[^1]: contract_RISE-QuoteTool-2503-0-2025-07-22_NX_PTO_V6-woBW-1.pdf

[^2]: contract_RISE-QuoteTool-25Q3-0-2025-08-18_NX_PTO_V7.pdf

