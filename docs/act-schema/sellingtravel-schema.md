# Act! `SellingTravel` (SellingTravel542) — Full Database Schema Reference
Restored from `Act! SellingTravel542_RDB.zip` (Act! full database backup, SQL Server native `.BAK`), explored directly against a disposable SQL Server 2022 instance. This document is the permanent record of that exploration — the restored database itself is discarded after this.
- **Total tables:** 217  
- **Total views:** 137 (Act!'s internal query layer, not source data — not documented here)  
- **Business/domain tables** (documented in full below): 69  
- **Act! internal/engine tables** (sync engine, ACL, UI metadata, licensing — listed for completeness, not detailed): 148
## Can we restore the `.bak` straight onto our Postgres/Dokploy instance?
**No — not directly, and we should not try.** A `.bak` is a SQL Server–native binary backup format; only SQL Server can restore it (which is exactly what we did here, in a throwaway Docker container). Postgres has no restore path for it at all. Beyond the format mismatch, a byte-for-byte port wouldn't be desirable anyway:

- The schema is Act!'s **internal application schema**, not a clean business model — ~80% of these 218 tables (sync engine, ACL/permissions, UI metadata, licensing, workflow engine) are Act! product internals with zero value to us; see 'Act! internal/engine tables' below.
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
| `TBL_CONTACT_HISTORY` | 96331 |
| `TBL_HISTORY` | 95341 |
| `CTL_EVENTLOGDETAIL` | 57976 |
| `TBL_SYNCCONTACT_ACL` | 57944 |
| `CTL_SYNCROW_UPDATECOLUMN` | 55980 |
| `TBL_CONTACT_ACL` | 54194 |
| `CTL_SYNCROW_ADD` | 32843 |
| `TBL_PHONE` | 29232 |
| `TBL_SYNCCONTACT` | 19313 |
| `CTL_SYNCDBMAP_SESSIONROW` | 18071 |
| `TBL_SYNCSUBSCRIPTION` | 18063 |
| `TBL_CONTACT` | 18063 |
| `TBL_EMAIL` | 17779 |
| `TBL_ADDRESS` | 15403 |
| `CTL_SYNCROW_UPDATE` | 12462 |
| `CTL_SYNCROW_DELETE` | 12209 |
| `TBL_GROUP_CONTACT` | 9387 |
| `CTL_EVENTLOG` | 9175 |
| `TBL_COMPANY_HISTORY` | 2879 |
| `CTL_SYNCCOLUMN` | 1770 |
| `TBL_SYSCOLUMN` | 1770 |
| `TBL_SYSCOLUMN_ACL` | 1097 |
| `CTL_OLEDBFUNCTION_SYSCOLUMN` | 1065 |
| `TBL_COMPANY_ACL` | 1002 |
| `TBL_SYSTABLEKEY_SYSCOLUMN` | 771 |
| `TBL_PICKLISTITEM` | 733 |
| `CTL_LOCALSTRING` | 600 |
| `TBL_SYSTABLEKEY` | 517 |
| `TBL_PREFERENCE` | 398 |
| `TBL_COMPANY` | 334 |
| `CTL_SYNCDBMAP_SESSION` | 331 |
| `CTL_SYNCDBMAPINFO_HISTORY` | 330 |
| `TBL_SYSTABLERELATION` | 313 |
| `TBL_SYSTABLE` | 228 |
| `CTL_SYNCTABLE` | 228 |
| `TBL_CONTACT_NOTE` | 224 |
| `TBL_NOTE` | 224 |
| `TBL_ROLE_PERMISSION` | 219 |
| `CTL_SYNCROW_FILE` | 218 |
| `CTL_OLEDBFUNCTION` | 201 |
| `CTL_OLEDBVIEW_KEYINDEX_SYSCOLUMN` | 197 |
| `CTL_OLEDBVIEW_KEYINDEX` | 181 |
| `CTL_SYSTABLEORDER` | 147 |
| `TBL_COMPANY_NOTE` | 145 |
| `CTL_SYNC_DEVICETABLE` | 136 |
| `CTL_OLEDBVIEW_DERIVEDCOLUMN` | 135 |
| `TBL_ACCESSOR_PREFERENCE` | 97 |
| `TBL_PERMISSION` | 94 |
| `CTL_OLEDBVIEW_OLEDBFUNCTION` | 69 |
| `CTL_DBCONFIG` | 67 |
| `TBL_GROUP_ACL` | 66 |
| `TBL_HISTORYTYPE` | 65 |
| `TBL_PICKLIST_SYSCOLUMN` | 64 |
| `CTL_OLEDBVIEW` | 63 |
| `CTL_OLEDBVIEW_PROVIDERVIEW` | 63 |
| `CTL_PROVIDERVIEW` | 63 |
| `TBL_PHONEMASK` | 61 |
| `TBL_COUNTRY` | 59 |
| `TBL_SYSDOMAIN_SYSOPERATOR` | 55 |
| `TBL_SYSCONSTANT` | 40 |
| `TBL_USER_PERMISSION` | 40 |
| `TBL_LOGONHISTORY` | 39 |
| `TBL_EVENTLOGTYPE` | 33 |
| `TBL_PICKLIST` | 33 |
| `TBL_PERMISSION_DEPEND` | 32 |
| `TBL_SYSDATATYPE` | 31 |
| `TBL_ACCESSOR_DELEGATE` | 24 |
| `TBL_SYSLOCALCOLUMN` | 23 |
| `TBL_SYSVALUEUSAGE` | 22 |
| `TBL_GROUP` | 22 |
| `TBL_INSTALL_LOGS` | 22 |
| `TBL_SYSOPERATOR` | 21 |
| `TBL_SYSENTITYRELATION` | 20 |
| `TBL_SYSTABLEDOMAIN` | 20 |
| `TBL_FOLDER` | 19 |
| `TBL_FEATURESET` | 18 |
| `TBL_ACTIVITYSERIESITEM` | 18 |
| `TBL_SYSCALCCOLUMN` | 17 |
| `TBL_HISTORYTYPE_GROUP` | 17 |
| `TBL_VIRTUALRECORDTYPE` | 17 |
| `TBL_SYSENTITY_SYSTABLE` | 17 |
| `TBL_STAGE` | 16 |
| `TBL_USER_ACCESSOR_ENUM` | 15 |
| `TBL_SYSVALUE` | 12 |
| `TBL_SYNCSET` | 12 |
| `TBL_TEAM_USER` | 10 |
| `TBL_ACCESSOR` | 9 |
| `TBL_SYNCDBTYPE` | 9 |
| `TBL_COMPANYCONTACT_MAP` | 9 |
| `CTL_SYNCACCESSOR` | 9 |
| `TBL_SYSENTITY` | 9 |
| `TBL_SYSDOMAIN` | 9 |
| `TBL_PASSWORDHISTORY` | 8 |
| `TBL_EXTERNALMAP_SOURCE` | 8 |
| `TBL_ACCESSOR_SETTING` | 6 |
| `TBL_ROLE` | 6 |
| `TBL_ANALYTICS_VIEW_DEFINITION` | 6 |
| `TBL_HISTORYTYPE_SUPERGROUP` | 6 |
| `TBL_ACTIVITYTYPE` | 6 |
| `TBL_SYNCSETQUERY` | 6 |
| `TBL_SYNCSET_ACCESSOR` | 5 |
| `TBL_ACTIVITYPRIORITY` | 5 |
| `CTL_ABL_CONNECTORTYPE` | 5 |
| `TBL_USER` | 5 |
| `TBL_SETTING` | 4 |
| `TBL_SYSLOCALMESSAGE` | 4 |
| `CTL_SYNCSETTYPE` | 4 |
| `TBL_SYNCEXTENDEDDATA` | 4 |
| `TBL_ACTIVITYSERIES` | 3 |
| `TBL_CONTACT_ACTIVITY` | 3 |
| `TBL_PROCESS` | 3 |
| `TBL_ACCESSOR_ACTIVITY` | 3 |
| `TBL_TEAM` | 3 |
| `TBL_SOCIALMEDIA` | 3 |
| `TBL_ACTIVITY` | 3 |
| `TBL_SYNCDB` | 2 |
| `CTL_USERSESSION` | 2 |
| `TBL_NOTETYPE` | 2 |
| `CTL_SYNCDB` | 2 |
| `CTL_SYNCDBMAP` | 1 |
| `CTL_SYNCDBMAPINFO` | 1 |
| `CTL_SYNCDBMAP_ROWDATA` | 1 |
| `CTL_SYNC_INITIALIZE_ROWDATA` | 1 |
| `TBL_ANALYTICS_KPIGROUP` | 1 |
| `TBL_GROUPQUERY` | 1 |
| `TBL_WORKFLOWDEF` | 0 |
| `TBL_WORKFLOWDEF_ACL` | 0 |
| `TBL_CONTACT_SOCIALMEDIA` | 0 |
| `CTL_OLEDBVIEW_JOINDATA` | 0 |
| `TBL_GROUP_HISTORY` | 0 |
| `TBL_WORKFLOW_ARCHIVE` | 0 |
| `TBL_GROUP_NOTE` | 0 |
| `TBL_GROUP_OPPORTUNITY` | 0 |
| `TBL_WORKFLOW_SUBSCRIPTION` | 0 |
| `TBL_USER_DEFAULT_ACL` | 0 |
| `TBL_GROUP_ACTIVITY` | 0 |
| `CTL_BI_USER_DIM` | 0 |
| `CTL_BI_OPPORTUNITYSTATUS_DIM` | 0 |
| `CTL_BI_GROUP_DIM` | 0 |
| `TBL_ACCESSOR_ACTIVITY_CLEARED` | 0 |
| `CTL_BI_HISTORYTYPE_DIM` | 0 |
| `CTL_CLOUD_ALARMSNOOZE_READ` | 0 |
| `CTL_BI_OPPORTUNITY_FACT` | 0 |
| `TBL_STAGE_COLOR` | 0 |
| `CTL_BI_OPPORTUNITY_DIM` | 0 |
| `CTL_BI_INDUSTRY_DIM` | 0 |
| `TBL_EXECUTE` | 0 |
| `CTL_BI_HISTORY_FACT` | 0 |
| `CTL_BI_GEOGRAPHY_DIM` | 0 |
| `CTL_BI_COMPANY_DIM` | 0 |
| `TBL_SECONDARY` | 0 |
| `CTL_WF_INSTANCESTATE` | 0 |
| `CTL_BI_CONTACT_DIM` | 0 |
| `TBL_SERIALNUMBER` | 0 |
| `TBL_RESOURCE` | 0 |
| `CTL_USERCOLUMN_CHANGED_TRIGGER` | 0 |
| `CTL_ABL_MASTERQUEUE_PREFILTER` | 0 |
| `TBL_ANALYTICS_PIPELINE_SETTING` | 0 |
| `TBL_CONTACT_OPPORTUNITY` | 0 |
| `CTL_USERPASSWORD_RESET` | 0 |
| `TBL_CAMPAIGN_RESULTS` | 0 |
| `CTL_ABL_SCHEDULEDFOR` | 0 |
| `CTL_ABL_LINK_DEPENDENT` | 0 |
| `CTL_ABL_MASTERQUEUE_INPUT` | 0 |
| `TBL_WORKFLOW_ACTIVITY_CLEARED` | 0 |
| `TBL_PRODUCT` | 0 |
| `CTL_ABL_LINKREMAP` | 0 |
| `TBL_CONTACT_CONTACT` | 0 |
| `TBL_PRODUCTSERVICE` | 0 |
| `TBL_CONTACT_TOPLEADS_EXCLUDE` | 0 |
| `CTL_ACTIVITY_ABL_ACTIVITY` | 0 |
| `TBL_CONTACT_SOURCE` | 0 |
| `CTL_WF_COMPLETEDSCOPE` | 0 |
| `CTL_BI_CALENDARDATE_DIM` | 0 |
| `TBL_CONTACT_CAMPAIGN_RESULTS` | 0 |
| `TBL_ACCESSOR_AEMPROFILE` | 0 |
| `CTL_USER_COLUMNACCESS` | 0 |
| `CTL_ABL_MASTERQUEUE_OUTPUT` | 0 |
| `CTL_ABL_LINK` | 0 |
| `CTL_ABL_DEPENDENT` | 0 |
| `TBL_COMPANYQUERY` | 0 |
| `CTL_ABL_FIELD` | 0 |
| `CTL_SYNCROW_EXCEPTION` | 0 |
| `TBL_COMPANY_OPPORTUNITY` | 0 |
| `CTL_ABL_CONNECTOR_ENTITYSCHEMA` | 0 |
| `CTL_ABL_CONNECTOR_ENTITY` | 0 |
| `TBL_COMPANY_CONTACT` | 0 |
| `CTL_ABL_CONNECTOR_ACCESSORCONFIG` | 0 |
| `TBL_STAGE_HISTORY` | 0 |
| `TBL_IMPORT_HISTORYITEM` | 0 |
| `TBL_AL_ACTIVITY_EXTERNALID` | 0 |
| `TBL_AL_ACTIVITY` | 0 |
| `CTL_SYNC_INITIALIZE_ROWSCHEMA` | 0 |
| `TBL_ACTIVITYSERIESAPPLIED` | 0 |
| `TBL_IMPORT_HISTORY` | 0 |
| `TBL_SYNCEXTENDEDDATA_TYPE` | 0 |
| `TBL_AL_SYNCDATA` | 0 |
| `CTL_SYNCDBMAP_ROWEXCEPTION` | 0 |
| `TBL_OPPORTUNITY_NOTE` | 0 |
| `TBL_ATTACHMENT` | 0 |
| `TBL_OPPORTUNITY_PRODUCTSERVICE` | 0 |
| `CTL_ABL_ACTIVITY` | 0 |
| `TBL_COMPANY_ACTIVITY` | 0 |
| `CTL_ABL_CONNECTOR` | 0 |
| `TBL_AL_LINK` | 0 |
| `CTL_SYNCDBMAP_ROWCOMPLETED` | 0 |
| `TBL_OPPORTUNITY_ACL` | 0 |
| `TBL_AL_SCHEDULEDFOR` | 0 |
| `TBL_OPPORTUNITY` | 0 |
| `TBL_AL_DATAMAPPING` | 0 |
| `TBL_AL_DRIVERCONFIG` | 0 |
| `TBL_OPPORTUNITY_HISTORY` | 0 |
| `TBL_ALARMSNOOZE` | 0 |
| `CTL_SYNCDBMAP_ROWSCHEMA` | 0 |
| `TBL_OPPORTUNITY_ACTIVITY` | 0 |
| `TBL_AL_USERSETTING` | 0 |
| `CTL_SYNCDBMAP_ROWFILE` | 0 |

## Business/domain tables — full column detail
Every column, every business-relevant table, as restored. PK columns marked **bold**. Row count from the table above shown per table.

### `TBL_ACTIVITY`  (rows: 3)
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
| ISINVITATIONSENT | bit | 1 | no |  |
| WF_CONTEXTID | uniqueidentifier | 16 | yes |  |
| WF_INSTANCEID | uniqueidentifier | 16 | yes |  |
| DURATION | int | 4 | yes |  |
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

### `TBL_ACTIVITYSERIES`  (rows: 3)
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

### `TBL_ACTIVITYSERIESITEM`  (rows: 18)
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

### `TBL_ADDRESS`  (rows: 15403)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ADDRESSID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |
| LINE1 | nvarchar | 512 | yes |  |
| LINE2 | nvarchar | 512 | yes |  |
| LINE3 | nvarchar | 512 | yes |  |
| CITY | nvarchar | 512 | yes |  |
| STATE | nvarchar | 512 | yes |  |
| POSTALCODE | nvarchar | 512 | yes |  |
| COUNTRYNAME | nvarchar | 512 | yes |  |
| LONGITUDE | decimal | 5 | yes |  |
| LATITUDE | decimal | 5 | yes |  |
| GEOLOCATION | geography | -1 | yes |  |

### `TBL_ATTACHMENT`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **ATTACHMENTID** | uniqueidentifier | 16 | no | ✓ |
| WORKFLOWDEFID | uniqueidentifier | 16 | yes |  |
| FILENAME | nvarchar | 510 | no |  |
| DISPLAYNAME | nvarchar | 510 | no |  |
| NOTEID | uniqueidentifier | 16 | yes |  |
| ACTIVITYID | uniqueidentifier | 16 | yes |  |
| HISTORYID | uniqueidentifier | 16 | yes |  |
| MACHINENAME | nvarchar | 510 | yes |  |
| FILEPATH | nvarchar | 4096 | yes |  |

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

### `TBL_COMPANY`  (rows: 334)
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
| ISPRIVATE | bit | 1 | no |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |

### `TBL_COMPANY_ACL`  (rows: 1002)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_COMPANY_ACTIVITY`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_CONTACT`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_COMPANY_HISTORY`  (rows: 2879)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_NOTE`  (rows: 145)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COMPANYID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_COMPANY_OPPORTUNITY`  (rows: 0)
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

### `TBL_COMPANYQUERY`  (rows: 0)
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

### `TBL_CONTACT`  (rows: 18063)
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
| LASTRESULTS | nvarchar | 256 | yes |  |
| LASTEMAILDATE | datetime | 8 | yes |  |
| REFERREDBY | nvarchar | 128 | yes |  |
| SPOUSENAME | nvarchar | 128 | yes |  |
| BIRTHDATE | datetime | 8 | yes |  |
| INSTANTMSGID | nvarchar | 32 | yes |  |
| USER1 | nvarchar | 128 | yes |  |
| USER2 | nvarchar | 128 | yes |  |
| USER3 | nvarchar | 128 | yes |  |
| USER4 | nvarchar | 128 | yes |  |
| USER5 | nvarchar | 128 | yes |  |
| USER6 | nvarchar | 128 | yes |  |
| USER7 | nvarchar | 150 | yes |  |
| USER8 | nvarchar | 150 | yes |  |
| USER9 | nvarchar | 150 | yes |  |
| USER10 | nvarchar | 128 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |
| ISUSER | bit | 1 | yes |  |
| AEM_OPTOUT | bit | 1 | no |  |
| AEM_BOUNCEBACK | bit | 1 | no |  |
| ISFAVORITE | bit | 1 | no |  |
| LONGITUDE | decimal | 5 | yes |  |
| LATITUDE | decimal | 5 | yes |  |
| CUST_Source_100547384 | nvarchar | 100 | yes |  |
| CUST_SellingTravelweekly_100943228 | bit | 1 | no |  |
| CUST_VisitUSAnewsletter_101007548 | bit | 1 | no |  |
| CUST_TravelAlberta_101031804 | bit | 1 | no |  |
| CUST_SellingTravelproducts_101123643 | bit | 1 | no |  |
| CUST_SellingTravelpartners_101144541 | bit | 1 | no |  |
| CUST_ABTAorIATA_102647742 | nvarchar | 100 | yes |  |
| CUST_NewField1_104954250 | nvarchar | 100 | yes |  |
| CUST_Geographicalinterest_093649931 | nvarchar | 300 | yes |  |
| CUST_Sectorinterest_093801826 | nvarchar | 300 | yes |  |
| CUST_Copies_103521511 | nvarchar | 100 | yes |  |
| CUST_Notes_110503086 | nvarchar | 900 | yes |  |
| CUST_Areasofinterest_112720826 | nvarchar | 400 | yes |  |
| CUST_Sectorsofinterest_112834695 | nvarchar | 400 | yes |  |
| CUST_Type_113848290 | nvarchar | 100 | yes |  |
| CUST_Printsubscription_014754574 | bit | 1 | no |  |
| AMA_SCORE | int | 4 | yes |  |
| CUST_SellingCanadaNews_112843126 | bit | 1 | no |  |

### `TBL_CONTACT_ACL`  (rows: 54194)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_CONTACT_ACTIVITY`  (rows: 3)
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

### `TBL_CONTACT_HISTORY`  (rows: 96331)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |
| ISINVITED | bit | 1 | no |  |

### `TBL_CONTACT_NOTE`  (rows: 224)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |
| **NOTEID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_CONTACT_OPPORTUNITY`  (rows: 0)
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

### `TBL_COUNTRY`  (rows: 59)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **COUNTRYID** | uniqueidentifier | 16 | no | ✓ |
| NAME | nvarchar | 256 | no |  |

### `TBL_EMAIL`  (rows: 17779)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **EMAILID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |
| ADDRESS | nvarchar | 512 | yes |  |

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

### `TBL_GROUP`  (rows: 22)
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
| IMPORTDATE | datetime | 8 | yes |  |

### `TBL_GROUP_ACL`  (rows: 66)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **ACCESSORID** | uniqueidentifier | 16 | no | ✓ |
| ROWSOURCE | char | 1 | no |  |

### `TBL_GROUP_ACTIVITY`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **ACTIVITYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_CONTACT`  (rows: 9387)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **CONTACTID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_HISTORY`  (rows: 0)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **GROUPID** | uniqueidentifier | 16 | no | ✓ |
| **HISTORYID** | uniqueidentifier | 16 | no | ✓ |

### `TBL_GROUP_NOTE`  (rows: 0)
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

### `TBL_GROUPQUERY`  (rows: 1)
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

### `TBL_HISTORY`  (rows: 95341)
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

### `TBL_NOTE`  (rows: 224)
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

### `TBL_OPPORTUNITY`  (rows: 0)
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
| WEIGHTEDAMT | decimal | 9 | no |  |
| GROSSMARGINAMT | decimal | 9 | yes |  |
| USER1 | nvarchar | 128 | yes |  |
| USER2 | nvarchar | 128 | yes |  |
| USER3 | nvarchar | 128 | yes |  |
| USER4 | nvarchar | 128 | yes |  |
| USER5 | nvarchar | 128 | yes |  |
| USER6 | nvarchar | 128 | yes |  |
| USER7 | nvarchar | 128 | yes |  |
| USER8 | nvarchar | 128 | yes |  |
| MANAGEUSERID | uniqueidentifier | 16 | no |  |
| CREATEUSERID | uniqueidentifier | 16 | no |  |
| CREATEDATE | datetime | 8 | no |  |
| EDITUSERID | uniqueidentifier | 16 | yes |  |
| EDITDATE | datetime | 8 | yes |  |
| IMPORTDATE | datetime | 8 | yes |  |
| DAYSOPEN | int | 4 | yes |  |
| STAGESTARTDATE | datetime | 8 | yes |  |
| DAYSINSTAGE | int | 4 | yes |  |
| SOURCEID | uniqueidentifier | 16 | yes |  |
| STATUS | nvarchar | 26 | yes |  |

### `TBL_OPPORTUNITY_ACL`  (rows: 0)
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

### `TBL_OPPORTUNITY_HISTORY`  (rows: 0)
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

### `TBL_PHONE`  (rows: 29232)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PHONEID** | uniqueidentifier | 16 | no | ✓ |
| TYPEID | uniqueidentifier | 16 | no |  |
| CONTACTID | uniqueidentifier | 16 | yes |  |
| COMPANYID | uniqueidentifier | 16 | yes |  |
| GROUPID | uniqueidentifier | 16 | yes |  |
| OPPORTUNITYID | uniqueidentifier | 16 | yes |  |
| NUMBERVALUE | nvarchar | 64 | yes |  |
| NUMBERDISPLAY | nvarchar | 64 | yes |  |
| SUFFIX | nvarchar | 512 | yes |  |
| COUNTRYCODE | smallint | 2 | no |  |
| PHONEMASKID | uniqueidentifier | 16 | yes |  |

### `TBL_PHONEMASK`  (rows: 61)
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

### `TBL_PICKLIST`  (rows: 33)
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

### `TBL_PICKLIST_SYSCOLUMN`  (rows: 64)
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

### `TBL_PICKLISTITEM`  (rows: 733)
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

### `TBL_PREFERENCE`  (rows: 398)
| Column | Type | Max len | Nullable | PK |
|---|---|---|---|---|
| **PREFERENCEID** | uniqueidentifier | 16 | no | ✓ |
| NAME | varchar | 256 | no |  |
| ISSERIALIZED | bit | 1 | no |  |
| OBJECTBINARYVALUE | varbinary | -1 | yes |  |
| OBJECTSTRINGVALUE | nvarchar | -1 | no |  |

### `TBL_PROCESS`  (rows: 3)
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

### `TBL_PRODUCT`  (rows: 0)
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

### `TBL_SECONDARY`  (rows: 0)
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

### `TBL_STAGE`  (rows: 16)
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

### `TBL_STAGE_HISTORY`  (rows: 0)
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
| `TBL_OPPORTUNITY`.STAGEID | → | `TBL_STAGE`.STAGEID |
| `TBL_OPPORTUNITY`.MANAGEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY`.EDITUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY`.CREATEUSERID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY_ACL`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_ACL`.ACCESSORID | → | `TBL_ACCESSOR`.ACCESSORID |
| `TBL_OPPORTUNITY_ACTIVITY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_ACTIVITY`.ACTIVITYID | → | `TBL_ACTIVITY`.ACTIVITYID |
| `TBL_OPPORTUNITY_HISTORY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_HISTORY`.HISTORYID | → | `TBL_HISTORY`.HISTORYID |
| `TBL_OPPORTUNITY_NOTE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_OPPORTUNITY_NOTE`.NOTEID | → | `TBL_NOTE`.NOTEID |
| `TBL_OPPORTUNITY_PRODUCTSERVICE`.PRODUCTSERVICEID | → | `TBL_PRODUCTSERVICE`.PRODUCTSERVICEID |
| `TBL_OPPORTUNITY_PRODUCTSERVICE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_PHONE`.CONTACTID | → | `TBL_CONTACT`.CONTACTID |
| `TBL_PHONE`.COMPANYID | → | `TBL_COMPANY`.COMPANYID |
| `TBL_PHONE`.TYPEID | → | `TBL_PICKLISTITEM`.PICKLISTITEMID |
| `TBL_PHONE`.PHONEMASKID | → | `TBL_PHONEMASK`.PHONEMASKID |
| `TBL_PHONE`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |
| `TBL_PHONE`.GROUPID | → | `TBL_GROUP`.GROUPID |
| `TBL_PHONEMASK`.COUNTRYID | → | `TBL_COUNTRY`.COUNTRYID |
| `TBL_PICKLIST`.DATATYPEID | → | `TBL_SYSDATATYPE`.DATATYPEID |
| `TBL_PICKLIST_SYSCOLUMN`.PICKLISTID | → | `TBL_PICKLIST`.PICKLISTID |
| `TBL_PICKLIST_SYSCOLUMN`.COLUMNID | → | `TBL_SYSCOLUMN`.COLUMNID |
| `TBL_PICKLISTITEM`.PICKLISTID | → | `TBL_PICKLIST`.PICKLISTID |
| `TBL_PRODUCTSERVICE`.PRODUCTID | → | `TBL_PRODUCT`.PRODUCTID |
| `TBL_STAGE`.PROCESSID | → | `TBL_PROCESS`.PROCESSID |
| `TBL_STAGE_COLOR`.USERID | → | `TBL_USER`.USERID |
| `TBL_STAGE_COLOR`.STAGEID | → | `TBL_STAGE`.STAGEID |
| `TBL_STAGE_HISTORY`.STAGETOID | → | `TBL_STAGE`.STAGEID |
| `TBL_STAGE_HISTORY`.STAGEFROMID | → | `TBL_STAGE`.STAGEID |
| `TBL_STAGE_HISTORY`.OPPORTUNITYID | → | `TBL_OPPORTUNITY`.OPPORTUNITYID |

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
| Call Regarding | Check In |
| Call Regarding | Cold Call |
| Call Regarding | Confirm Appointment |
| Call Regarding | Confirm Shipment |
| Call Regarding | Discuss Legal Points |
| Call Regarding | Follow-up |
| Call Regarding | Get the order |
| Call Regarding | Give Quote |
| Call Regarding | Initial Communication |
| Call Regarding | Needs Assessment |
| Call Regarding | Request Updated Catalog |
| Call Regarding | Request Updated Prices |
| Call Regarding | Returning Call |
| Call Regarding | Schedule a Meeting |
| Call Regarding | Schedule Presentation |
| Call Regarding | Thank You |
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
| Contact ID/Status | Business Associate |
| Contact ID/Status | Cold Lead |
| Contact ID/Status | Competitor |
| Contact ID/Status | Consultant |
| Contact ID/Status | Contractor |
| Contact ID/Status | Co-Worker |
| Contact ID/Status | Customer |
| Contact ID/Status | Decision Maker |
| Contact ID/Status | Distributor |
| Contact ID/Status | Employee |
| Contact ID/Status | Family |
| Contact ID/Status | Friend |
| Contact ID/Status | Gate Keeper |
| Contact ID/Status | Hot Lead |
| Contact ID/Status | Influencer |
| Contact ID/Status | Investor |
| Contact ID/Status | Key Customer |
| Contact ID/Status | Lead |
| Contact ID/Status | Manufacturer |
| Contact ID/Status | Personal |
| Contact ID/Status | Prospect |
| Contact ID/Status | Qualified Lead |
| Contact ID/Status | Reseller |
| Contact ID/Status | Resource |
| Contact ID/Status | Retailer |
| Contact ID/Status | Shareholder |
| Contact ID/Status | Supplier |
| Contact ID/Status | Vendor |
| Contact ID/Status | Warm Lead |
| Contact ID/Status | Wholesaler |
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
| Departments | Administration |
| Departments | Corporate |
| Departments | Customer Service |
| Departments | Engineering |
| Departments | Facilities |
| Departments | Finance/Accounting |
| Departments | Human Resources |
| Departments | Information Technology |
| Departments | Legal |
| Departments | Manufacturing |
| Departments | Marketing |
| Departments | Production |
| Departments | Public Relations |
| Departments | Purchasing |
| Departments | Sales |
| Departments | Security |
| Departments | Service |
| Departments | Shipping |
| Departments | Technical Support |
| EMail Types | Business |
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
| Meeting Regarding | Ask for the Order |
| Meeting Regarding | Breakfast Meeting |
| Meeting Regarding | Cold Call |
| Meeting Regarding | Contract Negotiations |
| Meeting Regarding | Demonstration |
| Meeting Regarding | Dinner Meeting |
| Meeting Regarding | First Meeting |
| Meeting Regarding | Follow-up on Delivery |
| Meeting Regarding | Follow-up on Presentation |
| Meeting Regarding | Introduction |
| Meeting Regarding | Lunch Meeting |
| Meeting Regarding | Presentation |
| Meeting Regarding | Sales Call |
| Meeting Regarding | Show New Products |
| Meeting Regarding | Staff Meeting |
| Meeting Regarding | Trade Show |
| Meeting Regarding | Vacation |
| Opportunity Close Reasons | Budget |
| Opportunity Close Reasons | Competition |
| Opportunity Close Reasons | Features |
| Opportunity Close Reasons | Pricing |
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
| Product Unit of Issue | Box/Carton |
| Product Unit of Issue | Each |
| Referred By | Advertisement |
| Referred By | Affiliate/Partner |
| Referred By | Article |
| Referred By | Associate |
| Referred By | Called In |
| Referred By | Customer Referral |
| Referred By | Direct Mail |
| Referred By | E-mail Campaign |
| Referred By | Event/Seminar |
| Referred By | Friend |
| Referred By | Other |
| Referred By | Phone Book |
| Referred By | Search Engine |
| Referred By | Trade Show |
| Referred By | Website |
| Referred By | Word of Mouth |
| Region | Channel Isles |
| Region | East Anglia |
| Region | East Midlands |
| Region | London |
| Region | London |
| Region | Midlands |
| Region | North West |
| Region | Northern |
| Region | Northern Ireland |
| Region | Scotland |
| Region | Scotland |
| Region | South East |
| Region | South West |
| Region | Wales |
| Region | Wales |
| Region | Yorkshire |
| Surname Suffixes | C.F.P. |
| Surname Suffixes | C.L.U. |
| Surname Suffixes | C.P.A. |
| Surname Suffixes | CFP |
| Surname Suffixes | CLU |
| Surname Suffixes | CPA |
| Surname Suffixes | D.D.S. |
| Surname Suffixes | DDS |
| Surname Suffixes | Esq |
| Surname Suffixes | Esq. |
| Surname Suffixes | I |
| Surname Suffixes | II |
| Surname Suffixes | III |
| Surname Suffixes | IV |
| Surname Suffixes | J.D. |
| Surname Suffixes | JD |
| Surname Suffixes | Jr |
| Surname Suffixes | Jr. |
| Surname Suffixes | M.B.A. |
| Surname Suffixes | M.D. |
| Surname Suffixes | MBA |
| Surname Suffixes | MD |
| Surname Suffixes | Ph.D. |
| Surname Suffixes | PhD |
| Surname Suffixes | Sr |
| Surname Suffixes | Sr. |
| Surname Suffixes | V |
| Territory | East |
| Territory | Mid West |
| Territory | North |
| Territory | North East |
| Territory | North West |
| Territory | South |
| Territory | South East |
| Territory | South West |
| Territory | West |
| To-do Regarding | Assemble Catalogs |
| To-do Regarding | Check Delivery Status |
| To-do Regarding | Follow-up |
| To-do Regarding | Get the order |
| To-do Regarding | Make Travel Arrangements |
| To-do Regarding | Send a Letter |
| To-do Regarding | Send Contract |
| To-do Regarding | Send Email |
| To-do Regarding | Send FAX |
| To-do Regarding | Send Follow-up Letter |
| To-do Regarding | Send Invoice |
| To-do Regarding | Send Literature |
| To-do Regarding | Send Proposal |
| To-do Regarding | Send Quote |
| To-do Regarding | Send Reminder |
| Type | Call Centre |
| Type | Cruising |
| Type | Homeworker |
| Type | Independent Travel Agent |
| Type | Miniple |
| Type | Multiple |
| Type | Other |
| Type | Tour Operator |
| Type | Unsubscribed |
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
Changed database context to 'SellingTravel'.
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
Changed database context to 'SellingTravel'.
NOTETYPEID|NAME
----------|----
103|AI Summary
100|Note

(2 rows affected)
```

## Custom field decode
`TBL_SYSCOLUMN` is Act!'s field catalogue — every column on every entity, including custom ones, with `ISCUSTOM`, `DISPLAYNAME` (the human label shown in the Act! UI) vs `COLUMNNAME` (the physical column, which is what SQL sees). Pull `TBL_SYSCOLUMN` during ETL and join on `COLUMNNAME` to get the true field label rather than guessing from the suffix.

**This database looks least alike the other two.** `TBL_CONTACT` has 27 custom/user fields, but with almost no overlap against OnBoard/Prospects — no `bmi_notes`, no `VATRegNo`, no `TickerSymbol`, no `zipcode`, no `SL_*` Sage fields at all:

| Physical column | Real meaning |
|---|---|
| `USER1`–`USER10` | Generic legacy fields — same caution as the other two databases |
| `CUST_SellingTravelweekly_100943228`, `CUST_SellingTravelproducts_101123643`, `CUST_SellingTravelpartners_101144541`, `CUST_SellingCanadaNews_112843126` (all `bit`) | Newsletter/mailing-list subscription flags for this title and a related "Selling Canada" product |
| `CUST_VisitUSAnewsletter_101007548`, `CUST_TravelAlberta_101031804` (both `bit`) | More newsletter flags — matches the `Visit USA Online 2026.xls` file already seen in your Drive folder; confirms this database backs multiple travel-trade titles/products, not just "Selling Travel" alone |
| `CUST_ABTAorIATA_102647742` | Travel-trade accreditation number (ABTA/IATA membership) — travel-agency-specific, no equivalent on the other two DBs |
| `CUST_Geographicalinterest_093649931`, `CUST_Sectorinterest_093801826`, `CUST_Areasofinterest_112720826`, `CUST_Sectorsofinterest_112834695` | Four separate but similarly-named "interest" free-text fields — likely redundant/overlapping, worth asking BMI which are actually current vs superseded by another |
| `CUST_Copies_103521511` | Likely print-copy quantity, relevant to circulation like OnBoard's print-subscription flag |
| `CUST_Notes_110503086` | A second, distinct free-text notes field alongside the standard `TBL_NOTE` mechanism — confirm with BMI whether this is actively used or legacy |
| `CUST_Type_113848290` | Not a raw text field — resolves through the `Type` picklist (see below), travel-agency segment |
| `CUST_Printsubscription_014754574` | Same concept as OnBoard's field, **different suffix ID again** — reconfirms custom fields must be matched by decoded label, not raw column name, across all three databases |
| `CUST_Source_100547384` | Free-text lead/contact source, same concept as Prospects' `CUST_Source`, different ID |
| `CUST_NewField1_104954250` | Literally named "NewField1" — almost certainly an ad-hoc/never-properly-named field; flag for BMI, do not assume meaning |

**`TBL_COMPANY` and `TBL_GROUP` have zero custom fields here** — a real structural difference from the other two databases (which both had `CUST_SL_*`/none on Company, and a rich custom set on Group). Company/Group classification in this database relies entirely on picklists.

New picklist not seen on the other two: **`Opportunity Close Reasons`** (Budget / Competition / Features / Pricing) — present despite this database having zero live Opportunities, so it's configured-but-unused. Also new: a generic **`Type`** picklist with travel-agency segments (Call Centre, Cruising, Homeworker, Independent Travel Agent, Miniple, Multiple, Tour Operator, Unsubscribed, Other) — this is real, useful domain classification for a travel-trade contact list.
## Observations & migration notes — SellingTravel-specific
- **By far the smallest and cleanest of the three databases**: 18,063 Contacts, 334 Companies, 22 Groups, 224 Notes, 95,341 History rows — roughly a quarter of OnBoard's size and a tenth of Prospects'.
- **History is almost entirely noise here — worse than the other two, proportionally**: of 95,341 rows, only 4 history types appear at all, and `Contact Deleted` alone is 79,185 rows (**83%**). Genuine `E-mail Sent` is 10,571 (11%); `Contact Linked`/`Unlinked` account for the rest. There is effectively **no** Call/Meeting/Letter history in this database at all — either this title's sales activity was never logged in Act!, or it happened through a different channel entirely. Worth asking BMI directly rather than assuming.
- **Opportunities: 0 here.** Combined across all three databases: OnBoard 1 + Prospects 6 + SellingTravel 0 = **7 total** — this exactly matches `CONTEXT.md`'s "~7 Opportunities" figure, so that part of the original assumption holds up precisely.
- **Activities: only 3 here**, but combined with OnBoard's 57 and Prospects' 2,071, the three-database total is **2,131** — this still meaningfully contradicts `CONTEXT.md`'s "0 Activities" assumption, and the contradiction is now confirmed to come entirely from the Prospects database (2,071 of 2,131). Worth specifically asking BMI what's actually in Prospects' Activities before deciding to discard that data — it may be real scheduled/completed task history worth preserving rather than designing Activities fresh from nothing.
- **No accounting-system integration fields here** (no `CUST_SL_*` Sage fields, unlike Prospects) — if Sage was in use, it wasn't synced against this database, or this title isn't invoiced through the same system.
- **Custom fields confirm the pattern established across all three DBs**: conceptually identical fields (`Printsubscription`, `Source`) exist under different `CUST_*_<digits>` suffixes per database, while a handful (`bmi_notes` between OnBoard/Prospects only) coincidentally share suffixes. **The ETL must always resolve custom fields via `TBL_SYSCOLUMN.DISPLAYNAME`, never via raw column name matching across databases.**
- Structural shape (tables, FK pattern, junction tables for Notes/History/Address/Phone/Email, GUID PKs, 217 tables/137 views — near-identical counts to OnBoard's 218/137) is **consistent across all three databases**, confirming the ETL script can be one parameterized script keyed on `source_db`, differing only in what data it finds and how it maps custom fields — not in the SQL Server schema navigation logic itself.

## Act! internal/engine tables — reference list only
These 148 tables are Act!'s own application internals — sync engine (`CTL_SYNC*`, `TBL_SYNC*`), system metadata/UI definitions (`TBL_SYS*`), access control (`TBL_ACCESSOR*`, ACL tables), workflow/analytics engine, licensing, login history. None of this carries BMI business data or is a migration target — listed here only so the schema documentation is genuinely complete. Row counts are in the table above.

`CTL_ABL_ACTIVITY`, `CTL_ABL_CONNECTOR`, `CTL_ABL_CONNECTOR_ACCESSORCONFIG`, `CTL_ABL_CONNECTOR_ENTITY`, `CTL_ABL_CONNECTOR_ENTITYSCHEMA`, `CTL_ABL_CONNECTORTYPE`, `CTL_ABL_DEPENDENT`, `CTL_ABL_FIELD`, `CTL_ABL_LINK`, `CTL_ABL_LINK_DEPENDENT`, `CTL_ABL_LINKREMAP`, `CTL_ABL_MASTERQUEUE_INPUT`, `CTL_ABL_MASTERQUEUE_OUTPUT`, `CTL_ABL_MASTERQUEUE_PREFILTER`, `CTL_ABL_SCHEDULEDFOR`, `CTL_ACTIVITY_ABL_ACTIVITY`, `CTL_BI_CALENDARDATE_DIM`, `CTL_BI_COMPANY_DIM`, `CTL_BI_CONTACT_DIM`, `CTL_BI_GEOGRAPHY_DIM`, `CTL_BI_GROUP_DIM`, `CTL_BI_HISTORY_FACT`, `CTL_BI_HISTORYTYPE_DIM`, `CTL_BI_INDUSTRY_DIM`, `CTL_BI_OPPORTUNITY_DIM`, `CTL_BI_OPPORTUNITY_FACT`, `CTL_BI_OPPORTUNITYSTATUS_DIM`, `CTL_BI_USER_DIM`, `CTL_CLOUD_ALARMSNOOZE_READ`, `CTL_DBCONFIG`, `CTL_EVENTLOG`, `CTL_EVENTLOGDETAIL`, `CTL_LOCALSTRING`, `CTL_OLEDBFUNCTION`, `CTL_OLEDBFUNCTION_SYSCOLUMN`, `CTL_OLEDBVIEW`, `CTL_OLEDBVIEW_DERIVEDCOLUMN`, `CTL_OLEDBVIEW_JOINDATA`, `CTL_OLEDBVIEW_KEYINDEX`, `CTL_OLEDBVIEW_KEYINDEX_SYSCOLUMN`, `CTL_OLEDBVIEW_OLEDBFUNCTION`, `CTL_OLEDBVIEW_PROVIDERVIEW`, `CTL_PROVIDERVIEW`, `CTL_SYNC_DEVICETABLE`, `CTL_SYNC_INITIALIZE_ROWDATA`, `CTL_SYNC_INITIALIZE_ROWSCHEMA`, `CTL_SYNCACCESSOR`, `CTL_SYNCCOLUMN`, `CTL_SYNCDB`, `CTL_SYNCDBMAP`, `CTL_SYNCDBMAP_ROWCOMPLETED`, `CTL_SYNCDBMAP_ROWDATA`, `CTL_SYNCDBMAP_ROWEXCEPTION`, `CTL_SYNCDBMAP_ROWFILE`, `CTL_SYNCDBMAP_ROWSCHEMA`, `CTL_SYNCDBMAP_SESSION`, `CTL_SYNCDBMAP_SESSIONROW`, `CTL_SYNCDBMAPINFO`, `CTL_SYNCDBMAPINFO_HISTORY`, `CTL_SYNCROW_ADD`, `CTL_SYNCROW_DELETE`, `CTL_SYNCROW_EXCEPTION`, `CTL_SYNCROW_FILE`, `CTL_SYNCROW_UPDATE`, `CTL_SYNCROW_UPDATECOLUMN`, `CTL_SYNCSETTYPE`, `CTL_SYNCTABLE`, `CTL_SYSTABLEORDER`, `CTL_USER_COLUMNACCESS`, `CTL_USERCOLUMN_CHANGED_TRIGGER`, `CTL_USERPASSWORD_RESET`, `CTL_USERSESSION`, `CTL_WF_COMPLETEDSCOPE`, `CTL_WF_INSTANCESTATE`, `TBL_ACCESSOR`, `TBL_ACCESSOR_ACTIVITY`, `TBL_ACCESSOR_ACTIVITY_CLEARED`, `TBL_ACCESSOR_AEMPROFILE`, `TBL_ACCESSOR_DELEGATE`, `TBL_ACCESSOR_PREFERENCE`, `TBL_ACCESSOR_SETTING`, `TBL_AL_ACTIVITY`, `TBL_AL_ACTIVITY_EXTERNALID`, `TBL_AL_DATAMAPPING`, `TBL_AL_DRIVERCONFIG`, `TBL_AL_LINK`, `TBL_AL_SCHEDULEDFOR`, `TBL_AL_SYNCDATA`, `TBL_AL_USERSETTING`, `TBL_ALARMSNOOZE`, `TBL_ANALYTICS_KPIGROUP`, `TBL_ANALYTICS_PIPELINE_SETTING`, `TBL_ANALYTICS_VIEW_DEFINITION`, `TBL_EXTERNALMAP_SOURCE`, `TBL_FEATURESET`, `TBL_FOLDER`, `TBL_IMPORT_HISTORY`, `TBL_IMPORT_HISTORYITEM`, `TBL_INSTALL_LOGS`, `TBL_LOGONHISTORY`, `TBL_PASSWORDHISTORY`, `TBL_PERMISSION`, `TBL_PERMISSION_DEPEND`, `TBL_RESOURCE`, `TBL_ROLE`, `TBL_ROLE_PERMISSION`, `TBL_SYNCCONTACT`, `TBL_SYNCCONTACT_ACL`, `TBL_SYNCDB`, `TBL_SYNCDBTYPE`, `TBL_SYNCEXTENDEDDATA`, `TBL_SYNCEXTENDEDDATA_TYPE`, `TBL_SYNCSET`, `TBL_SYNCSET_ACCESSOR`, `TBL_SYNCSETQUERY`, `TBL_SYNCSUBSCRIPTION`, `TBL_SYSCALCCOLUMN`, `TBL_SYSCOLUMN`, `TBL_SYSCOLUMN_ACL`, `TBL_SYSCONSTANT`, `TBL_SYSDATATYPE`, `TBL_SYSDOMAIN`, `TBL_SYSDOMAIN_SYSOPERATOR`, `TBL_SYSENTITY`, `TBL_SYSENTITY_SYSTABLE`, `TBL_SYSENTITYRELATION`, `TBL_SYSLOCALCOLUMN`, `TBL_SYSLOCALMESSAGE`, `TBL_SYSOPERATOR`, `TBL_SYSTABLE`, `TBL_SYSTABLEDOMAIN`, `TBL_SYSTABLEKEY`, `TBL_SYSTABLEKEY_SYSCOLUMN`, `TBL_SYSTABLERELATION`, `TBL_SYSVALUE`, `TBL_SYSVALUEUSAGE`, `TBL_TEAM`, `TBL_TEAM_USER`, `TBL_USER`, `TBL_USER_ACCESSOR_ENUM`, `TBL_USER_DEFAULT_ACL`, `TBL_USER_PERMISSION`, `TBL_VIRTUALRECORDTYPE`, `TBL_WORKFLOW_ACTIVITY_CLEARED`, `TBL_WORKFLOW_ARCHIVE`, `TBL_WORKFLOW_SUBSCRIPTION`, `TBL_WORKFLOWDEF`, `TBL_WORKFLOWDEF_ACL`
