import type {
  CompanyDetail,
  CompanyListItem,
  ContactDetail,
  ContactListItem,
  DashboardStats,
  GroupListItem,
  Page,
  Publication,
} from "@/lib/types";

export function getDevFallback<T>(path: string): T | null {
  // Publications
  if (path.startsWith("/api/publications")) {
    return [
      {
        id: "pub_1",
        name: "Onboard Hospitality",
        slug: "onboard",
        description: "Inflight catering & onboard services",
        color: "blue",
        icon: "plane",
        contact_count: 42150,
        company_count: 5310,
      },
      {
        id: "pub_2",
        name: "Selling Travel",
        slug: "sellingtravel",
        description: "Travel trade & agent distribution",
        color: "emerald",
        icon: "compass",
        contact_count: 51200,
        company_count: 6420,
      },
      {
        id: "pub_3",
        name: "Prospects",
        slug: "prospects",
        description: "Global leads & brand directory",
        color: "amber",
        icon: "globe",
        contact_count: 25070,
        company_count: 2500,
      },
    ] as unknown as T;
  }

  // Dashboard Stats
  if (path.startsWith("/api/dashboard/stats")) {
    return {
      total_contacts: 118420,
      total_companies: 14230,
      total_groups: 34,
      contacts_by_source: [
        { source_db: "onboard", count: 42150 },
        { source_db: "sellingtravel", count: 51200 },
        { source_db: "prospects", count: 25070 },
      ],
      companies_by_source: [
        { source_db: "onboard", count: 5310 },
        { source_db: "sellingtravel", count: 6420 },
        { source_db: "prospects", count: 2500 },
      ],
      recent_contacts: [
        {
          id: "cnt_01h8x1",
          full_name: "Eleanor Vance",
          first_name: "Eleanor",
          last_name: "Vance",
          job_title: "Head of Inflight Catering & Procurement",
          company_id: "cmp_01h8x1",
          company_name: "British Airways",
          source_db: "onboard",
          last_activity_date: new Date().toISOString(),
          last_activity_type: "call",
          last_activity_summary: "Confirmed WTCE 2026 meeting for Onboard issue feature",
        },
        {
          id: "cnt_02h8x2",
          full_name: "Marcus Thorne",
          first_name: "Marcus",
          last_name: "Thorne",
          job_title: "Senior VP Global Supply Chain",
          company_id: "cmp_02h8x2",
          company_name: "Gate Gourmet Europe",
          source_db: "onboard",
          last_activity_date: new Date(Date.now() - 86400000).toISOString(),
          last_activity_type: "meeting",
          last_activity_summary: "Discussed double-page spread ad rates for Q3",
        },
        {
          id: "cnt_03h8x3",
          full_name: "Clara Higgins",
          first_name: "Clara",
          last_name: "Higgins",
          job_title: "Marketing Director",
          company_id: "cmp_03h8x3",
          company_name: "Visit California UK",
          source_db: "sellingtravel",
          last_activity_date: new Date(Date.now() - 172800000).toISOString(),
          last_activity_type: "email",
          last_activity_summary: "Requested Selling Travel 2026 media pack",
        },
      ],
      recent_companies: [
        {
          id: "cmp_01h8x1",
          name: "British Airways",
          industry: "Aviation & Inflight Retail",
          source_db: "onboard",
          last_activity_date: new Date().toISOString(),
          last_activity_type: "call",
          last_activity_summary: "Called Eleanor Vance regarding WTCE 2026",
        },
      ],
      top_companies: [
        {
          id: "cmp_01h8x1",
          name: "British Airways",
          industry: "Aviation & Inflight Retail",
          contact_count: 8,
        },
        {
          id: "cmp_02h8x2",
          name: "Gate Gourmet Europe",
          industry: "Airline Catering & Logistics",
          contact_count: 14,
        },
        {
          id: "cmp_03h8x3",
          name: "Visit California UK",
          industry: "Destination Marketing",
          contact_count: 5,
        },
      ],
    } as unknown as T;
  }

  // Single Contact Detail
  if (path.startsWith("/api/contacts/")) {
    const id = path.replace("/api/contacts/", "").split("?")[0];
    return {
      id: id || "cnt_01h8x1",
      source_db: "onboard",
      source_act_id: "ACT-ONB-4921",
      first_name: "Eleanor",
      last_name: "Vance",
      full_name: "Eleanor Vance",
      job_title: "Head of Inflight Catering & Procurement",
      department: "Catering Operations & Inflight Services",
      category: "VIP / Decision Maker",
      referred_by: "Clare - Publisher Lead",
      birthdate: "1982-04-15",
      created_at: "2021-03-10T10:00:00Z",
      last_meet_date: "2026-08-22T14:30:00Z",
      last_reach_date: "2026-09-02T11:15:00Z",
      last_attempt_date: "2026-09-10T09:45:00Z",
      last_letter_date: "2026-07-14T00:00:00Z",
      company: {
        id: "cmp_01h8x1",
        name: "British Airways",
        industry: "Aviation & Inflight Retail",
      },
      addresses: [
        {
          id: "addr_1",
          type_label: "Headquarters",
          line1: "Waterside, Speedbird Way",
          line2: "Harmondsworth",
          city: "West Drayton",
          state: "Middlesex",
          postal_code: "UB7 0GA",
          country: "United Kingdom",
        },
      ],
      phones: [
        { id: "ph_1", type_label: "Direct", number: "+44 (0)20 8738 5100" },
        { id: "ph_2", type_label: "Mobile", number: "+44 (0)7700 900842" },
      ],
      emails: [
        { id: "em_1", type_label: "Business", address: "eleanor.vance@ba.com" },
        { id: "em_2", type_label: "Alternate", address: "e.vance.procure@gmail.com" },
      ],
      groups: [
        { id: "grp_1", name: "WTCE 2026 Buyers" },
        { id: "grp_2", name: "Onboard Hospitality Awards Panel" },
        { id: "grp_3", name: "Aviation Catering VIPs" },
      ],
      notes: [
        {
          id: "note_1",
          note_type: "Call",
          body: "Called Eleanor regarding WTCE Hamburg stand location. She confirmed BA will have 4 buyers attending. Wants to review preliminary page proofs for the April issue.",
          act_created_at: "2026-09-02T11:15:00Z",
        },
        {
          id: "note_2",
          note_type: "Note",
          body: "Met at World Travel Catering Expo. Discussed sustainably packaged culinary offerings for long-haul Club World. High interest in the Onboard Taste of Travel theater.",
          act_created_at: "2026-08-22T14:30:00Z",
        },
        {
          id: "note_3",
          note_type: "Email",
          body: "Sent updated 2026 media kit with advertising specs and print deadlines. Follow up in 10 days regarding inside front cover booking.",
          act_created_at: "2026-07-28T16:00:00Z",
        },
      ],
      history: [
        {
          id: "hist_1",
          history_type: "Call Completed",
          subject: "Editorial Q&A on BA plant-based menu rollout",
          occurred_at: "2026-09-02T11:15:00Z",
        },
        {
          id: "hist_2",
          history_type: "Meeting Held",
          subject: "WTCE 2026 Pre-planning Strategy Session",
          occurred_at: "2026-08-22T14:30:00Z",
        },
        {
          id: "hist_3",
          history_type: "Letter Sent",
          subject: "Onboard Hospitality Autumn 2026 Complimentary Issue with Certificate",
          occurred_at: "2026-07-14T09:00:00Z",
        },
      ],
      custom_fields: {
        "user1_circulation_copies": "15 Print Copies",
        "user2_wtce_booth": "Hall A1 / Stand 142",
        "user3_preferred_issue": "March/April Pre-Expo",
        "user4_account_director": "Clare",
        "user5_rate_bracket": "Tier 1 Enterprise VIP",
        "user6_catering_tier": "Long-Haul Premium",
        "user7_contract_renewal": "November 2026",
      },
    } as unknown as T;
  }

  // Single Company Detail
  if (path.startsWith("/api/companies/")) {
    const id = path.replace("/api/companies/", "").split("?")[0];
    return {
      id: id || "cmp_01h8x1",
      source_db: "onboard",
      source_act_id: "ACT-COMP-1082",
      name: "British Airways",
      industry: "Aviation & Inflight Retail",
      category: "Key Global Account",
      territory: "UK & Global Routes",
      region: "Western Europe",
      website: "www.britishairways.com",
      description: "Flag carrier airline of the United Kingdom, operating global passenger and cargo services with extensive premium inflight catering partnerships.",
      num_employees: 38000,
      addresses: [
        {
          id: "caddr_1",
          type_label: "Global HQ",
          line1: "Waterside, Speedbird Way",
          line2: "Harmondsworth",
          city: "West Drayton",
          state: "Middlesex",
          postal_code: "UB7 0GA",
          country: "United Kingdom",
        },
      ],
      phones: [
        { id: "cph_1", type_label: "Switchboard", number: "+44 (0)20 8738 5000" },
      ],
      emails: [
        { id: "cem_1", type_label: "Press / Media", address: "media.relations@ba.com" },
      ],
      contacts: [
        {
          id: "cnt_01h8x1",
          source_db: "onboard",
          full_name: "Eleanor Vance",
          first_name: "Eleanor",
          last_name: "Vance",
          job_title: "Head of Inflight Catering & Procurement",
          company_id: "cmp_01h8x1",
          company_name: "British Airways",
          primary_email: "eleanor.vance@ba.com",
          primary_phone: "+44 (0)20 8738 5100",
        },
        {
          id: "cnt_04h8x4",
          source_db: "onboard",
          full_name: "James Sterling",
          first_name: "James",
          last_name: "Sterling",
          job_title: "Director of Inflight Product Experience",
          company_id: "cmp_01h8x1",
          company_name: "British Airways",
          primary_email: "james.sterling@ba.com",
          primary_phone: "+44 (0)20 8738 5220",
        },
      ],
      notes: [
        {
          id: "cnote_1",
          note_type: "Meeting",
          body: "Annual media partnership review with BA inflight product team. Discussed sponsorship of Onboard Hospitality Awards Category 4.",
          act_created_at: "2026-08-15T15:00:00Z",
        },
      ],
      custom_fields: {
        "user1_fleet_size": "280 Aircraft",
        "user2_annual_ad_spend": "£45,000",
        "user3_priority": "Tier 1 Platinum",
      },
    } as unknown as T;
  }

  // Contacts List
  if (path.startsWith("/api/contacts")) {
    return {
      items: [
        {
          id: "cnt_01h8x1",
          source_db: "onboard",
          full_name: "Eleanor Vance",
          first_name: "Eleanor",
          last_name: "Vance",
          job_title: "Head of Inflight Catering & Procurement",
          company_id: "cmp_01h8x1",
          company_name: "British Airways",
          primary_email: "eleanor.vance@ba.com",
          primary_phone: "+44 (0)20 8738 5100",
        },
        {
          id: "cnt_02h8x2",
          source_db: "onboard",
          full_name: "Marcus Thorne",
          first_name: "Marcus",
          last_name: "Thorne",
          job_title: "Senior VP Global Supply Chain",
          company_id: "cmp_02h8x2",
          company_name: "Gate Gourmet Europe",
          primary_email: "m.thorne@gategourmet.com",
          primary_phone: "+41 44 532 1000",
        },
        {
          id: "cnt_03h8x3",
          source_db: "sellingtravel",
          full_name: "Clara Higgins",
          first_name: "Clara",
          last_name: "Higgins",
          job_title: "Marketing Director",
          company_id: "cmp_03h8x3",
          company_name: "Visit California UK",
          primary_email: "clara.h@visitcalifornia.co.uk",
          primary_phone: "+44 (0)20 7420 1800",
        },
      ],
      total: 118420,
      page: 1,
      page_size: 50,
      pages: 2368,
    } as unknown as T;
  }

  // Companies List
  if (path.startsWith("/api/companies")) {
    return {
      items: [
        {
          id: "cmp_01h8x1",
          source_db: "onboard",
          name: "British Airways",
          industry: "Aviation & Inflight Retail",
          category: "Key Global Account",
          contact_count: 8,
        },
        {
          id: "cmp_02h8x2",
          source_db: "onboard",
          name: "Gate Gourmet Europe",
          industry: "Airline Catering & Logistics",
          category: "Global Supplier",
          contact_count: 14,
        },
        {
          id: "cmp_03h8x3",
          source_db: "sellingtravel",
          name: "Visit California UK",
          industry: "Destination Marketing",
          category: "Tourism Board",
          contact_count: 5,
        },
      ],
      total: 14230,
      page: 1,
      page_size: 50,
      pages: 285,
    } as unknown as T;
  }

  // Groups List
  if (path.startsWith("/api/groups")) {
    return {
      items: [
        {
          id: "grp_1",
          name: "WTCE 2026 Buyers",
          description: "Key decision makers attending World Travel Catering Expo",
          member_count: 342,
          hier_level: 0,
          parent_group_id: null,
        },
        {
          id: "grp_2",
          name: "Onboard Hospitality Awards Panel",
          description: "Official judging committee and nominees",
          member_count: 88,
          hier_level: 0,
          parent_group_id: null,
        },
        {
          id: "grp_3",
          name: "Aviation Catering VIPs",
          description: "Top 100 airline catering executives",
          member_count: 120,
          hier_level: 0,
          parent_group_id: null,
        },
      ],
      total: 3,
      page: 1,
      page_size: 50,
      pages: 1,
    } as unknown as T;
  }

  return null;
}
