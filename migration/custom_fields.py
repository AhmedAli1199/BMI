"""Custom-field decode maps, one per (source_db, act_table).

Hand-verified against the actual restored databases and written up in
docs/act-schema/{onboard,prospects,sellingtravel}-schema.md - see each
doc's "Custom field decode" section for the reasoning behind each label.

These are hardcoded (not looked up from Act!'s own TBL_SYSCOLUMN at ETL
time) on purpose: it's the same information, but hardcoding it here means
the mapping is reviewable in a PR diff and doesn't depend on trusting
Act!'s own DISPLAYNAME text verbatim as a Postgres jsonb key. Raw
`CUST_*_<digits>` / `USERn` column names are NEVER used as keys directly -
see docs/act-schema/prospects-schema.md's finding that the same field can
carry a different suffix ID per database, and the reverse (different
fields coincidentally sharing an ID) - matching must go through this map.

Any custom column NOT listed here for its (source_db, table) is still
captured, under its raw column name prefixed `unmapped_` - so nothing is
silently dropped, but anything new shows up clearly as needing a decision
rather than blending in as if reviewed.
"""

# --- OnBoard --------------------------------------------------------------

ONBOARD_CONTACT = {
    "USER1": "user1", "USER2": "user2", "USER3": "user3", "USER4": "user4",
    "USER5": "user5", "USER6": "user6", "USER7": "user7", "USER8": "user8",
    "USER9": "user9", "USER10": "user10",
    "CUST_User11_020248031": "user11", "CUST_User12_020250421": "user12",
    "CUST_User13_020252750": "user13", "CUST_User14_020253703": "user14",
    "CUST_User15_020256046": "user15",
    "CUST_2ndLastReach_020257000": "second_last_reach_date",
    "CUST_3rdLastReach_020259406": "third_last_reach_date",
    "CUST_TickerSymbol_020300375": "ticker_symbol",
    "CUST_zipcode_020302765": "zipcode",
    "CUST_BMINotes_093741681": "bmi_notes",
    "CUST_VATRegNo_104355159": "vat_reg_no",
    "CUST_Printsubscription_014611185": "print_subscription",
}

ONBOARD_COMPANY: dict[str, str] = {}

ONBOARD_GROUP = {
    "CUST_Division_020311187": "division", "CUST_Priority_020314218": "priority",
    "CUST_User1_020315390": "user1", "CUST_User2_020317562": "user2",
    "CUST_User3_020318218": "user3", "CUST_User4_020320390": "user4",
    "CUST_User5_020321078": "user5", "CUST_User6_020323312": "user6",
    "CUST_Region_020324000": "region", "CUST_Industry_020326218": "industry",
    "CUST_SICCode_020326921": "sic_code",
    "CUST_NumberofEmployees_020329187": "number_of_employees",
    "CUST_Revenue_020329921": "revenue", "CUST_TickerSymbol_020332171": "ticker_symbol",
    "CUST_ReferredBy_020333234": "referred_by", "CUST_WebSite_020335687": "website",
}

# --- Prospects --------------------------------------------------------------

PROSPECTS_CONTACT = {
    "USER1": "user1", "USER2": "user2", "USER3": "user3", "USER4": "user4",
    "USER5": "user5", "USER6": "user6", "USER7": "user7", "USER8": "user8",
    "USER9": "user9", "USER10": "user10",
    "CUST_User11_020248031": "user11", "CUST_User12_020250421": "user12",
    "CUST_User13_020252750": "user13", "CUST_User14_020253703": "user14",
    "CUST_User15_020256046": "user15",
    "CUST_2ndLastReach_020257000": "second_last_reach_date",
    "CUST_3rdLastReach_020259406": "third_last_reach_date",
    "CUST_TickerSymbol_020300375": "ticker_symbol",
    "CUST_zipcode_020302765": "zipcode",
    "CUST_BMINotes_093741681": "bmi_notes",
    "CUST_VATRegNo_104355159": "vat_reg_no",
    # Sage Line 50 accounting-system mirror - see prospects-schema.md.
    "CUST_SL_ACCOUNT_REF_100819508": "sage_account_ref",
    "CUST_SL_NAME_100823161": "sage_name",
    "CUST_SL_CONTACT_NAME_100826277": "sage_contact_name",
    "CUST_SL_ADDRESS_1_100829462": "sage_address_1",
    "CUST_SL_ADDRESS_2_100832373": "sage_address_2",
    "CUST_SL_ADDRESS_3_100835651": "sage_address_3",
    "CUST_SL_ADDRESS_4_100838637": "sage_address_4",
    "CUST_SL_ADDRESS_5_100842087": "sage_address_5",
    "CUST_SL_TELEPHONE_100849250": "sage_telephone",
    "CUST_SL_TELEPHONE_2_100852578": "sage_telephone_2",
    "CUST_SL_FAX_100855667": "sage_fax",
    "CUST_SL_E_MAIL_100859600": "sage_email",
    "CUST_SL_VAT_REG_NUMBER_100902813": "sage_vat_reg_number",
    "CUST_Spend_041525705": "spend",
    "CUST_TBTMweekly_041623361": "tbtm_weekly_subscriber",
    "CUST_TBTMProducts_041643596": "tbtm_products_subscriber",
    "CUST_TBTMpartners_045338908": "tbtm_partners_subscriber",
    "CUST_Check_125538556": "check_field",
    "CUST_PrintSubscription_015023575": "print_subscription",
    "CUST_Source_015043607": "source",
    "CUST_Areaofresponsibility_015140123": "area_of_responsibility",
    "CUST_Travelregions_015309983": "travel_regions",
}

