# Act! `Prospects` (Prospects549) — Full Database Schema Reference
Restored from `Act! Prospects549_RDB.zip` (Act! full database backup, SQL Server native `.BAK`), explored directly against a disposable SQL Server 2022 instance. This document is the permanent record of that exploration — the restored database itself is discarded after this.
- **Total tables:** 228  
- **Total views:** 153 (Act!'s internal query layer, not source data — not documented here)  
- **Business/domain tables** (documented in full below): 79  
- **Act! internal/engine tables** (sync engine, ACL, UI metadata, licensing — listed for completeness, not detailed): 149
## Can we restore the `.bak` straight onto our Postgres/Dokploy instance?
**No — not directly, and we should not try.** A `.bak` is a SQL Server–native binary backup format; only SQL Server can restore it (which is exactly what we did here, in a throwaway Docker container). Postgres has no restore path for it at all. Beyond the format mismatch, a byte-for-byte port wouldn't be desirable anyway:

- The schema is Act!'s **internal application schema**, not a clean business model — ~65% of these 228 tables (sync engine, ACL/permissions, UI metadata, licensing, workflow engine) are Act! product internals with zero value to us; see 'Act! internal/engine tables' below.
- Even the real business tables use GUID PKs everywhere, a notes/history model split across a fact table plus per-entity junction tables (`TBL_NOTE` + `TBL_CONTACT_NOTE`/`TBL_COMPANY_NOTE`/`TBL_GROUP_NOTE`/...), and custom fields as a flat `USER1..USER15` block plus separately-suffixed `CUST_*` columns whose real names live in `TBL_SYSCOLUMN`, not in the column name Postgres would see.
- Per `CONTEXT.md`'s already-agreed principles, we want a clean hand-designed Postgres schema (typed columns for what matters, `jsonb` for the rest, explicit `source_act_id`/`source_db` provenance) — not an automatic mirror of Act!'s internals.

**The real path:** restore `.bak` → SQL Server (done, disposable) → hand-write a Postgres schema informed by this document → write an ETL script that reads from the (temporary) SQL Server instance and writes into Postgres, cross-referencing `TBL_SYSCOLUMN`/`TBL_PICKLIST`/`TBL_PICKLISTITEM` to decode custom fields and dropdown values along the way → validate row counts + spot-check → only then point at the real Dokploy instance. This document is what the ETL script and the target schema design will be written against.
## Table of contents
1. [Row counts, all tables](#row-counts-all-tables)
2. [Business/domain tables — full column detail](#businessdomain-tables--full-column-detail)
3. [Foreign key map (business tables)](#foreign-key-map-business-tables)
4. [Decoded picklists / dropdown values](#decoded-picklists--dropdown-values)
5. [History types & Note types](#history-types--note-types)
6. [Custom field decode — `TBL_SYSCOLUMN`](#custom-field-decode)
7. [Observations & migration notes](#observations--migration-notes)
8. [Act! internal/engine tables — reference list only](#act-internalengine-tables--reference-list-only)
## Row counts, all tables
| Table | Row count |
|---|---|
| `TBL_HISTORY` | 1169998 |
| `TBL_CONTACT_HISTORY` | 1056743 |
| `TBL_SYNCCONTACT_ACL` | 361873 |
| `TBL_CONTACT_ACL` | 267968 |
| `TBL_COMPANY_HISTORY` | 213208 |
| `TBL_GROUP_CONTACT` | 190506 |
| `TBL_SYNCSUBSCRIPTION` | 179132 |
| `TBL_NOTE` | 112795 |
| `TBL_PHONE` | 106101 |
| `TBL_SYNCCONTACT` | 98819 |
| `CTL_SYNCROW_ADD` | 96074 |
| `CTL_SYNCROW_DELETE` | 89385 |
| `TBL_ADDRESS` | 84177 |
| `CTL_SYNCDBMAP_SESSIONROW` | 77553 |
| `TBL_CONTACT` | 77464 |
| `TBL_EMAIL` | 75281 |
| `TBL_CONTACT_NOTE` | 74924 |
| `CTL_EVENTLOGDETAIL` | 68371 |
| `TBL_COMPANY_NOTE` | 68105 |
| `CTL_SYNCROW_UPDATECOLUMN` | 56149 |
| `TBL_COMPANY_ACL` | 32152 |
| `TBL_IMPORT_HISTORYITEM` | 16225 |
| `CTL_SYNCROW_UPDATE` | 15186 |
| `TBL_COMPANY` | 10370 |
| `CTL_EVENTLOG` | 9147 |
| `TBL_COMPANY_CONTACT` | 7959 |
| `TBL_PICKLISTITEM` | 3110 |
| `TBL_CONTACT_ACTIVITY` | 2333 |
| `TBL_ACCESSOR_ACTIVITY` | 2089 |
| `TBL_ACTIVITY` | 2071 |
| `TBL_GROUP_ACL` | 1990 |
| `TBL_SYSCOLUMN` | 1918 |
| `CTL_SYNCCOLUMN` | 1918 |
| `TBL_SYSCOLUMN_ACL` | 1603 |
| `CUST_ContactTable1_100939` | 1509 |
| `CTL_SYNCROW_FILE` | 1278 |
| `TBL_PHONEMASK` | 1265 |
| `TBL_COUNTRY` | 1246 |
| `CTL_OLEDBFUNCTION_SYSCOLUMN` | 1210 |
| `TBL_COMPANY_ACTIVITY` | 912 |
| `TBL_PREFERENCE` | 824 |
| `TBL_SYSTABLEKEY_SYSCOLUMN` | 777 |
| `CTL_LOCALSTRING` | 600 |
| `TBL_GROUP_NOTE` | 572 |
| `TBL_GROUP` | 565 |
| `TBL_GROUP_HISTORY` | 547 |
| `TBL_SYSTABLEKEY` | 527 |
| `TBL_ACCESSOR_DELEGATE` | 409 |
| `TBL_SYSTABLERELATION` | 335 |
| `CTL_SYNCDBMAP_SESSION` | 330 |
| `CTL_SYNCDBMAPINFO_HISTORY` | 329 |
| `TBL_ACCESSOR_PREFERENCE` | 314 |
| `TBL_ACCESSOR_ACTIVITY_CLEARED` | 309 |
| `CTL_SYNCTABLE` | 239 |
| `TBL_SYSTABLE` | 239 |
| `CTL_OLEDBVIEW_KEYINDEX_SYSCOLUMN` | 221 |
| `TBL_ROLE_PERMISSION` | 219 |
| `TBL_ATTACHMENT` | 215 |
| `CTL_OLEDBFUNCTION` | 213 |
| `CTL_OLEDBVIEW_KEYINDEX` | 201 |
| `CTL_SYSTABLEORDER` | 157 |
| `CTL_SYNC_DEVICETABLE` | 143 |
| `CTL_OLEDBVIEW_DERIVEDCOLUMN` | 139 |
| `CTL_SYNCACCESSOR` | 107 |
| `TBL_ACCESSOR` | 107 |
| `TBL_USER_PERMISSION` | 104 |
| `TBL_PERMISSION` | 94 |
| `TBL_LOGONHISTORY` | 82 |
| `CTL_OLEDBVIEW_OLEDBFUNCTION` | 79 |
| `CTL_OLEDBVIEW_PROVIDERVIEW` | 74 |
| `CTL_OLEDBVIEW` | 73 |
| `CTL_PROVIDERVIEW` | 71 |
| `CTL_DBCONFIG` | 67 |
| `TBL_HISTORYTYPE` | 65 |
| `TBL_PICKLIST_SYSCOLUMN` | 63 |
| `TBL_SECONDARY` | 60 |
| `TBL_SYSDOMAIN_SYSOPERATOR` | 55 |
| `TBL_USER_ACCESSOR_ENUM` | 42 |
| `TBL_USER_DEFAULT_ACL` | 41 |
| `TBL_SYSCONSTANT` | 40 |
| `TBL_PASSWORDHISTORY` | 35 |
| `TBL_PICKLIST` | 35 |
| `TBL_EVENTLOGTYPE` | 33 |
| `TBL_PERMISSION_DEPEND` | 32 |
| `TBL_TEAM_USER` | 31 |
| `TBL_SYSDATATYPE` | 31 |
| `TBL_WORKFLOWDEF_ACL` | 30 |
| `TBL_SYSTABLEDOMAIN` | 24 |
| `TBL_SYSENTITYRELATION` | 24 |
| `TBL_SYSLOCALCOLUMN` | 23 |
| `TBL_SYSENTITY_SYSTABLE` | 23 |
| `TBL_INSTALL_LOGS` | 22 |
| `TBL_SYSVALUEUSAGE` | 22 |
| `TBL_SYSOPERATOR` | 21 |
| `TBL_VIRTUALRECORDTYPE` | 20 |
| `TBL_SYNCSET` | 20 |
| `CUST_CONTACT_SL_CONTACT_INVOICE` | 19 |
| `CUST_SL_CONTACT_INVOICE` | 19 |
| `TBL_FOLDER` | 19 |
| `TBL_FEATURESET` | 18 |
| `TBL_OPPORTUNITY_ACL` | 18 |
| `TBL_STAGE` | 17 |
| `TBL_SYSCALCCOLUMN` | 17 |
| `TBL_HISTORYTYPE_GROUP` | 17 |
| `TBL_ANALYTICS_VIEW_DEFINITION` | 15 |
| `TBL_SYSENTITY` | 13 |
| `TBL_SYSVALUE` | 12 |
| `TBL_USER` | 11 |
| `TBL_SYNCSET_ACCESSOR` | 11 |
| `CTL_USERSESSION` | 10 |
| `TBL_ACCESSOR_SETTING` | 10 |
| `TBL_COMPANYQUERY` | 10 |
| `TBL_STAGE_HISTORY` | 10 |
| `TBL_COMPANYCONTACT_MAP` | 9 |
| `TBL_SYNCDBTYPE` | 9 |
| `TBL_SYSDOMAIN` | 9 |
| `CTL_SYNC_INITIALIZE_ROWDATA` | 8 |
| `TBL_SYNCSETQUERY` | 8 |
| `TBL_EXTERNALMAP_SOURCE` | 8 |
| `CTL_SYNCDBMAP_ROWDATA` | 8 |
| `TBL_OPPORTUNITY_HISTORY` | 7 |
| `CUST_CONTACT_SL_CONTACT_SOP` | 7 |
| `TBL_TEAM` | 7 |
| `TBL_WORKFLOWDEF` | 7 |
| `TBL_GROUPQUERY` | 7 |
| `CUST_SL_CONTACT_SOP` | 7 |
| `TBL_ROLE` | 6 |
| `TBL_OPPORTUNITY` | 6 |
| `TBL_ACTIVITYTYPE` | 6 |
| `TBL_HISTORYTYPE_SUPERGROUP` | 6 |
| `TBL_ACTIVITYPRIORITY` | 5 |
| `CTL_ABL_CONNECTORTYPE` | 5 |
| `TBL_ANALYTICS_KPIGROUP` | 5 |
| `CTL_SYNCSETTYPE` | 4 |
| `CTL_SYNC_INITIALIZE_ROWSCHEMA` | 4 |
| `TBL_SETTING` | 4 |
| `TBL_SYSLOCALMESSAGE` | 4 |
| `TBL_SYNCEXTENDEDDATA` | 4 |
| `CTL_SYNCDBMAP_ROWSCHEMA` | 4 |
| `CTL_OLEDBVIEW_JOINDATA` | 3 |
| `TBL_SOCIALMEDIA` | 3 |
| `TBL_GROUP_ACTIVITY` | 2 |
| `TBL_NOTETYPE` | 2 |
| `TBL_SYNCDB` | 2 |
| `CTL_SYNCDB` | 2 |
| `TBL_COMPANY_OPPORTUNITY` | 2 |
| `TBL_CONTACT_OPPORTUNITY` | 2 |
| `TBL_PRODUCT` | 2 |
| `TBL_PROCESS` | 2 |
| `CUST_SL_COMPANY_INVOICE` | 1 |
| `TBL_ALARMSNOOZE` | 1 |
| `TBL_ACCESSOR_AEMPROFILE` | 1 |
| `CTL_CONVERSION_FILES` | 1 |
| `CTL_SYNCDBMAP` | 1 |
| `CUST_COMPANY_SL_COMPANY_INVOICE` | 1 |
| `CTL_SYNCDBMAPINFO` | 1 |
| `TBL_IMPORT_HISTORY` | 1 |
| `TBL_CONTACT_CAMPAIGN_RESULTS` | 0 |
| `CTL_CLOUD_ALARMSNOOZE_READ` | 0 |
| `TBL_ANALYTICS_PIPELINE_SETTING` | 0 |
| `CTL_USERCOLUMN_CHANGED_TRIGGER` | 0 |
| `CTL_USER_COLUMNACCESS` | 0 |
| `TBL_CONTACT_CONTACT` | 0 |
| `CTL_SYNCDBMAP_ROWFILE` | 0 |
| `TBL_CONTACT_TOPLEADS_EXCLUDE` | 0 |
| `TBL_CAMPAIGN_RESULTS` | 0 |
| `CTL_ABL_CONNECTOR_ENTITYSCHEMA` | 0 |
| `CUST_COMPANY_SL_COMPANY_SOP` | 0 |
| `CTL_USERPASSWORD_RESET` | 0 |
| `CTL_ABL_ACTIVITY` | 0 |
| `TBL_WORKFLOW_ACTIVITY_CLEARED` | 0 |
| `CTL_ABL_SCHEDULEDFOR` | 0 |
| `TBL_EXECUTE` | 0 |
| `TBL_CONTACT_SOCIALMEDIA` | 0 |
| `TBL_GROUP_OPPORTUNITY` | 0 |
| `CTL_ACTIVITY_ABL_ACTIVITY` | 0 |
| `CTL_ABL_FIELD` | 0 |
| `CTL_ABL_LINK` | 0 |
| `CTL_ABL_LINKREMAP` | 0 |
| `CTL_ABL_MASTERQUEUE_INPUT` | 0 |
| `CTL_ABL_MASTERQUEUE_OUTPUT` | 0 |
| `CUST_SL_COMPANY_SOP` | 0 |
| `CTL_ABL_MASTERQUEUE_PREFILTER` | 0 |
| `TBL_SYNCEXTENDEDDATA_TYPE` | 0 |
| `CTL_SYNCROW_EXCEPTION` | 0 |
| `TBL_WORKFLOW_SUBSCRIPTION` | 0 |
| `TBL_OPPORTUNITY_PRODUCTSERVICE` | 0 |
| `TBL_RESOURCE` | 0 |
| `TBL_WORKFLOW_ARCHIVE` | 0 |
| `TBL_PRODUCTSERVICE` | 0 |
| `TBL_SERIALNUMBER` | 0 |
| `CTL_ABL_CONNECTOR` | 0 |
| `CTL_ABL_CONNECTOR_ACCESSORCONFIG` | 0 |
| `CTL_SYNCDBMAP_ROWEXCEPTION` | 0 |
| `CTL_ABL_CONNECTOR_ENTITY` | 0 |
| `TBL_STAGE_COLOR` | 0 |
| `CTL_BI_CALENDARDATE_DIM` | 0 |
| `CTL_ABL_DEPENDENT` | 0 |
| `CTL_ABL_LINK_DEPENDENT` | 0 |
| `TBL_AL_ACTIVITY_EXTERNALID` | 0 |
| `CTL_BI_COMPANY_DIM` | 0 |
| `CTL_BI_CONTACT_DIM` | 0 |
| `CTL_BI_GROUP_DIM` | 0 |
| `CTL_BI_GEOGRAPHY_DIM` | 0 |
| `CTL_BI_HISTORY_FACT` | 0 |
| `TBL_ACTIVITYSERIES` | 0 |
| `TBL_OPPORTUNITY_ACTIVITY` | 0 |
| `TBL_OPPORTUNITY_NOTE` | 0 |
| `TBL_ACTIVITYSERIESAPPLIED` | 0 |
| `CTL_SYNCDBMAP_ROWCOMPLETED` | 0 |
| `TBL_AL_ACTIVITY` | 0 |
| `TBL_ACTIVITYSERIESITEM` | 0 |
| `TBL_AL_USERSETTING` | 0 |
| `TBL_AL_SCHEDULEDFOR` | 0 |
| `CUST_CompanyTable1_093656` | 0 |
| `TBL_AL_SYNCDATA` | 0 |
| `TBL_AL_DATAMAPPING` | 0 |
| `CTL_BI_OPPORTUNITY_FACT` | 0 |
| `TBL_AL_LINK` | 0 |
| `CTL_BI_INDUSTRY_DIM` | 0 |
| `CTL_BI_OPPORTUNITY_DIM` | 0 |
| `CTL_BI_HISTORYTYPE_DIM` | 0 |
| `CTL_BI_OPPORTUNITYSTATUS_DIM` | 0 |
| `TBL_AL_DRIVERCONFIG` | 0 |
| `CTL_BI_USER_DIM` | 0 |
| `CTL_WF_INSTANCESTATE` | 0 |
| `TBL_CONTACT_SOURCE` | 0 |
| `CTL_WF_COMPLETEDSCOPE` | 0 |

## Business/domain tables — full column detail
Every column, every business-relevant table, as restored. PK columns marked **bold**. Row count from the table above shown per table.

### `CUST_COMPANY_SL_COMPANY_INVOICE`  (rows: 1)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **SL_COMPANY_INVOICEID** | uniqueidentifier | 16 | no | ✓ |

### `CUST_COMPANY_SL_COMPANY_SOP`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **SL_COMPANY_SOPID** | uniqueidentifier | 16 | no | ✓ |

### `CUST_CompanyTable1_093656`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |

### `CUST_CONTACT_SL_CONTACT_INVOICE`  (rows: 19)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **SL_CONTACT_INVOICEID** | uniqueidentifier | 16 | no | ✓ |

### `CUST_CONTACT_SL_CONTACT_SOP`  (rows: 7)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **SL_CONTACT_SOPID** | uniqueidentifier | 16 | no | ✓ |

### `CUST_ContactTable1_100939`  (rows: 1509)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| CUST_Industryevents_015336045 | nvarchar | 800 | yes |  |
| CUST_Region_042802448 | nvarchar | 100 | yes |  |

### `CUST_SL_COMPANY_INVOICE`  (rows: 1)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SL_COMPANY_INVOICEID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| CUST_SL_INVOICE_NUMBER_093943607 | int | 4 | yes |  |
| CUST_SL_ACCOUNT_REF_093945606 | nvarchar | 16 | yes |  |
| CUST_SL_INVOICE_DATE_093946580 | datetime | 8 | yes |  |
| CUST_SL_ORDER_NUMBER_093948707 | nvarchar | 14 | yes |  |
| CUST_SL_ITEMS_NET_093949763 | decimal | 9 | yes |  |
| CUST_SL_ITEMS_TAX_093951637 | decimal | 9 | yes |  |
| CUST_SL_CARR_NET_093952772 | decimal | 9 | yes |  |
| CUST_SL_CARR_TAX_093954645 | decimal | 9 | yes |  |
| CUST_SL_POSTED_CODE_093955976 | int | 4 | yes |  |
| CUST_SL_TAKEN_BY_093957977 | nvarchar | 120 | yes |  |
| CUST_SL_INVOICE_TYPE_CODE_093959244 | int | 4 | yes |  |
| CUST_SL_CUST_ORDER_NUMBER_094001391 | nvarchar | 120 | yes |  |

### `CUST_SL_COMPANY_SOP`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SL_COMPANY_SOPID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| CUST_SL_ACCOUNT_REF_093903811 | nvarchar | 16 | yes |  |
| CUST_SL_ORDER_NUMBER_093905962 | int | 4 | yes |  |
| CUST_SL_ORDER_DATE_093907316 | datetime | 8 | yes |  |
| CUST_SL_ORDER_TYPE_CODE_093908968 | int | 4 | yes |  |
| CUST_SL_INVOICE_NUMBER_093910060 | nvarchar | 14 | yes |  |
| CUST_SL_CUST_ORDER_NUMBER_093911871 | nvarchar | 120 | yes |  |
| CUST_SL_INVOICE_GROSS_093913008 | decimal | 9 | yes |  |
| CUST_SL_INVOICE_NET_093914921 | decimal | 9 | yes |  |
| CUST_SL_TAKEN_BY_093917892 | nvarchar | 120 | yes |  |
| CUST_SL_DESPATCH_DATE_093919856 | datetime | 8 | yes |  |
| CUST_SL_GLOBAL_DEPT_NUMBER_093921156 | int | 4 | yes |  |

### `CUST_SL_CONTACT_INVOICE`  (rows: 19)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SL_CONTACT_INVOICEID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| CUST_SL_INVOICE_NUMBER_094058793 | int | 4 | yes |  |
| CUST_SL_ACCOUNT_REF_094100890 | nvarchar | 16 | yes |  |
| CUST_SL_INVOICE_DATE_094102156 | datetime | 8 | yes |  |
| CUST_SL_ORDER_NUMBER_094104016 | nvarchar | 14 | yes |  |
| CUST_SL_ITEMS_NET_094105246 | decimal | 9 | yes |  |
| CUST_SL_ITEMS_TAX_094107047 | decimal | 9 | yes |  |
| CUST_SL_CARR_NET_094108267 | decimal | 9 | yes |  |
| CUST_SL_CARR_TAX_094110122 | decimal | 9 | yes |  |
| CUST_SL_POSTED_CODE_094111365 | int | 4 | yes |  |
| CUST_SL_TAKEN_BY_094113325 | nvarchar | 120 | yes |  |
| CUST_SL_INVOICE_TYPE_CODE_094114654 | int | 4 | yes |  |
| CUST_SL_CUST_ORDER_NUMBER_094116749 | nvarchar | 120 | yes |  |

### `CUST_SL_CONTACT_SOP`  (rows: 7)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SL_CONTACT_SOPID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| CUST_SL_ACCOUNT_REF_094019499 | nvarchar | 16 | yes |  |
| CUST_SL_ORDER_NUMBER_094021416 | int | 4 | yes |  |
| CUST_SL_ORDER_DATE_094023399 | datetime | 8 | yes |  |
| CUST_SL_ORDER_TYPE_CODE_094025074 | int | 4 | yes |  |
| CUST_SL_INVOICE_NUMBER_094026663 | nvarchar | 14 | yes |  |
| CUST_SL_CUST_ORDER_NUMBER_094028440 | nvarchar | 120 | yes |  |
| CUST_SL_INVOICE_GROSS_094029549 | decimal | 9 | yes |  |
| CUST_SL_INVOICE_NET_094031398 | decimal | 9 | yes |  |
| CUST_SL_TAKEN_BY_094032621 | nvarchar | 120 | yes |  |
| CUST_SL_DESPATCH_DATE_094034573 | datetime | 8 | yes |  |
| CUST_SL_GLOBAL_DEPT_NUMBER_094035911 | int | 4 | yes |  |

### `TBL_ACTIVITY`  (rows: 2071)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |
| ACTIVITYTYPEID | smallint | 2 | no |  |
| ACTIVITYSERIESAPPLIEDID | uniqueidentifier | 16 | yes |  |
| REGARDING | nvarchar | 512 | yes |  |
| STARTTIME | smalldatetime | 4 | no |  |
| ENDTIME | smalldatetime | 4 | no |  |
| ORIGINALTIME | smalldatetime | 4 | no |  |
| ISTIMELESS | bit | 1 | no |  |
| LOCATION | nvarchar | 256 | yes |  |
| ISPRIVATE | tinyint | 1 | no |  |
| ORGANIZEUSERID | uniqueidentifier | 16 | no |  |
| DETAILS | nvarchar | -1 | yes |  |
| MASTERACTIVITYID | uniqueidentifier | 16 | no |  |
| PARENTACTIVITYID | uniqueidentifier | 16 | yes |  |
| RECURSOURCEACTIVITYID | uniqueidentifier | 16 | yes |  |
| ISEVENT | bit | 1 | no |  |
| SOURCENUM | tinyint | 1 | no |  |
| EXTERNALID | varchar | 1024 | yes |  |
| RECURPERIOD | tinyint | 1 | no |  |
| RECURFREQ | tinyint | 1 | yes |  |
| RECURMODIFIER | tinyint | 1 | yes |  |
| RECURDAY | tinyint | 1 | yes |  |
| RECURDAYTYPE | tinyint | 1 | yes |  |
| RECURMONTH | tinyint | 1 | yes |  |
| RECURENDDATE | datetime | 8 | no |  |
| ISRECURENDLESS | bit | 1 | no |  |
| ISDELETED | bit | 1 | no |  |
| DELETED_DATES | nvarchar | -1 | yes |  |
| TZ_BIAS | smallint | 2 | no |  |
| TZ_DAYLIGHT_BIAS | smallint | 2 | no |  |
| TZ_STANDARD_BIAS | smallint | 2 | no |  |
| TZ_DAYLIGHT_MONTH | tinyint | 1 | no |  |
| TZ_DAYLIGHT_DOW | tinyint | 1 | no |  |
| TZ_DAYLIGHT_DAY | tinyint | 1 | no |  |
| TZ_DAYLIGHT_HOUR | tinyint | 1 | no |  |
| TZ_DAYLIGHT_MINUTE | tinyint | 1 | no |  |
| TZ_STANDARD_MONTH | tinyint | 1 | no |  |
| TZ_STANDARD_DOW | tinyint | 1 | no |  |
| TZ_STANDARD_DAY | tinyint | 1 | no |  |
| TZ_STANDARD_HOUR | tinyint | 1 | no |  |
| TZ_STANDARD_MINUTE | tinyint | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| DURATION | int | 4 | yes |  |
| ISINVITATIONSENT | bit | 1 | no |  |
| WF_CONTEXTID | uniqueidentifier | 16 | yes |  |
| WF_INSTANCEID | uniqueidentifier | 16 | yes |  |
| CALENDARUID | nvarchar | 1024 | yes |  |
| SCHEDULEUPDATEDAT | datetime | 8 | yes |  |

### `TBL_ACTIVITYPRIORITY`  (rows: 5)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYPRIORITYGUID** | uniqueidentifier | 16 | no | ✓ |
| ACTIVITYPRIORITYID | tinyint | 1 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 128 | yes |  |
| ISACTIVE | bit | 1 | no |  |
| ORDINAL | tinyint | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_ACTIVITYSERIES`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYSERIESID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 512 | yes |  |
| ISPRIVATE | bit | 1 | no |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_ACTIVITYSERIESAPPLIED`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYSERIESAPPLIEDID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 128 | no |  |
| ACTIVITYSERIESID | uniqueidentifier | 16 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |

### `TBL_ACTIVITYSERIESITEM`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYSERIESITEMID** | uniqueidentifier | 16 | no | ✓ |
| ACTIVITYSERIESID | uniqueidentifier | 16 | no |  |
| ACTIVITYTYPEID | smallint | 2 | yes |  |
| ACTIVITYPRIORITYID | tinyint | 1 | no |  |
| DURATION | int | 4 | no |  |
| ANCHOROFFSET | smallint | 2 | no |  |
| ANCHOROFFSETPERIOD | tinyint | 1 | no |  |
| REGARDING | nvarchar | 512 | yes |  |
| ISALARMED | bit | 1 | no |  |
| LEADMINUTES | int | 4 | yes |  |
| ISTIMELESS | bit | 1 | no |  |
| ISNOWEEKENDS | bit | 1 | no |  |
| BANNERCOLOR | int | 4 | yes |  |
| ORGANIZEUSERID | uniqueidentifier | 16 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_ACTIVITYTYPE`  (rows: 6)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ACTIVITYTYPEGUID** | uniqueidentifier | 16 | no | ✓ |
| ACTIVITYTYPEID | smallint | 2 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| ISACTIVE | bit | 1 | no |  |
| ISCUSTOM | bit | 1 | no |  |
| REGARDING_PICKLISTID | uniqueidentifier | 16 | no |  |
| TYPEIMAGE | varbinary | -1 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_ADDRESS`  (rows: 84177)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ADDRESSID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| LINE1 | nvarchar | 512 | yes |  |
| LINE2 | nvarchar | 512 | yes |  |
| LINE3 | nvarchar | 512 | yes |  |
| CITY | nvarchar | 512 | yes |  |
| STATE | nvarchar | 512 | yes |  |
| POSTALCODE | nvarchar | 512 | yes |  |
| COUNTRYNAME | nvarchar | 512 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |
| LONGITUDE | decimal | 5 | yes |  |
| LATITUDE | decimal | 5 | yes |  |
| GEOLOCATION | geography | -1 | yes |  |

### `TBL_ATTACHMENT`  (rows: 215)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ATTACHMENTID** | uniqueidentifier | 16 | no | ✓ |
| FILENAME | nvarchar | 510 | no |  |
| DISPLAYNAME | nvarchar | 510 | no |  |
| NOTEID | uniqueidentifier | 16 | yes |  |
| ACTIVITYID | uniqueidentifier | 16 | yes |  |
| HISTORYID | uniqueidentifier | 16 | yes |  |
| MACHINENAME | nvarchar | 510 | yes |  |
| FILEPATH | nvarchar | 4096 | yes |  |
| WORKFLOWDEFID | uniqueidentifier | 16 | yes |  |

### `TBL_CAMPAIGN_RESULTS`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CAMPAIGN_RESULTSID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| TYPENUM | tinyint | 1 | yes |  |
| URL | nvarchar | 4000 | yes |  |
| RECIPIENT_EMAIL | nvarchar | 500 | yes |  |
| CAMPAIGNID | uniqueidentifier | 16 | yes |  |
| CAMPAIGN_NAME | nvarchar | 500 | yes |  |
| SUBJECT_LINE | nvarchar | 300 | yes |  |
| SENDDATE | datetime | 8 | yes |  |
| LASTCLICKDATE | datetime | 8 | yes |  |
| CLICKS | int | 4 | yes |  |
| OPENS | int | 4 | yes |  |
| OPENDATE | datetime | 8 | yes |  |
| ISBOUNCED | bit | 1 | no |  |
| ISUNSUBSCRIBED | bit | 1 | no |  |
| HASCOMPLAINED | bit | 1 | no |  |
| SENDER_EMAIL | nvarchar | 500 | yes |  |
| JUMPTO_URL | nvarchar | 4000 | yes |  |
| CAMPAIGN_EMAILID | uniqueidentifier | 16 | no |  |

### `TBL_COMPANY`  (rows: 10370)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 256 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| CATEGORY | nvarchar | 512 | yes |  |
| REFERREDBY | nvarchar | 128 | yes |  |
| TICKERSYMBOL | nvarchar | 24 | yes |  |
| NUMEMPLOYEES | int | 4 | yes |  |
| INDUSTRY | nvarchar | 128 | yes |  |
| SICCODE | nvarchar | 16 | yes |  |
| REVENUE | decimal | 9 | yes |  |
| TERRITORY | nvarchar | 128 | yes |  |
| REGION | nvarchar | 128 | yes |  |
| DIVISION | nvarchar | 128 | yes |  |
| WEBADDRESS | nvarchar | 256 | yes |  |
| HIERLEVEL | int | 4 | yes |  |
| HIERPATH | varchar | 556 | yes |  |
| HASSUBCOMPANY | bit | 1 | no |  |
| CONTACTQUERYTEXT | nvarchar | -1 | yes |  |
| OPPQUERYTEXT | nvarchar | -1 | yes |  |
| QUERYVERSIONID | uniqueidentifier | 16 | no |  |
| PARENTCOMPANYID | uniqueidentifier | 16 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| ISPRIVATE | bit | 1 | no |  |
| IMPORTDATE | datetime | 8 | yes |  |
| CUST_SL_ACCOUNT_REF_093337006 | nvarchar | 16 | yes |  |
| CUST_SL_NAME_093348011 | nvarchar | 120 | yes |  |
| CUST_SL_CONTACT_NAME_093349661 | nvarchar | 60 | yes |  |
| CUST_SL_ADDRESS_1_093352783 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_2_093354266 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_3_093357642 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_4_093359615 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_5_093402626 | nvarchar | 120 | yes |  |
| CUST_SL_TELEPHONE_093404556 | nvarchar | 60 | yes |  |
| CUST_SL_TELEPHONE_2_093408472 | nvarchar | 60 | yes |  |
| CUST_SL_FAX_093410678 | nvarchar | 60 | yes |  |
| CUST_SL_E_MAIL_093413537 | nvarchar | 510 | yes |  |
| CUST_SL_VAT_REG_NUMBER_093415579 | nvarchar | 40 | yes |  |

### `TBL_COMPANY_ACL`  (rows: 32152)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_COMPANY_ACTIVITY`  (rows: 912)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_CONTACT`  (rows: 7959)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_COMPANY_HISTORY`  (rows: 213208)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_NOTE`  (rows: 68105)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_OPPORTUNITY`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| ISMEMBER | bit | 1 | no |  |

### `TBL_COMPANYCONTACT_MAP`  (rows: 9)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANY_COLUMNID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACT_COLUMNID** | uniqueidentifier | 16 | no | ✓ |
| ISCUSTOM | bit | 1 | no |  |
| ISACTIVE | bit | 1 | no |  |
| ISMANDATORY | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_COMPANYQUERY`  (rows: 10)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYQUERYID** | uniqueidentifier | 16 | no | ✓ |
| COMPANYID | uniqueidentifier | 16 | no |  |
| QUERYVERSIONID | uniqueidentifier | 16 | no |  |
| ORDINAL | smallint | 2 | no |  |
| LEFTPAREN | tinyint | 1 | no |  |
| RIGHTPAREN | tinyint | 1 | no |  |
| LOGICALOPERATOR | tinyint | 1 | no |  |
| COLUMNID | uniqueidentifier | 16 | no |  |
| OPERATORID | tinyint | 1 | no |  |
| VALUEID1 | tinyint | 1 | yes |  |
| VALUEID2 | tinyint | 1 | yes |  |
| VALUESTRING1 | nvarchar | 1000 | yes |  |
| VALUESTRING2 | nvarchar | 1000 | yes |  |

### `TBL_CONTACT`  (rows: 77464)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| TYPENUM | tinyint | 1 | no |  |
| LASTNAME | nvarchar | 256 | yes |  |
| FIRSTNAME | nvarchar | 128 | yes |  |
| MIDDLENAME | nvarchar | 128 | yes |  |
| NAMEPREFIX | nvarchar | 64 | yes |  |
| NAMESUFFIX | nvarchar | 64 | yes |  |
| SALUTATION | nvarchar | 64 | yes |  |
| FULLNAME | nvarchar | 256 | yes |  |
| CATEGORY | nvarchar | 512 | yes |  |
| ISPRIVATE | bit | 1 | no |  |
| ISIMPORTED | bit | 1 | no |  |
| JOBTITLE | nvarchar | 256 | yes |  |
| DEPARTMENT | nvarchar | 256 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| COMPANYNAME | nvarchar | 256 | yes |  |
| CONTACTWEBADDRESS | nvarchar | 256 | yes |  |
| LASTMEETDATE | datetime | 8 | yes |  |
| LASTREACHDATE | datetime | 8 | yes |  |
| LASTATTEMPTDATE | datetime | 8 | yes |  |
| LASTLETTERDATE | datetime | 8 | yes |  |
| LASTRESULTS | nvarchar | 508 | yes |  |
| REFERREDBY | nvarchar | 128 | yes |  |
| SPOUSENAME | nvarchar | 100 | yes |  |
| BIRTHDATE | datetime | 8 | yes |  |
| INSTANTMSGID | nvarchar | 32 | yes |  |
| USER1 | nvarchar | 100 | yes |  |
| USER2 | nvarchar | 100 | yes |  |
| USER3 | nvarchar | 100 | yes |  |
| USER4 | nvarchar | 100 | yes |  |
| USER5 | nvarchar | 100 | yes |  |
| USER6 | nvarchar | 100 | yes |  |
| USER7 | nvarchar | 150 | yes |  |
| USER8 | nvarchar | 150 | yes |  |
| USER9 | nvarchar | 150 | yes |  |
| USER10 | nvarchar | 100 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| CUST_User11_020248031 | nvarchar | 100 | yes |  |
| CUST_User12_020250421 | nvarchar | 100 | yes |  |
| CUST_User13_020252750 | nvarchar | 100 | yes |  |
| CUST_User14_020253703 | nvarchar | 100 | yes |  |
| CUST_User15_020256046 | nvarchar | 100 | yes |  |
| CUST_2ndLastReach_020257000 | datetime | 8 | yes |  |
| CUST_3rdLastReach_020259406 | datetime | 8 | yes |  |
| CUST_TickerSymbol_020300375 | nvarchar | 100 | yes |  |
| CUST_zipcode_020302765 | nvarchar | 100 | yes |  |
| CUST_BMINotes_093741681 | nvarchar | -1 | yes |  |
| LASTEMAILDATE | datetime | 8 | yes |  |
| ISUSER | bit | 1 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |
| CUST_VATRegNo_104355159 | nvarchar | 100 | yes |  |
| AEM_OPTOUT | bit | 1 | no |  |
| AEM_BOUNCEBACK | bit | 1 | no |  |
| ISFAVORITE | bit | 1 | no |  |
| CUST_SL_ACCOUNT_REF_100819508 | nvarchar | 16 | yes |  |
| CUST_SL_NAME_100823161 | nvarchar | 120 | yes |  |
| CUST_SL_CONTACT_NAME_100826277 | nvarchar | 60 | yes |  |
| CUST_SL_ADDRESS_1_100829462 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_2_100832373 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_3_100835651 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_4_100838637 | nvarchar | 120 | yes |  |
| CUST_SL_ADDRESS_5_100842087 | nvarchar | 120 | yes |  |
| CUST_SL_TELEPHONE_100849250 | nvarchar | 60 | yes |  |
| CUST_SL_TELEPHONE_2_100852578 | nvarchar | 60 | yes |  |
| CUST_SL_FAX_100855667 | nvarchar | 60 | yes |  |
| CUST_SL_E_MAIL_100859600 | nvarchar | 510 | yes |  |
| CUST_SL_VAT_REG_NUMBER_100902813 | nvarchar | 40 | yes |  |
| LONGITUDE | decimal | 5 | yes |  |
| LATITUDE | decimal | 5 | yes |  |
| CUST_Spend_041525705 | nvarchar | 100 | yes |  |
| CUST_TBTMweekly_041623361 | bit | 1 | no |  |
| CUST_TBTMProducts_041643596 | bit | 1 | no |  |
| CUST_TBTMpartners_045338908 | bit | 1 | no |  |
| CUST_Check_125538556 | nvarchar | 100 | yes |  |
| CUST_PrintSubscription_015023575 | bit | 1 | no |  |
| CUST_Source_015043607 | nvarchar | 100 | yes |  |
| CUST_Areaofresponsibility_015140123 | nvarchar | 156 | yes |  |
| CUST_Travelregions_015309983 | nvarchar | 200 | yes |  |
| AMA_SCORE | int | 4 | yes |  |

### `TBL_CONTACT_ACL`  (rows: 267968)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_CONTACT_ACTIVITY`  (rows: 2333)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |
| ISINVITED | bit | 1 | no |  |

### `TBL_CONTACT_CAMPAIGN_RESULTS`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **CAMPAIGN_RESULTSID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_CONTACT_CONTACT`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID1** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID2** | uniqueidentifier | 16 | no | ✓ |
| CONTACT1ROLE | nvarchar | 256 | yes |  |
| CONTACT2ROLE | nvarchar | 256 | yes |  |
| DETAILS | nvarchar | -1 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_CONTACT_HISTORY`  (rows: 1056743)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |
| ISINVITED | bit | 1 | no |  |

### `TBL_CONTACT_NOTE`  (rows: 74924)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_CONTACT_OPPORTUNITY`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_CONTACT_SOCIALMEDIA`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTSOCIALMEDIAID** | uniqueidentifier | 16 | no | ✓ |
| SOCIALMEDIAID | uniqueidentifier | 16 | no |  |
| CONNECTIONID | nvarchar | -1 | no |  |
| CONTACTID | uniqueidentifier | 16 | no |  |
| USERACCOUNTID | nvarchar | 400 | no |  |

### `TBL_CONTACT_SOURCE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| SOURCE | smallint | 2 | no |  |
| USERID | uniqueidentifier | 16 | yes |  |

### `TBL_CONTACT_TOPLEADS_EXCLUDE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| EXCLUDE_THRU_DATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_COUNTRY`  (rows: 1246)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COUNTRYID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 256 | no |  |

### `TBL_EMAIL`  (rows: 75281)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **EMAILID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| ADDRESS | nvarchar | 512 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |

### `TBL_EVENTLOGTYPE`  (rows: 33)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **EVENTLOGTYPEID** | tinyint | 1 | no | ✓ |
| SECTION | nvarchar | 128 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |

### `TBL_EXECUTE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **EXECUTEID** | uniqueidentifier | 16 | no | ✓ |
| STATEMENT | nvarchar | -1 | yes |  |
| RUNCOUNT | int | 4 | yes |  |

### `TBL_GROUP`  (rows: 565)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 256 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| HIERLEVEL | int | 4 | yes |  |
| HIERPATH | varchar | 556 | yes |  |
| HASSUBGROUP | bit | 1 | no |  |
| CONTACTQUERYTEXT | nvarchar | -1 | yes |  |
| OPPQUERYTEXT | nvarchar | -1 | yes |  |
| QUERYVERSIONID | uniqueidentifier | 16 | no |  |
| PARENTGROUPID | uniqueidentifier | 16 | yes |  |
| ISPRIVATE | bit | 1 | no |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| CUST_Division_020311187 | nvarchar | 100 | yes |  |
| CUST_Priority_020314218 | nvarchar | 50 | yes |  |
| CUST_User1_020315390 | nvarchar | 100 | yes |  |
| CUST_User2_020317562 | nvarchar | 100 | yes |  |
| CUST_User3_020318218 | nvarchar | 100 | yes |  |
| CUST_User4_020320390 | nvarchar | 100 | yes |  |
| CUST_User5_020321078 | nvarchar | 100 | yes |  |
| CUST_User6_020323312 | nvarchar | 150 | yes |  |
| CUST_Region_020324000 | nvarchar | 100 | yes |  |
| CUST_Industry_020326218 | nvarchar | 100 | yes |  |
| CUST_SICCode_020326921 | nvarchar | 40 | yes |  |
| CUST_NumberofEmployees_020329187 | decimal | 9 | yes |  |
| CUST_Revenue_020329921 | decimal | 9 | yes |  |
| CUST_TickerSymbol_020332171 | nvarchar | 100 | yes |  |
| CUST_ReferredBy_020333234 | nvarchar | 60 | yes |  |
| CUST_WebSite_020335687 | nvarchar | 256 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |

### `TBL_GROUP_ACL`  (rows: 1990)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_GROUP_ACTIVITY`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_CONTACT`  (rows: 190506)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_HISTORY`  (rows: 547)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_NOTE`  (rows: 572)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_OPPORTUNITY`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| ISMEMBER | bit | 1 | no |  |

### `TBL_GROUPQUERY`  (rows: 7)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPQUERYID** | uniqueidentifier | 16 | no | ✓ |
| GROUPID | uniqueidentifier | 16 | no |  |
| QUERYVERSIONID | uniqueidentifier | 16 | no |  |
| ORDINAL | smallint | 2 | no |  |
| LEFTPAREN | tinyint | 1 | no |  |
| RIGHTPAREN | tinyint | 1 | no |  |
| LOGICALOPERATOR | tinyint | 1 | no |  |
| COLUMNID | uniqueidentifier | 16 | no |  |
| OPERATORID | tinyint | 1 | no |  |
| VALUEID1 | tinyint | 1 | yes |  |
| VALUEID2 | tinyint | 1 | yes |  |
| VALUESTRING1 | nvarchar | 1000 | yes |  |
| VALUESTRING2 | nvarchar | 1000 | yes |  |

### `TBL_HISTORY`  (rows: 1169998)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |
| HISTORYTYPEID | smallint | 2 | no |  |
| ISPRIVATE | tinyint | 1 | no |  |
| STARTTIME | smalldatetime | 4 | no |  |
| ENDTIME | smalldatetime | 4 | no |  |
| REGARDING | nvarchar | 512 | yes |  |
| DETAILS | nvarchar | -1 | yes |  |
| ACCESSOR_ACTIVITY_CLEAREDID | uniqueidentifier | 16 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| DURATION | int | 4 | yes |  |
| OUTLOOKID | uniqueidentifier | 16 | yes |  |

### `TBL_HISTORYTYPE`  (rows: 65)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **HISTORYTYPEGUID** | uniqueidentifier | 16 | no | ✓ |
| HISTORYTYPEID | smallint | 2 | no |  |
| ACTIVITYTYPEID | smallint | 2 | yes |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| ISACTIVE | bit | 1 | no |  |
| ISCUSTOM | bit | 1 | no |  |
| ISUSERRECORDABLE | bit | 1 | no |  |
| ISDEFAULT | bit | 1 | no |  |
| CLEARTYPENUM | tinyint | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| HISTORYTYPEGROUPID | smallint | 2 | no |  |

### `TBL_HISTORYTYPE_GROUP`  (rows: 17)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **HISTORYTYPEGROUPGUID** | uniqueidentifier | 16 | no | ✓ |
| HISTORYTYPEGROUPID | smallint | 2 | no |  |
| NAME | nvarchar | 128 | no |  |
| HISTORYTYPESUPERGROUPID | smallint | 2 | no |  |

### `TBL_HISTORYTYPE_SUPERGROUP`  (rows: 6)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **HISTORYTYPESUPERGROUPGUID** | uniqueidentifier | 16 | no | ✓ |
| HISTORYTYPESUPERGROUPID | smallint | 2 | no |  |
| NAME | nvarchar | 128 | no |  |

### `TBL_NOTE`  (rows: 112795)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |
| NOTETYPEID | smallint | 2 | no |  |
| ISPRIVATE | tinyint | 1 | no |  |
| NOTETEXT | nvarchar | -1 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| DISPLAYDATE | smalldatetime | 4 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_NOTETYPE`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **NOTETYPEGUID** | uniqueidentifier | 16 | no | ✓ |
| NOTETYPEID | smallint | 2 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| ISACTIVE | bit | 1 | no |  |
| ISCUSTOM | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_OPPORTUNITY`  (rows: 6)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 128 | yes |  |
| STATUSNUM | tinyint | 1 | no |  |
| ISPRIVATE | bit | 1 | no |  |
| OPENDATE | datetime | 8 | no |  |
| ESTIMATEDCLOSEDATE | datetime | 8 | no |  |
| ACTUALCLOSEDATE | datetime | 8 | yes |  |
| COMPETITOR | nvarchar | 256 | yes |  |
| STAGEID | uniqueidentifier | 16 | no |  |
| SOURCE | nvarchar | 128 | yes |  |
| CLOSEREASON | nvarchar | 256 | yes |  |
| TOTALEXTENDEDAMT | decimal | 9 | no |  |
| PROBABILITYPCT | tinyint | 1 | no |  |
| GROSSMARGINAMT | decimal | 9 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| USER1 | nvarchar | 128 | yes |  |
| USER2 | nvarchar | 128 | yes |  |
| USER3 | nvarchar | 128 | yes |  |
| USER4 | nvarchar | 128 | yes |  |
| USER5 | nvarchar | 128 | yes |  |
| USER6 | nvarchar | 128 | yes |  |
| USER7 | nvarchar | 128 | yes |  |
| USER8 | nvarchar | 128 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |
| WEIGHTEDAMT | decimal | 9 | no |  |
| DAYSOPEN | int | 4 | yes |  |
| STAGESTARTDATE | datetime | 8 | yes |  |
| DAYSINSTAGE | int | 4 | yes |  |
| SOURCEID | uniqueidentifier | 16 | yes |  |
| STATUS | nvarchar | 26 | yes |  |

### `TBL_OPPORTUNITY_ACL`  (rows: 18)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_OPPORTUNITY_ACTIVITY`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_OPPORTUNITY_HISTORY`  (rows: 7)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_OPPORTUNITY_NOTE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_OPPORTUNITY_PRODUCTSERVICE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **OPPORTUNITYID** | uniqueidentifier | 16 | no | ✓ |
| **PRODUCTSERVICEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_PHONE`  (rows: 106101)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PHONEID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| NUMBERVALUE | nvarchar | 64 | yes |  |
| NUMBERDISPLAY | nvarchar | 64 | yes |  |
| SUFFIX | nvarchar | 512 | yes |  |
| COUNTRYCODE | smallint | 2 | no |  |
| PHONEMASKID | uniqueidentifier | 16 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |

### `TBL_PHONEMASK`  (rows: 1265)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PHONEMASKID** | uniqueidentifier | 16 | no | ✓ |
| PHONEMASK | nvarchar | 64 | no |  |
| ISDEFAULT | bit | 1 | no |  |
| COUNTRYID | uniqueidentifier | 16 | no |  |
| ISACTIVE | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PICKLIST`  (rows: 35)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PICKLISTID** | uniqueidentifier | 16 | no | ✓ |
| ISCUSTOM | bit | 1 | no |  |
| TYPENUM | tinyint | 1 | no |  |
| ISEDITLIST | bit | 1 | no |  |
| ISAUTOINSERT | bit | 1 | no |  |
| DATATYPEID | tinyint | 1 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PICKLIST_SYSCOLUMN`  (rows: 63)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PICKLISTID** | uniqueidentifier | 16 | no | ✓ |
| **COLUMNID** | uniqueidentifier | 16 | no | ✓ |
| ISLIMITTOLIST | bit | 1 | no |  |
| ISMULTISELECT | bit | 1 | no |  |
| ISSHOWDESC | bit | 1 | no |  |
| ISTYPEAHEAD | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PICKLISTITEM`  (rows: 3110)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PICKLISTITEMID** | uniqueidentifier | 16 | no | ✓ |
| PICKLISTID | uniqueidentifier | 16 | no |  |
| NAME | nvarchar | 884 | no |  |
| DESCRIPTION | nvarchar | 256 | yes |  |
| ISCUSTOM | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PREFERENCE`  (rows: 824)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PREFERENCEID** | uniqueidentifier | 16 | no | ✓ |
| NAME | varchar | 256 | no |  |
| ISSERIALIZED | bit | 1 | no |  |
| OBJECTBINARYVALUE | varbinary | -1 | yes |  |
| OBJECTSTRINGVALUE | nvarchar | -1 | yes |  |

### `TBL_PROCESS`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PROCESSID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 512 | yes |  |
| ISACTIVE | bit | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PRODUCT`  (rows: 2)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PRODUCTID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 512 | no |  |
| DESCRIPTION | nvarchar | 2048 | yes |  |
| CODE | nvarchar | 128 | yes |  |
| TYPE | nvarchar | 256 | yes |  |
| UNITOFISSUE | nvarchar | 64 | yes |  |
| UNITCOST | decimal | 9 | no |  |
| UNITPRICE | decimal | 9 | no |  |
| PICTURE | varbinary | -1 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_PRODUCTSERVICE`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PRODUCTSERVICEID** | uniqueidentifier | 16 | no | ✓ |
| PRODUCTID | uniqueidentifier | 16 | yes |  |
| NAME | nvarchar | 512 | yes |  |
| ITEMCODE | nvarchar | 128 | yes |  |
| ITEMTYPE | nvarchar | 256 | yes |  |
| QUANTITY | decimal | 9 | no |  |
| UNITCOST | decimal | 9 | no |  |
| UNITPRICE | decimal | 9 | no |  |
| UNITDISCOUNT | decimal | 9 | no |  |
| DISCOUNTTYPENUM | tinyint | 1 | no |  |
| DISCOUNTPRICE | decimal | 9 | no |  |
| EXTENDEDAMT | decimal | 9 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| DISCOUNTTYPE | nvarchar | 20 | yes |  |

### `TBL_SECONDARY`  (rows: 60)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SECONDARYID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |

### `TBL_SERIALNUMBER`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SERIALNUMBERID** | uniqueidentifier | 16 | no | ✓ |
| SERIALNUMBER | nvarchar | 128 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |

### `TBL_SETTING`  (rows: 4)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SETTINGID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 900 | no |  |
| SETTINGSTRINGVALUE | nvarchar | -1 | yes |  |
| EDITUSERID | uniqueidentifier | 16 | no |  |
| EDITDATE | datetime | 8 | no |  |

### `TBL_SOCIALMEDIA`  (rows: 3)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **SOCIALMEDIAID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | -1 | yes |  |
| DISPLAYNAME | nvarchar | -1 | yes |  |

### `TBL_STAGE`  (rows: 17)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **STAGEID** | uniqueidentifier | 16 | no | ✓ |
| PROCESSID | uniqueidentifier | 16 | no |  |
| ORDINAL | int | 4 | no |  |
| NAME | nvarchar | 128 | no |  |
| DESCRIPTION | nvarchar | 512 | yes |  |
| PROBABILITYPCT | tinyint | 1 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |

### `TBL_STAGE_COLOR`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **USERID** | uniqueidentifier | 16 | no | ✓ |
| **STAGEID** | uniqueidentifier | 16 | no | ✓ |
| COLOR | int | 4 | no |  |

### `TBL_STAGE_HISTORY`  (rows: 10)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **STAGE_HISTORYID** | uniqueidentifier | 16 | no | ✓ |
| OPPORTUNITYID | uniqueidentifier | 16 | no |  |
| STAGEFROMID | uniqueidentifier | 16 | yes |  |
| STAGETOID | uniqueidentifier | 16 | yes |  |
| WEIGHTEDAMT | decimal | 9 | yes |  |
| DATECHANGED | datetime | 8 | yes |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |

## Foreign key map (business tables)
| Parent table.column | → | Referenced table.column |
|---|---|---|
| `CUST_COMPANY_SL_COMPANY_INVOICE`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `CUST_COMPANY_SL_COMPANY_INVOICE`.SL_COMPANY_INVOICEID | → | `CUST_SL_COMPANY_INVOICE`.SL_COMPANY_INVOICEID |
| `CUST_COMPANY_SL_COMPANY_SOP`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `CUST_COMPANY_SL_COMPANY_SOP`.SL_COMPANY_SOPID | → | `CUST_SL_COMPANY_SOP`.SL_COMPANY_SOPID |
| `CUST_CompanyTable1_093656`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `CUST_CONTACT_SL_CONTACT_INVOICE`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `CUST_CONTACT_SL_CONTACT_INVOICE`.SL_CONTACT_INVOICEID | → | `CUST_SL_CONTACT_INVOICE`.SL_CONTACT_INVOICEID |
| `CUST_CONTACT_SL_CONTACT_SOP`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `CUST_CONTACT_SL_CONTACT_SOP`.SL_CONTACT_SOPID | → | `CUST_SL_CONTACT_SOP`.SL_CONTACT_SOPID |
| `CUST_ContactTable1_100939`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_ACTIVITY`.ACTIVITYSERIESAPPLIEDID | → | `TBL_ACTIVITYSERIESAPPLIED`.ACTIVITYSERIESAPPLIEDID |
| `TBL_ACTIVITY`.ACTIVITYTYPEID | → | `TBL_ACTIVITYTYPE`.ACTIVITYTYPEID |
| `TBL_ACTIVITY`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_ACTIVITY`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_ACTIVITY`.MASTERACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_ACTIVITY`.ORGANIZEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_ACTIVITY`.PARENTACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_ACTIVITY`.RECURSOURCEACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_ACTIVITYSERIESAPPLIED`.ACTIVITYSERIESID | → | `TBL_ACTIVITYSERIES`.ACTIVITYSERIESID |
| `TBL_ACTIVITYSERIESITEM`.ACTIVITYPRIORITYID | → | `TBL_ACTIVITYPRIORITY`.ACTIVITYPRIORITYID |
| `TBL_ACTIVITYSERIESITEM`.ACTIVITYSERIESID | → | `TBL_ACTIVITYSERIES`.ACTIVITYSERIESID |
| `TBL_ACTIVITYSERIESITEM`.ACTIVITYTYPEID | → | `TBL_ACTIVITYTYPE`.ACTIVITYTYPEID |
| `TBL_ACTIVITYSERIESITEM`.ORGANIZEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_ACTIVITYTYPE`.REGARDING_PICKLISTID | → | `TBL_PICKLIST`.PICKLISTID |
| `TBL_ADDRESS`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_ADDRESS`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_ADDRESS`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_ADDRESS`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_ADDRESS`.TYPEID | → | `TBL_PICKLISTITEM`.PICKLISTITEMID |
| `TBL_ATTACHMENT`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_ATTACHMENT`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_ATTACHMENT`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_ATTACHMENT`.WORKFLOWDEFID | → | `TBL_WORKFLOWDEF`.WORKFLOWDEFID |
| `TBL_COMPANY`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_COMPANY`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_COMPANY`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_COMPANY`.PARENTCOMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_ACL`.ACCESSORID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_COMPANY_ACL`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_ACTIVITY`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_COMPANY_ACTIVITY`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_CONTACT`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_CONTACT`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_COMPANY_HISTORY`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_HISTORY`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_COMPANY_NOTE`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_NOTE`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_COMPANY_OPPORTUNITY`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANY_OPPORTUNITY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_COMPANYQUERY`.COLUMNID | → | `TBL_SYSCOLUMN`.COLUMNID |
| `TBL_COMPANYQUERY`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_COMPANYQUERY`.VALUEID2 | → | `TBL_SYSVALUE`.VALUEID |
| `TBL_COMPANYQUERY`.OPERATORID | → | `TBL_SYSOPERATOR`.OPERATORID |
| `TBL_COMPANYQUERY`.VALUEID1 | → | `TBL_SYSVALUE`.VALUEID |
| `TBL_CONTACT`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_CONTACT`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_CONTACT`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_CONTACT`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_CONTACT_ACL`.ACCESSORID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_CONTACT_ACL`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_ACTIVITY`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_CONTACT_ACTIVITY`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_CAMPAIGN_RESULTS`.CAMPAIGN_RESULTSID | → | `TBL_CAMPAIGN_RESULTS`.CAMPAIGN_RESULTSID |
| `TBL_CONTACT_CAMPAIGN_RESULTS`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_HISTORY`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_HISTORY`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_CONTACT_NOTE`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_NOTE`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_CONTACT_OPPORTUNITY`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_OPPORTUNITY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_CONTACT_SOCIALMEDIA`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_SOCIALMEDIA`.SOCIALMEDIAID | → | `TBL_SOCIALMEDIA`.SOCIALMEDIAID |
| `TBL_CONTACT_SOURCE`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_CONTACT_SOURCE`.USERID | → | `TBL_USER`.USERID |
| `TBL_EMAIL`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_EMAIL`.TYPEID | → | `TBL_PICKLISTITEM`.PICKLISTITEMID |
| `TBL_EMAIL`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_EMAIL`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_EMAIL`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_GROUP`.PARENTGROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_GROUP`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_GROUP`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_GROUP_ACL`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP_ACL`.ACCESSORID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_GROUP_ACTIVITY`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP_ACTIVITY`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_GROUP_CONTACT`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP_CONTACT`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_GROUP_HISTORY`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_GROUP_HISTORY`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP_NOTE`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_GROUP_NOTE`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUP_OPPORTUNITY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_GROUP_OPPORTUNITY`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUPQUERY`.VALUEID2 | → | `TBL_SYSVALUE`.VALUEID |
| `TBL_GROUPQUERY`.VALUEID1 | → | `TBL_SYSVALUE`.VALUEID |
| `TBL_GROUPQUERY`.OPERATORID | → | `TBL_SYSOPERATOR`.OPERATORID |
| `TBL_GROUPQUERY`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_GROUPQUERY`.COLUMNID | → | `TBL_SYSCOLUMN`.COLUMNID |
| `TBL_HISTORY`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_HISTORY`.HISTORYTYPEID | → | `TBL_HISTORYTYPE`.HISTORYTYPEID |
| `TBL_HISTORY`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_HISTORY`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_HISTORYTYPE`.ACTIVITYTYPEID | → | `TBL_ACTIVITYTYPE`.ACTIVITYTYPEID |
| `TBL_HISTORYTYPE`.HISTORYTYPEGROUPID | → | `TBL_HISTORYTYPE_GROUP`.HISTORYTYPEGROUPID |
| `TBL_HISTORYTYPE_GROUP`.HISTORYTYPESUPERGROUPID | → | `TBL_HISTORYTYPE_SUPERGROUP`.HISTORYTYPESUPERGROUPID |
| `TBL_NOTE`.NOTETYPEID | → | `TBL_NOTETYPE`.NOTETYPEID |
| `TBL_NOTE`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_NOTE`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY`.STAGEID | → | `TBL_STAGE`.STAGEID |
| `TBL_OPPORTUNITY`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY_ACL`.ACCESSORID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY_ACL`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_ACTIVITY`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_OPPORTUNITY_ACTIVITY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_HISTORY`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_OPPORTUNITY_HISTORY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_NOTE`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_OPPORTUNITY_NOTE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_PRODUCTSERVICE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_PRODUCTSERVICE`.PRODUCTSERVICEID | → | `TBL_PRODUCTSERVICE`.PRODUCTSERVICEID |
| `TBL_PHONE`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_PHONE`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_PHONE`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_PHONE`.TYPEID | → | `TBL_PICKLISTITEM`.PICKLISTITEMID |
| `TBL_PHONE`.PHONEMASKID | → | `TBL_PHONEMASK`.PHONEMASKID |
| `TBL_PHONE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_PHONEMASK`.COUNTRYID | → | `TBL_COUNTRY`.COUNTRYID |
| `TBL_PICKLIST`.DATATYPEID | → | `TBL_SYSDATATYPE`.DATATYPEID |
| `TBL_PICKLIST_SYSCOLUMN`.COLUMNID | → | `TBL_SYSCOLUMN`.COLUMNID |
| `TBL_PICKLIST_SYSCOLUMN`.PICKLISTID | → | `TBL_PICKLIST`.PICKLISTID |
| `TBL_PICKLISTITEM`.PICKLISTID | → | `TBL_PICKLIST`.PICKLISTID |
| `TBL_PRODUCTSERVICE`.PRODUCTID | → | `TBL_PRODUCT`.PRODUCTID |
| `TBL_STAGE`.PROCESSID | → | `TBL_PROCESS`.PROCESSID |
| `TBL_STAGE_COLOR`.STAGEID | → | `TBL_STAGE`.STAGEID |
| `TBL_STAGE_COLOR`.USERID | → | `TBL_USER`.USERID |
| `TBL_STAGE_HISTORY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_STAGE_HISTORY`.STAGETOID | → | `TBL_STAGE`.STAGEID |
| `TBL_STAGE_HISTORY`.STAGEFROMID | → | `TBL_STAGE`.STAGEID |

## Decoded picklists / dropdown values
Act! stores dropdown/select-field values here (`TBL_PICKLIST` + `TBL_PICKLISTITEM`), separate from the column definition. These are the real allowed values behind fields like Contact/Company `CATEGORY`, address/phone/email `TYPEID`, etc. Very large lookups (`Cities` 1386 items, `Jobtitles` 1029, `Countries` 274, `Counties` 93, `First Name Prefixes` 39) are omitted here for size — pull them from `TBL_PICKLIST`/`TBL_PICKLISTITEM` directly if needed during ETL.

| Picklist | Value |
|---|---|
| Access Level | Limited |
| Access Level | Private |
| Access Level | Public |
| Address Types | Billing |
| Address Types | Business |
| Address Types | Home |
| Address Types | Shipping |
| Busin. Cat. | Airline |
| Busin. Cat. | Airline Caterer |
| Busin. Cat. | Association |
| Busin. Cat. | Attraction |
| Busin. Cat. | Car Hire |
| Busin. Cat. | Catering Equipment |
| Busin. Cat. | Chocolate/Dairy |
| Busin. Cat. | Consultancy |
| Busin. Cat. | Cruise |
| Busin. Cat. | Exhibitions |
| Busin. Cat. | F&B Meat Products/Poultry |
| Busin. Cat. | F&B Miscellaneous |
| Busin. Cat. | F&B Wine/Champagne |
| Busin. Cat. | Furniture |
| Busin. Cat. | Hardware Suppliers |
| Busin. Cat. | Hotel |
| Busin. Cat. | Hygiene |
| Busin. Cat. | IFH Advertisers |
| Busin. Cat. | Insurance |
| Busin. Cat. | Miscellaneous |
| Busin. Cat. | National Tour Op |
| Busin. Cat. | PR |
| Busin. Cat. | Recruitment |
| Busin. Cat. | Seafood |
| Busin. Cat. | Tabletop |
| Busin. Cat. | Technology |
| Busin. Cat. | Toiletries |
| Busin. Cat. | Tour Operator |
| Busin. Cat. | Travel Agents |
| Busin. Cat. | Uniforms |
| Busin. Cat. | University/Colleges |
| Call Regarding | Cold call |
| Call Regarding | Confirm appointment |
| Call Regarding | Confirm shipment |
| Call Regarding | Discuss legal points |
| Call Regarding | Follow up |
| Call Regarding | Get the order |
| Call Regarding | Give quote |
| Call Regarding | Request updated catalog |
| Call Regarding | Request updated prices |
| Call Regarding | Returning call |
| Call Regarding | Schedule a meeting |
| Call Regarding | Thank you |
| Company ID/Status | Cold Lead |
| Company ID/Status | Competitor |
| Company ID/Status | Consultants |
| Company ID/Status | Contractor |
| Company ID/Status | Customer |
| Company ID/Status | Distributor |
| Company ID/Status | Hot Lead |
| Company ID/Status | Key Customer |
| Company ID/Status | Lead |
| Company ID/Status | Manufacturer |
| Company ID/Status | Prospect |
| Company ID/Status | Qualified Lead |
| Company ID/Status | Reseller |
| Company ID/Status | Resource |
| Company ID/Status | Retailer |
| Company ID/Status | Supplier |
| Company ID/Status | Vendor |
| Company ID/Status | Warm Lead |
| Company ID/Status | Wholesaler |
| Contact ID/Status | Competitor |
| Contact ID/Status | Customer |
| Contact ID/Status | Director |
| Contact ID/Status | Distributor |
| Contact ID/Status | Friend |
| Contact ID/Status | Investor |
| Contact ID/Status | Manufacturer |
| Contact ID/Status | Personal |
| Contact ID/Status | Prospect |
| Contact ID/Status | Shareholder |
| Contact ID/Status | Supplier |
| Contact ID/Status | Vendor |
| Contact Relations | Assistant |
| Contact Relations | Business Partner |
| Contact Relations | Client |
| Contact Relations | Consultant |
| Contact Relations | Coworker |
| Contact Relations | Employee |
| Contact Relations | Family |
| Contact Relations | Friend |
| Contact Relations | Manager |
| Contact Relations | Spouse |
| Contact Relations | Vendor |
| Departments | 00 965 252 0600 |
| Departments | 0207 430 6148 |
| Departments | Administration |
| Departments | Airline |
| Departments | Cold Drinks/Southwest Fountain |
| Departments | Corporate |
| Departments | Department |
| Departments | Domestic Marketing Department |
| Departments | Engineering |
| Departments | Finance/Accounting |
| Departments | Florida & Bahamas |
| Departments | Human Resources |
| Departments | International & Domestic Trade |
| Departments | Legal |
| Departments | Leisure Sales |
| Departments | Long Haul Division |
| Departments | Manufacturing |
| Departments | Marketing |
| Departments | Marketing Manager |
| Departments | Miami & Daytona Beach Locations |
| Departments | Military/Transportation Channel Sales |
| Departments | Montserrat Government UK Office |
| Departments | National Accounts |
| Departments | Office of Culture Affairs/Tourism Develo |
| Departments | Press 2 then 5 |
| Departments | Procter & Gamble |
| Departments | Proctor & Gamble |
| Departments | Production |
| Departments | Purchasing |
| Departments | Sales |
| Departments | Sales - Canada |
| Departments | Sales & Marketing |
| Departments | Selling Long Haul |
| Departments | Selling Short Breaks |
| Departments | Service |
| Departments | Shipping |
| Departments | The Carribean |
| Departments | Travel Industry Sales |
| Departments | Travel Industry UK |
| Departments | Travel Uni |
| Departments | Wholesaler Marketing |
| Departments | Zentralbereich |
| EMail Types | Business |
| EMail Types | E-Mail 2 |
| EMail Types | E-Mail 3 |
| EMail Types | E-Mail 4 |
| EMail Types | Personal |
| Industry | Advertising/Marketing |
| Industry | Automotive/Aerospace |
| Industry | Communication |
| Industry | Computers/High Tech |
| Industry | Construction |
| Industry | Distribution/Wholesale |
| Industry | Education |
| Industry | Electronics |
| Industry | Energy/Utilities |
| Industry | Entertainment |
| Industry | Financial/Insurance |
| Industry | Government/Public Sector |
| Industry | Healthcare/Medical |
| Industry | Legal |
| Industry | Manufacturing |
| Industry | Non-Profit |
| Industry | Real Estate |
| Industry | Retail/Consumer Goods |
| Industry | Services/Consulting |
| Industry | Transportation |
| Industry | Travel/Hospitality |
| Last Results | Discussed opportunities |
| Last Results | Followed up |
| Last Results | Got appointment |
| Last Results | Just received information |
| Last Results | Left message to call me back |
| Last Results | Qualified, OK to pursue |
| Last Results | Requested more information |
| Last Results | Sent literature |
| Meeting Regarding | Cold call |
| Meeting Regarding | Confirm appointment |
| Meeting Regarding | Confirm shipment |
| Meeting Regarding | Discuss legal points |
| Meeting Regarding | Follow up |
| Meeting Regarding | Get the order |
| Meeting Regarding | Give quote |
| Meeting Regarding | Request updated catalog |
| Meeting Regarding | Request updated prices |
| Meeting Regarding | Returning call |
| Meeting Regarding | Schedule a meeting |
| Meeting Regarding | Thank you |
| Personal Activity Regarding | Appointment |
| Personal Activity Regarding | Call |
| Personal Activity Regarding | Dentist Appointment |
| Personal Activity Regarding | Doctor Appointment |
| Personal Activity Regarding | Eye Doctor Appointment |
| Personal Activity Regarding | Make Appointment |
| Personal Activity Regarding | Meeting |
| Personal Activity Regarding | Parent-Teacher Conference |
| Personal Activity Regarding | Shopping |
| Personal Activity Regarding | Time Off |
| Personal Activity Regarding | Workout |
| Phone Types | Alternate |
| Phone Types | Business |
| Phone Types | Fax |
| Phone Types | Home |
| Phone Types | Mobile |
| Phone Types | Pager |
| Phone Types | Toll-Free |
| Priority Group | High |
| Priority Group | Low |
| Priority Group | Medium |
| Referred By | Advertisement |
| Referred By | Associate |
| Referred By | Called in |
| Referred By | Mailer |
| Referred By | Referral |
| Referred By | Trade show |
| Referred By Group | Advertisement |
| Referred By Group | Associate |
| Referred By Group | Called in |
| Referred By Group | Mailer |
| Referred By Group | Referral |
| Referred By Group | Trade show |
| Region | Channel Isles |
| Region | East Anglia |
| Region | East Midlands |
| Region | East Midlands |
| Region | London |
| Region | London |
| Region | Midlands |
| Region | Midlands |
| Region | North East |
| Region | North West |
| Region | Northern Ireland |
| Region | Scotland |
| Region | Scotland |
| Region | South East |
| Region | South West |
| Region | Wales |
| Region | Yorkshire |
| Territory | East |
| Territory | Mid West |
| Territory | North |
| Territory | North East |
| Territory | North West |
| Territory | South |
| Territory | South East |
| Territory | South West |
| Territory | West |
| To-do Regarding | Confirm appointment |
| To-do Regarding | Confirm shipment |
| To-do Regarding | Discuss legal points |
| To-do Regarding | Follow up |
| To-do Regarding | Get the order |
| To-do Regarding | Request updated catalog |
| To-do Regarding | Request updated prices |
| To-do Regarding | Returning call |
| To-do Regarding | Thank you |
| Vacation Regarding | Arrange For Transportation |
| Vacation Regarding | Arrival |
| Vacation Regarding | Call Travel Agent |
| Vacation Regarding | Change Voicemail Greeting |
| Vacation Regarding | Departure |
| Vacation Regarding | Flight |
| Vacation Regarding | Forward E-Mail |
| Vacation Regarding | Notify Colleagues |
| Vacation Regarding | Out Of The Office |
| Vacation Regarding | Purchase Tickets |
| Vacation Regarding | Request For Time Off |
| Vacation Regarding | Reserve a Car |
| Vacation Regarding | Reserve a Hotel Room |
| Vacation Regarding | Set-Up Out of the Office Reply |
| Vacation Regarding | Travel Arrangements |

## History types & Note types
`TBL_HISTORY.HISTORYTYPEID` and `TBL_NOTE.NOTETYPEID` are enum-style FKs into these lookup tables — needed to interpret what kind of activity a History row actually records.

### History types
```
Changed database context to 'Prospects'.
HISTORYTYPEID|NAME
-------------|----
-1|Library Document
0|Call Attempted
1|Call Completed
2|Call Received
3|Field Changed
4|Access
5|Letter Sent
6|Meeting Held
7|Meeting Not Held
8|To-do Done
9|To-do Not Done
10|Timer
11|Call Erased
12|Contact Deleted
13|Contact Updated
14|Activity Updated
15|Activity Deleted
16|E-mail Sent
17|Call Left Message
18|Access Changed
24|Personal Activity Completed
25|Personal Activity Not Completed
26|Personal Activity Postponed
27|Personal Activity Cancelled
32|Vacation Completed
33|Vacation Not Completed
34|Vacation Cancelled
37|Personal Activity Erased
39|Vacation Erased
50|Fax Sent
51|Sent Sync
52|Received Sync
53|Replace Fields Log
54|To-do Erased
55|Meeting Erased
56|Error
57|Opportunity Won
58|Opportunity Lost
59|New Opportunity
60|Opportunity Inactive
61|Opportunity Stage Update
62|Quote
63|E-mail Not Sent
64|Fax Not Sent
65|Data Moved
66|Opportunity Opened
67|Contact Linked
68|Contact Unlinked
80|Send Campaign
81|Campaign Results
82|Web Activity
83|Email Sends
84|Email Open
85|Email Click
86|Email Bounce
87|Email Unsubscribe
88|Landing Pages
101|Attachment
102|E-mail Attachment
103|Library Document Attached
104|E-mail Auto Attached
105|Photo
110|Appointment Completed
111|Appointment Not Completed
112|Appointment Erased

(65 rows affected)
```

### Note types
```
Changed database context to 'Prospects'.
NOTETYPEID|NAME
----------|----
103|AI Summary
100|Note

(2 rows affected)
```
## Custom field decode
`TBL_SYSCOLUMN` is Act!'s field catalogue — every column on every entity, including custom ones, with `ISCUSTOM`, `DISPLAYNAME` (the human label shown in the Act! UI) vs `COLUMNNAME` (the physical column, which is what SQL sees). Pull `TBL_SYSCOLUMN` during ETL and join on `COLUMNNAME` to get the true field label rather than guessing from the suffix.

`TBL_CONTACT` here has **43 custom/user fields — nearly double OnBoard's set**, and a genuinely new category not seen in OnBoard:

| Physical column | Real meaning |
|---|---|
| `USER1`–`USER10`, `CUST_User11`..`User15` | Generic legacy fields — same caution as OnBoard, do not assume meaning without checking populated values |
| `CUST_BMINotes_093741681` | `bmi_notes` — same field as OnBoard, **same suffix ID**, confirming this is a shared custom-field definition across the Act! install, not redefined per database |
| `CUST_VATRegNo_104355159`, `CUST_TickerSymbol_020300375`, `CUST_zipcode_020302765` | Same as OnBoard, same suffix IDs |
| `CUST_2ndLastReach_020257000` / `CUST_3rdLastReach_020259406` | Same as OnBoard |
| **`CUST_SL_ACCOUNT_REF`, `CUST_SL_NAME`, `CUST_SL_CONTACT_NAME`, `CUST_SL_ADDRESS_1..5`, `CUST_SL_TELEPHONE`, `CUST_SL_TELEPHONE_2`, `CUST_SL_FAX`, `CUST_SL_E_MAIL`, `CUST_SL_VAT_REG_NUMBER`** | **New — not present on OnBoard.** `SL` strongly suggests **Sage Line 50** (a UK accounting package) — a full mirrored contact record (name/address/phone/VAT) synced from an accounting system. Present on **both** `TBL_CONTACT` and `TBL_COMPANY` here. This is a real integration surface: confirm with BMI whether Sage is still in use alongside/instead of Xero, and whether this data is stale or actively synced — directly relevant to the Stage 4 Xero reporting work in the build spec. |
| `CUST_TBTMweekly_041623361`, `CUST_TBTMProducts_041643596`, `CUST_TBTMpartners_045338908` (all `bit`) | Newsletter/mailing-list subscription flags — `TBTM` matches the `TBTM Events 2026.xls` / `TBTM Print and Digital 2026.xls` files already seen in your Drive folder, so this is a real, current title/product code, not legacy cruft |
| `CUST_PrintSubscription_015023575` | Same concept as OnBoard's `CUST_Printsubscription`, different suffix ID — **custom fields are not guaranteed to share suffix IDs across databases even when conceptually identical**; match by intent/label during ETL, not by raw column name |
| `CUST_Source_015043607` | Free-text lead/contact source |
| `CUST_Areaofresponsibility_015140123`, `CUST_Travelregions_015309983` | Travel-industry-specific fields — makes sense for a shared prospects list feeding travel titles |
| `CUST_Spend_041525705`, `CUST_Check_125538556` | Unclear from name alone — flag for BMI to confirm rather than guess |

`TBL_COMPANY` custom fields here are **only** the 13 `CUST_SL_*` Sage fields (mirrored company-level version of the contact ones) — otherwise no custom fields, same as OnBoard.

`TBL_GROUP` custom fields: identical set to OnBoard (`Division`, `Priority`, `User1`-`6`, `Region`, `Industry`, `SICCode`, `NumberOfEmployees`, `Revenue`, `TickerSymbol`, `ReferredBy`, `WebSite`) — this custom-field layout is consistent across databases, unlike Contact's.

## Observations & migration notes — Prospects-specific
- **This database contradicts `CONTEXT.md`'s "0 Activities, ~7 Opportunities" assumption.** Prospects alone has **2,071 Activities** and **6 Opportunities** (vs OnBoard's 57/1). Combined so far: 2,128 Activities, 7 Opportunities across two of three databases — the "Activities/Opportunities are unused, design fresh" plan from `CONTEXT.md` needs re-confirming with BMI before we treat that data as throwaway; 2,071 Activities may hold real, in-flight task data worth preserving or reviewing before this database is discarded.
- **Real accounting-system integration data present** (`CUST_SL_*` fields, both Contact and Company) — looks like a Sage Line 50 sync/import. This is new information relevant to `CONTEXT.md`'s "Xero: not yet wired in" note — worth asking BMI whether Sage is a second, still-live accounting system alongside Xero, or legacy/retired.
- **Custom field suffix IDs are per-database, not global** — confirmed by `bmi_notes` sharing an ID with OnBoard while `PrintSubscription` does not. ETL must match custom fields by **decoded label** (via `TBL_SYSCOLUMN.DISPLAYNAME`), never by raw `CUST_*_<digits>` column name, since the same concept can carry a different suffix per source database.
- **History is 3.4x the volume of OnBoard (1.17M rows) and system noise is proportionally worse**: `Access Changed` (277k) and `Contact Deleted` (213k) are now the largest categories, `Field Changed` alone is 78k (vs OnBoard's 336) — reinforces the earlier finding that a large share of `TBL_HISTORY` is Act! audit/sync noise, not sales activity, and the filtering approach needs to be per-database (proportions differ significantly), not a fixed global rule.
- **New picklist not present on OnBoard: `Region`** (17 values) — separate from `Territory` (9 values, same on both DBs). Confirm with BMI whether Region/Territory are both meaningfully used or redundant.
- **565 Groups** (vs OnBoard's 245) and **10,370 Companies** (vs 3,892) — this database is substantially larger across the board (77,464 Contacts vs 22,535), consistent with "Prospects" being the broad ~40k-prospect pool `CONTEXT.md`/build spec describes, not a single-title list.
- Structural shape (tables, FKs, junction-table pattern for Notes/History/Address/Phone/Email, GUID PKs) is **identical to OnBoard** — confirms the "same schema shape, different content/config" expectation from the earlier session, so the eventual ETL script can be genuinely parameterized by `source_db` rather than needing per-database branches for structure.

## Act! internal/engine tables — reference list only
These 149 tables are Act!'s own application internals — sync engine (`CTL_SYNC*`, `TBL_SYNC*`), system metadata/UI definitions (`TBL_SYS*`), access control (`TBL_ACCESSOR*`, ACL tables), workflow/analytics engine, licensing, login history. None of this carries BMI business data or is a migration target — listed here only so the schema documentation is genuinely complete. Row counts are in the table above.

`CTL_ABL_ACTIVITY`, `CTL_ABL_CONNECTOR`, `CTL_ABL_CONNECTOR_ACCESSORCONFIG`, `CTL_ABL_CONNECTOR_ENTITY`, `CTL_ABL_CONNECTOR_ENTITYSCHEMA`, `CTL_ABL_CONNECTORTYPE`, `CTL_ABL_DEPENDENT`, `CTL_ABL_FIELD`, `CTL_ABL_LINK`, `CTL_ABL_LINK_DEPENDENT`, `CTL_ABL_LINKREMAP`, `CTL_ABL_MASTERQUEUE_INPUT`, `CTL_ABL_MASTERQUEUE_OUTPUT`, `CTL_ABL_MASTERQUEUE_PREFILTER`, `CTL_ABL_SCHEDULEDFOR`, `CTL_ACTIVITY_ABL_ACTIVITY`, `CTL_BI_CALENDARDATE_DIM`, `CTL_BI_COMPANY_DIM`, `CTL_BI_CONTACT_DIM`, `CTL_BI_GEOGRAPHY_DIM`, `CTL_BI_GROUP_DIM`, `CTL_BI_HISTORY_FACT`, `CTL_BI_HISTORYTYPE_DIM`, `CTL_BI_INDUSTRY_DIM`, `CTL_BI_OPPORTUNITY_DIM`, `CTL_BI_OPPORTUNITY_FACT`, `CTL_BI_OPPORTUNITYSTATUS_DIM`, `CTL_BI_USER_DIM`, `CTL_CLOUD_ALARMSNOOZE_READ`, `CTL_CONVERSION_FILES`, `CTL_DBCONFIG`, `CTL_EVENTLOG`, `CTL_EVENTLOGDETAIL`, `CTL_LOCALSTRING`, `CTL_OLEDBFUNCTION`, `CTL_OLEDBFUNCTION_SYSCOLUMN`, `CTL_OLEDBVIEW`, `CTL_OLEDBVIEW_DERIVEDCOLUMN`, `CTL_OLEDBVIEW_JOINDATA`, `CTL_OLEDBVIEW_KEYINDEX`, `CTL_OLEDBVIEW_KEYINDEX_SYSCOLUMN`, `CTL_OLEDBVIEW_OLEDBFUNCTION`, `CTL_OLEDBVIEW_PROVIDERVIEW`, `CTL_PROVIDERVIEW`, `CTL_SYNC_DEVICETABLE`, `CTL_SYNC_INITIALIZE_ROWDATA`, `CTL_SYNC_INITIALIZE_ROWSCHEMA`, `CTL_SYNCACCESSOR`, `CTL_SYNCCOLUMN`, `CTL_SYNCDB`, `CTL_SYNCDBMAP`, `CTL_SYNCDBMAP_ROWCOMPLETED`, `CTL_SYNCDBMAP_ROWDATA`, `CTL_SYNCDBMAP_ROWEXCEPTION`, `CTL_SYNCDBMAP_ROWFILE`, `CTL_SYNCDBMAP_ROWSCHEMA`, `CTL_SYNCDBMAP_SESSION`, `CTL_SYNCDBMAP_SESSIONROW`, `CTL_SYNCDBMAPINFO`, `CTL_SYNCDBMAPINFO_HISTORY`, `CTL_SYNCROW_ADD`, `CTL_SYNCROW_DELETE`, `CTL_SYNCROW_EXCEPTION`, `CTL_SYNCROW_FILE`, `CTL_SYNCROW_UPDATE`, `CTL_SYNCROW_UPDATECOLUMN`, `CTL_SYNCSETTYPE`, `CTL_SYNCTABLE`, `CTL_SYSTABLEORDER`, `CTL_USER_COLUMNACCESS`, `CTL_USERCOLUMN_CHANGED_TRIGGER`, `CTL_USERPASSWORD_RESET`, `CTL_USERSESSION`, `CTL_WF_COMPLETEDSCOPE`, `CTL_WF_INSTANCESTATE`, `TBL_ACCESSOR`, `TBL_ACCESSOR_ACTIVITY`, `TBL_ACCESSOR_ACTIVITY_CLEARED`, `TBL_ACCESSOR_AEMPROFILE`, `TBL_ACCESSOR_DELEGATE`, `TBL_ACCESSOR_PREFERENCE`, `TBL_ACCESSOR_SETTING`, `TBL_AL_ACTIVITY`, `TBL_AL_ACTIVITY_EXTERNALID`, `TBL_AL_DATAMAPPING`, `TBL_AL_DRIVERCONFIG`, `TBL_AL_LINK`, `TBL_AL_SCHEDULEDFOR`, `TBL_AL_SYNCDATA`, `TBL_AL_USERSETTING`, `TBL_ALARMSNOOZE`, `TBL_ANALYTICS_KPIGROUP`, `TBL_ANALYTICS_PIPELINE_SETTING`, `TBL_ANALYTICS_VIEW_DEFINITION`, `TBL_EXTERNALMAP_SOURCE`, `TBL_FEATURESET`, `TBL_FOLDER`, `TBL_IMPORT_HISTORY`, `TBL_IMPORT_HISTORYITEM`, `TBL_INSTALL_LOGS`, `TBL_LOGONHISTORY`, `TBL_PASSWORDHISTORY`, `TBL_PERMISSION`, `TBL_PERMISSION_DEPEND`, `TBL_RESOURCE`, `TBL_ROLE`, `TBL_ROLE_PERMISSION`, `TBL_SYNCCONTACT`, `TBL_SYNCCONTACT_ACL`, `TBL_SYNCDB`, `TBL_SYNCDBTYPE`, `TBL_SYNCEXTENDEDDATA`, `TBL_SYNCEXTENDEDDATA_TYPE`, `TBL_SYNCSET`, `TBL_SYNCSET_ACCESSOR`, `TBL_SYNCSETQUERY`, `TBL_SYNCSUBSCRIPTION`, `TBL_SYSCALCCOLUMN`, `TBL_SYSCOLUMN`, `TBL_SYSCOLUMN_ACL`, `TBL_SYSCONSTANT`, `TBL_SYSDATATYPE`, `TBL_SYSDOMAIN`, `TBL_SYSDOMAIN_SYSOPERATOR`, `TBL_SYSENTITY`, `TBL_SYSENTITY_SYSTABLE`, `TBL_SYSENTITYRELATION`, `TBL_SYSLOCALCOLUMN`, `TBL_SYSLOCALMESSAGE`, `TBL_SYSOPERATOR`, `TBL_SYSTABLE`, `TBL_SYSTABLEDOMAIN`, `TBL_SYSTABLEKEY`, `TBL_SYSTABLEKEY_SYSCOLUMN`, `TBL_SYSTABLERELATION`, `TBL_SYSVALUE`, `TBL_SYSVALUEUSAGE`, `TBL_TEAM`, `TBL_TEAM_USER`, `TBL_USER`, `TBL_USER_ACCESSOR_ENUM`, `TBL_USER_DEFAULT_ACL`, `TBL_USER_PERMISSION`, `TBL_VIRTUALRECORDTYPE`, `TBL_WORKFLOW_ACTIVITY_CLEARED`, `TBL_WORKFLOW_ARCHIVE`, `TBL_WORKFLOW_SUBSCRIPTION`, `TBL_WORKFLOWDEF`, `TBL_WORKFLOWDEF_ACL`