PROSPECTS_COMPANY = {
    "CUST_SL_ACCOUNT_REF_093337006": "sage_account_ref",
    "CUST_SL_NAME_093348011": "sage_name",
    "CUST_SL_CONTACT_NAME_093349661": "sage_contact_name",
    "CUST_SL_ADDRESS_1_093352783": "sage_address_1",
    "CUST_SL_ADDRESS_2_093354266": "sage_address_2",
    "CUST_SL_ADDRESS_3_093357642": "sage_address_3",
    "CUST_SL_ADDRESS_4_093359615": "sage_address_4",
    "CUST_SL_ADDRESS_5_093402626": "sage_address_5",
    "CUST_SL_TELEPHONE_093404556": "sage_telephone",
    "CUST_SL_TELEPHONE_2_093408472": "sage_telephone_2",
    "CUST_SL_FAX_093410678": "sage_fax",
    "CUST_SL_E_MAIL_093413537": "sage_email",
    "CUST_SL_VAT_REG_NUMBER_093415579": "sage_vat_reg_number",
}

PROSPECTS_GROUP = ONBOARD_GROUP  # identical layout, confirmed in prospects-schema.md

# --- SellingTravel --------------------------------------------------------------

SELLINGTRAVEL_CONTACT = {
    "USER1": "user1", "USER2": "user2", "USER3": "user3", "USER4": "user4",
    "USER5": "user5", "USER6": "user6", "USER7": "user7", "USER8": "user8",
    "USER9": "user9", "USER10": "user10",
    "CUST_Source_100547384": "source",
    "CUST_SellingTravelweekly_100943228": "selling_travel_weekly_subscriber",
    "CUST_VisitUSAnewsletter_101007548": "visit_usa_newsletter_subscriber",
    "CUST_TravelAlberta_101031804": "travel_alberta_subscriber",
    "CUST_SellingTravelproducts_101123643": "selling_travel_products_subscriber",
    "CUST_SellingTravelpartners_101144541": "selling_travel_partners_subscriber",
    "CUST_ABTAorIATA_102647742": "abta_or_iata",
    "CUST_NewField1_104954250": "new_field_1_unconfirmed",
    "CUST_Geographicalinterest_093649931": "geographical_interest",
    "CUST_Sectorinterest_093801826": "sector_interest",
    "CUST_Copies_103521511": "copies",
    "CUST_Notes_110503086": "notes",
    "CUST_Areasofinterest_112720826": "areas_of_interest",
    "CUST_Sectorsofinterest_112834695": "sectors_of_interest",
    "CUST_Type_113848290": "type",
    "CUST_Printsubscription_014754574": "print_subscription",
    "CUST_SellingCanadaNews_112843126": "selling_canada_news_subscriber",
}

SELLINGTRAVEL_COMPANY: dict[str, str] = {}
SELLINGTRAVEL_GROUP: dict[str, str] = {}


CUSTOM_FIELD_MAPS = {
    "onboard": {"contact": ONBOARD_CONTACT, "company": ONBOARD_COMPANY, "group": ONBOARD_GROUP},
    "prospects": {"contact": PROSPECTS_CONTACT, "company": PROSPECTS_COMPANY, "group": PROSPECTS_GROUP},
    "sellingtravel": {
        "contact": SELLINGTRAVEL_CONTACT,
        "company": SELLINGTRAVEL_COMPANY,
        "group": SELLINGTRAVEL_GROUP,
    },
}


def decode_custom_fields(row: dict, field_map: dict[str, str]) -> dict:
    """row: a dict of raw SQL column -> value, for the CUST_*/USERn columns
    only. Returns the jsonb-ready dict, keyed by clean label. Anything not
    in field_map is kept under an `unmapped_` key rather than dropped.
    """
    out = {}
    for col, value in row.items():
        if value is None:
            continue
        label = field_map.get(col)
        if label is None:
            label = f"unmapped_{col}"
        out[label] = value
    return out
