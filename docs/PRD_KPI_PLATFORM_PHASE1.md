# 📋 Product Requirements Document (PRD)
## KPI Platform - Phase 1 Implementation

**Version:** 1.0  
**Date:** January 17, 2026  
**Status:** Approved for Implementation  
**Owner:** Engineering Team

---

## 🎯 EXECUTIVE SUMMARY

Transform the Sales Intelligence Platform into a comprehensive KPI Management Platform by adding:
- Team management and hierarchy
- Portfolio management for Product Directors
- Initiative/campaign tracking
- Enhanced activity linkage to portfolios and goals

**Timeline:** 8 weeks  
**Sprints:** 4 (2 weeks each)  
**Resources Required:** 1 full-stack developer

---

## 👥 USER PERSONAS

### Persona 1: Product Director (Primary)
**Name:** Sarah Chen  
**Role:** Product Director - Application Security  
**Goals:**
- Manage Application Security portfolio
- Plan and track quarterly initiatives
- Assign goals to account managers
- Monitor team performance and KPIs

**Pain Points:**
- No centralized portfolio view
- Can't track initiatives systematically
- Manual goal assignment and tracking
- No visibility into team activity completion

**Success Metrics:**
- Can create and manage 3+ portfolios
- Can launch 5+ initiatives per quarter
- Can assign goals to 10+ team members
- Can view team performance dashboard

---

### Persona 2: CEO (Secondary)
**Name:** Michael Thompson  
**Role:** Chief Executive Officer  
**Goals:**
- Monitor strategic account penetration
- Track company-wide KPI performance
- Identify bottlenecks and overdue activities
- Make data-driven strategic decisions

**Pain Points:**
- No strategic overview dashboard
- Can't see cross-portfolio performance
- Manual tracking of strategic goals
- No team accountability metrics

**Success Metrics:**
- Single dashboard for all strategic KPIs
- Real-time team performance visibility
- Account penetration metrics
- Activity completion tracking

---

### Persona 3: Sales Manager (Tertiary)
**Name:** David Rodriguez  
**Role:** Sales Manager  
**Goals:**
- Track team quota attainment
- Monitor activity completion
- Align activities to portfolio goals
- Track invoice collection KPIs

**Pain Points:**
- Activities not linked to strategic initiatives
- No portfolio context for sales activities
- Manual KPI tracking
- Difficulty correlating activities to outcomes

**Success Metrics:**
- Team activities linked to initiatives
- Clear visibility of portfolio targets
- Automated activity-to-KPI mapping
- Real-time team performance

---

## 🎯 USER STORIES

### Sprint 1: Team Management

**US-1.1: Create Team**
```
As a CEO
I want to create teams (CEO, Product, Sales)
So that I can organize users into strategic groups

Acceptance Criteria:
- Can create team with name and type
- Can select team owner/leader
- Can add team description
- Team appears in team list
- Owner receives notification (optional)

API: POST /api/teams
{
  "name": "Application Security Team",
  "type": "product",
  "owner_id": "sarah_uuid",
  "description": "AppSec portfolio team"
}
```

**US-1.2: Manage Team Members**
```
As a Team Owner
I want to add/remove team members
So that I can manage my team composition

Acceptance Criteria:
- Can add multiple users to team
- Can remove team members
- Members see team in their profile
- Can view team member list
- Access control: only owner can modify

API: POST /api/teams/{team_id}/members
{
  "user_ids": ["user1", "user2", "user3"]
}
```

**US-1.3: View Teams**
```
As a User
I want to see all teams I'm part of
So that I know my organizational context

Acceptance Criteria:
- Dashboard shows my teams
- Can view team details
- Can see team members
- Can see team owner
- Can filter by team type

API: GET /api/teams?member_id=current_user
```

---

### Sprint 2: Portfolio Management

**US-2.1: Create Portfolio**
```
As a Product Director
I want to create a portfolio for my product line
So that I can organize initiatives and track performance

Acceptance Criteria:
- Can create portfolio with name
- Can assign to team
- Can define product lines
- Can set strategic priority
- Portfolio appears in portfolio list

API: POST /api/portfolios
{
  "name": "Application Security",
  "team_id": "team_uuid",
  "product_lines": ["Penetration Testing", "Code Review", "SAST"],
  "strategic_priority": "high"
}
```

**US-2.2: View Portfolio Dashboard**
```
As a Product Director
I want to see my portfolio performance dashboard
So that I can monitor initiative progress and KPIs

Acceptance Criteria:
- Shows all initiatives in portfolio
- Shows active vs planned initiatives
- Shows linked KPIs with values
- Shows team activity completion rate
- Shows opportunity pipeline by product line

API: GET /api/portfolios/{id}/dashboard
Response:
{
  "portfolio": {...},
  "initiatives": [{...}],
  "kpis": [{name, current, target, status}],
  "metrics": {
    "active_initiatives": 3,
    "total_activities": 50,
    "completion_rate": 78.5,
    "pipeline_value": 500000
  }
}
```

**US-2.3: Portfolio Metrics**
```
As a CEO
I want to see all portfolios and their performance
So that I can compare portfolio effectiveness

Acceptance Criteria:
- Grid/list view of all portfolios
- Shows owner, team, priority
- Shows key metrics (initiatives, pipeline, KPIs)
- Can sort by performance
- Can filter by priority/team

API: GET /api/portfolios?include_metrics=true
```

---

### Sprint 3: Initiative Management

**US-3.1: Create Initiative**
```
As a Product Director
I want to create a quarterly initiative
So that I can plan and execute campaigns

Acceptance Criteria:
- Can create initiative with name and dates
- Can link to portfolio
- Can define activity template (demos, calls, etc.)
- Can set status (planning/active/completed)
- Can assign goals

API: POST /api/initiatives
{
  "name": "Q2 2026 Demo Campaign",
  "portfolio_id": "appsec_uuid",
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "activity_template": {
    "demos": 20,
    "outreach_calls": 50,
    "proposals": 10
  },
  "status": "planning"
}
```

**US-3.2: Track Initiative Progress**
```
As a Product Director
I want to see initiative progress
So that I can ensure we're on track

Acceptance Criteria:
- Shows activity completion vs template
- Shows linked goals and their progress
- Shows linked KPIs and their values
- Timeline view of milestones
- Can mark initiative as completed

API: GET /api/initiatives/{id}/progress
Response:
{
  "initiative": {...},
  "activity_progress": {
    "demos": {"completed": 12, "target": 20, "percentage": 60},
    "calls": {"completed": 35, "target": 50, "percentage": 70}
  },
  "goals": [{name, progress, status}],
  "kpis": [{name, current, target}]
}
```

**US-3.3: Link Activities to Initiative**
```
As a Sales Rep
I want to log an activity and link it to an initiative
So that my work contributes to initiative goals

Acceptance Criteria:
- Activity creation shows initiative selector
- Can filter initiatives by portfolio
- Activity counts toward initiative progress
- Activity appears in initiative activity list

API: POST /api/activities
{
  "title": "Demo for TechCorp",
  "initiative_id": "q2_campaign_uuid",
  "opportunity_id": "opp_uuid"
}
```

---

### Sprint 4: Enhanced Activity Linkage

**US-4.1: Multi-Dimensional Activity Links**
```
As a User
I want to link an activity to multiple entities
So that it contributes to multiple goals/KPIs

Acceptance Criteria:
- Can link activity to: opportunity, portfolio, initiative, goal
- Activity creation form shows all link options
- Linked entities appear in activity detail
- Activity counts toward all linked KPIs

API: POST /api/activities
{
  "title": "Strategic demo with ACME Corp",
  "opportunity_id": "opp_uuid",
  "portfolio_id": "appsec_uuid",
  "initiative_id": "q2_campaign_uuid",
  "goal_ids": ["goal1_uuid", "goal2_uuid"]
}
```

**US-4.2: Activity Outcome Tracking**
```
As a Sales Rep
I want to record activity outcomes
So that success rates can be tracked

Acceptance Criteria:
- Can mark activity as completed
- Can record outcome (success/failure)
- Can add outcome notes
- Can record next steps
- Outcome affects KPI calculations

API: PATCH /api/activities/{id}/complete
{
  "outcome": {
    "success": true,
    "notes": "Client very interested, moving to proposal",
    "next_steps": "Send pricing proposal by Friday"
  }
}
```

---

## 🎨 UI/UX SPECIFICATIONS

### Teams Page (New)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Teams                                        [+ New Team]│
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │ 👥 CEO Team      │  │ 🎯 Product Team  │            │
│  │ Owner: Michael   │  │ Owner: Sarah     │            │
│  │ 3 members        │  │ 12 members       │            │
│  │ 5 portfolios     │  │ 3 portfolios     │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐                                   │
│  │ 💼 Sales Team    │                                   │
│  │ Owner: David     │                                   │
│  │ 8 members        │                                   │
│  │ 0 portfolios     │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- TeamCard: Shows team summary
- TeamDetailModal: Member list, add/remove
- NewTeamModal: Create team form

---

### Portfolios Page (New)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Portfolios                                [+ New Portfolio]│
├─────────────────────────────────────────────────────────┤
│ [All Teams ▼] [Priority: All ▼] [Search...]            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────┐               │
│  │ 🔐 Application Security              │               │
│  │ Owner: Sarah Chen | Product Team     │               │
│  │ Priority: HIGH                       │               │
│  ├──────────────────────────────────────┤               │
│  │ Initiatives: 3 active | 2 completed │               │
│  │ Pipeline: $2.5M | Win Rate: 65%    │               │
│  │ KPIs: 5 (3 on track, 2 at risk)    │               │
│  │                                      │               │
│  │ [View Dashboard →]                  │               │
│  └──────────────────────────────────────┘               │
│                                                          │
│  ┌──────────────────────────────────────┐               │
│  │ 🌐 Network Security                  │               │
│  │ Owner: John Smith | Product Team     │               │
│  │ Priority: MEDIUM                     │               │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- PortfolioCard: Summary metrics
- PortfolioDashboard: Detailed view with initiatives, KPIs
- NewPortfolioModal: Creation form

---

### Initiatives Page (New)

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Initiatives                            [+ New Initiative]│
├─────────────────────────────────────────────────────────┤
│ [Planning] [Active] [Completed] [All Portfolios ▼]     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  📋 PLANNING (2)                                        │
│  ┌──────────────────────────────────────┐               │
│  │ Q2 2026 Demo Campaign                │               │
│  │ Portfolio: Application Security      │               │
│  │ Timeline: Apr 1 - Jun 30, 2026      │               │
│  ├──────────────────────────────────────┤               │
│  │ Activity Plan:                       │               │
│  │   Demos: 0/20 (0%)                  │               │
│  │   Calls: 0/50 (0%)                  │               │
│  │   Proposals: 0/10 (0%)              │               │
│  ├──────────────────────────────────────┤               │
│  │ Goals: 2 assigned                    │               │
│  │ KPIs: 3 linked                       │               │
│  │ [View Details →]                     │               │
│  └──────────────────────────────────────┘               │
│                                                          │
│  🚀 ACTIVE (3)                                          │
│  ┌──────────────────────────────────────┐               │
│  │ Account Penetration - EMEA           │               │
│  │ Portfolio: Network Security          │               │
│  │ Progress: 67% complete               │               │
│  │ [Progress bar........................]│               │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

**Components:**
- InitiativeKanban: Status-based columns
- InitiativeCard: Progress indicators
- InitiativeDetailPanel: Full view with activity list
- NewInitiativeModal: Creation wizard

---

## 🔧 TECHNICAL SPECIFICATIONS

### Sprint 1: Team Management

#### Database Schema

**Collection:** `teams`
```javascript
{
  "_id": ObjectId("..."),
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Application Security Team",
  "type": "product",  // product | sales | strategic | ops
  "owner_id": "user_uuid",
  "description": "Team managing AppSec portfolio",
  "member_ids": ["user1_uuid", "user2_uuid", "user3_uuid"],
  "parent_team_id": null,  // For team hierarchy
  "metadata": {
    "portfolios_count": 3,
    "initiatives_count": 5
  },
  "created_at": ISODate("2026-01-17T..."),
  "updated_at": ISODate("2026-01-17T..."),
  "is_active": true
}

// Indexes
db.teams.createIndex({ "owner_id": 1 })
db.teams.createIndex({ "type": 1 })
db.teams.createIndex({ "member_ids": 1 })
```

**Collection:** `team_members` (Junction Table)
```javascript
{
  "_id": ObjectId("..."),
  "id": "uuid",
  "team_id": "team_uuid",
  "user_id": "user_uuid",
  "role": "member" | "owner" | "admin",
  "joined_at": ISODate("..."),
  "is_active": true
}

// Indexes
db.team_members.createIndex({ "team_id": 1, "user_id": 1 }, { unique: true })
db.team_members.createIndex({ "user_id": 1 })
```

---

#### API Endpoints

**POST /api/teams**
```python
# Create a new team
Request:
{
  "name": "Application Security Team",
  "type": "product",
  "owner_id": "sarah_uuid",
  "description": "Team managing AppSec portfolio",
  "initial_members": ["user1", "user2"]
}

Response:
{
  "id": "team_uuid",
  "name": "Application Security Team",
  "owner_id": "sarah_uuid",
  "member_count": 2,
  "created_at": "2026-01-17T..."
}

Validation:
- name: required, max 100 chars
- type: must be in enum [product, sales, strategic, ops]
- owner_id: must exist in users collection
- initial_members: must exist in users collection
```

**GET /api/teams**
```python
# List all teams (with optional filters)
Query Params:
  ?type=product
  ?owner_id=user_uuid
  ?member_id=user_uuid

Response:
{
  "teams": [
    {
      "id": "team_uuid",
      "name": "Application Security Team",
      "type": "product",
      "owner": {
        "id": "user_uuid",
        "name": "Sarah Chen",
        "email": "sarah@company.com"
      },
      "member_count": 12,
      "portfolios_count": 3,
      "created_at": "..."
    }
  ],
  "count": 1
}
```

**GET /api/teams/{team_id}**
```python
# Get team details with members
Response:
{
  "id": "team_uuid",
  "name": "Application Security Team",
  "type": "product",
  "owner": {...},
  "description": "...",
  "members": [
    {
      "user_id": "uuid",
      "name": "John Doe",
      "email": "john@company.com",
      "role": "member",
      "joined_at": "..."
    }
  ],
  "portfolios": [{...}],
  "created_at": "..."
}
```

**POST /api/teams/{team_id}/members**
```python
# Add members to team
Request:
{
  "user_ids": ["user1_uuid", "user2_uuid"],
  "role": "member"  // optional, default: member
}

Response:
{
  "added": 2,
  "team_id": "team_uuid",
  "new_member_count": 14
}

Validation:
- user_ids: must exist, max 50 per request
- role: must be in [member, admin]
- Only team owner or admin can add members
```

**DELETE /api/teams/{team_id}/members/{user_id}**
```python
# Remove member from team
Response:
{
  "removed": true,
  "remaining_members": 13
}

Validation:
- Cannot remove team owner
- Only owner or admin can remove members
```

---

### Sprint 2: Portfolio Management

#### Database Schema

**Collection:** `portfolios`
```javascript
{
  "_id": ObjectId("..."),
  "id": "uuid",
  "name": "Application Security",
  "team_id": "team_uuid",
  "owner_id": "sarah_uuid",
  "product_lines": ["Penetration Testing", "Code Review", "SAST", "DAST"],
  "strategic_priority": "high",  // high | medium | low
  "fiscal_year": "FY2026",
  "description": "Enterprise application security solutions",
  "metadata": {
    "active_initiatives": 3,
    "total_initiatives": 8,
    "total_activities": 150,
    "pipeline_value": 2500000.0,
    "active_opportunities": 12
  },
  "created_at": ISODate("..."),
  "updated_at": ISODate("..."),
  "is_active": true
}

// Indexes
db.portfolios.createIndex({ "owner_id": 1 })
db.portfolios.createIndex({ "team_id": 1 })
db.portfolios.createIndex({ "strategic_priority": 1 })
```

---

#### API Endpoints

**POST /api/portfolios**
```python
Request:
{
  "name": "Application Security",
  "team_id": "team_uuid",
  "product_lines": ["Penetration Testing", "Code Review"],
  "strategic_priority": "high",
  "description": "Enterprise AppSec solutions"
}

Response:
{
  "id": "portfolio_uuid",
  "name": "Application Security",
  "team_id": "team_uuid",
  "owner_id": "current_user_id",
  "created_at": "..."
}

Validation:
- name: required, max 100 chars, unique per team
- team_id: must exist
- product_lines: array, max 10 items
- Only team members can create portfolios for that team
```

**GET /api/portfolios**
```python
Query Params:
  ?team_id=uuid
  ?owner_id=uuid
  ?priority=high
  ?include_metrics=true

Response:
{
  "portfolios": [{
    "id": "uuid",
    "name": "Application Security",
    "team": {...},
    "owner": {...},
    "priority": "high",
    "metrics": {  // if include_metrics=true
      "active_initiatives": 3,
      "pipeline_value": 2500000,
      "win_rate": 65.5,
      "kpi_health": "green"
    }
  }],
  "count": 1
}
```

**GET /api/portfolios/{id}/dashboard**
```python
# Complete portfolio dashboard
Response:
{
  "portfolio": {...},
  "initiatives": [
    {
      "id": "uuid",
      "name": "Q2 Demo Campaign",
      "status": "active",
      "progress": 67.5,
      "start_date": "2026-04-01",
      "end_date": "2026-06-30"
    }
  ],
  "kpis": [
    {
      "id": "uuid",
      "name": "Demo Conversion Rate",
      "current_value": 68.5,
      "target_value": 75.0,
      "status": "at_risk",
      "trend": "down"
    }
  ],
  "metrics": {
    "total_pipeline": 2500000,
    "active_opportunities": 12,
    "won_value_ytd": 1200000,
    "activity_completion_rate": 78.5,
    "team_size": 12
  },
  "recent_activities": [...],  // Last 10
  "top_opportunities": [...]   // Top 5 by value
}
```

---

### Sprint 3: Initiative Management

#### Database Schema

**Collection:** `initiatives`
```javascript
{
  "_id": ObjectId("..."),
  "id": "uuid",
  "name": "Q2 2026 Demo Campaign",
  "portfolio_id": "portfolio_uuid",
  "owner_id": "sarah_uuid",
  "type": "campaign",  // campaign | program | project
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "status": "active",  // planning | active | completed | paused | cancelled
  
  "activity_template": {
    "demos": { "target": 20, "completed": 12 },
    "outreach_calls": { "target": 50, "completed": 35 },
    "proposals": { "target": 10, "completed": 5 }
  },
  
  "goals": ["goal1_uuid", "goal2_uuid"],
  "kpis": ["kpi1_uuid", "kpi2_uuid"],
  
  "milestones": [
    {
      "name": "Campaign Launch",
      "date": "2026-04-15",
      "completed": true
    },
    {
      "name": "Mid-quarter Review",
      "date": "2026-05-15",
      "completed": false
    }
  ],
  
  "metadata": {
    "total_activities": 47,
    "opportunities_created": 8,
    "pipeline_generated": 500000
  },
  
  "created_at": ISODate("..."),
  "updated_at": ISODate("..."),
  "is_active": true
}

// Indexes
db.initiatives.createIndex({ "portfolio_id": 1 })
db.initiatives.createIndex({ "owner_id": 1 })
db.initiatives.createIndex({ "status": 1 })
db.initiatives.createIndex({ "start_date": 1, "end_date": 1 })
```

---

#### API Endpoints

**POST /api/initiatives**
```python
Request:
{
  "name": "Q2 2026 Demo Campaign",
  "portfolio_id": "portfolio_uuid",
  "type": "campaign",
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "activity_template": {
    "demos": 20,
    "outreach_calls": 50,
    "proposals": 10
  },
  "milestones": [
    {"name": "Launch", "date": "2026-04-15"},
    {"name": "Mid-review", "date": "2026-05-15"}
  ]
}

Response:
{
  "id": "initiative_uuid",
  "name": "Q2 2026 Demo Campaign",
  "status": "planning",
  "created_at": "..."
}

Validation:
- name: required, max 200 chars
- portfolio_id: must exist
- start_date < end_date
- Only portfolio owner or team members can create
```

**GET /api/initiatives/{id}/progress**
```python
Response:
{
  "initiative": {...},
  "progress": {
    "overall": 67.5,  // Percentage
    "activity_completion": {
      "demos": {
        "completed": 12,
        "target": 20,
        "percentage": 60.0
      },
      "outreach_calls": {
        "completed": 35,
        "target": 50,
        "percentage": 70.0
      },
      "proposals": {
        "completed": 5,
        "target": 10,
        "percentage": 50.0
      }
    },
    "milestones": {
      "completed": 1,
      "total": 2,
      "next_due": "2026-05-15"
    }
  },
  "goals": [
    {
      "id": "uuid",
      "name": "15 qualified opportunities",
      "progress": 53.3,  // 8/15
      "status": "on_track"
    }
  ],
  "kpis": [...],
  "recent_activities": [...]
}
```

---

### Sprint 4: Enhanced Activity Linkage

#### Database Migration

**Update activities collection:**
```python
# Add new fields
{
  # Existing fields...
  "title": "Demo for TechCorp",
  "opportunity_id": "uuid",
  
  # NEW FIELDS
  "portfolio_id": "uuid",
  "initiative_id": "uuid",
  "goal_ids": ["goal1_uuid", "goal2_uuid"],
  "kpi_ids": ["kpi1_uuid"],
  
  "outcome": {
    "recorded": true,
    "success": true,
    "notes": "Client interested in premium package",
    "next_steps": "Send proposal by Friday",
    "recorded_at": ISODate("..."),
    "recorded_by": "user_uuid"
  }
}
```

---

#### API Endpoints

**POST /api/activities (Enhanced)**
```python
Request:
{
  "title": "Strategic demo with ACME Corp",
  "activity_type": "demo",
  "opportunity_id": "opp_uuid",
  
  // NEW: Multi-dimensional linkage
  "portfolio_id": "appsec_uuid",
  "initiative_id": "q2_campaign_uuid",
  "goal_ids": ["goal1_uuid", "goal2_uuid"],
  
  "assigned_to": "user_uuid",
  "due_date": "2026-01-25"
}

Response:
{
  "id": "activity_uuid",
  "title": "Strategic demo with ACME Corp",
  "linked_entities": {
    "opportunity": "opp_uuid",
    "portfolio": "appsec_uuid",
    "initiative": "q2_campaign_uuid",
    "goals": 2
  },
  "created_at": "..."
}
```

**PATCH /api/activities/{id}/complete**
```python
Request:
{
  "outcome": {
    "success": true,
    "notes": "Very positive response, moving to proposal stage",
    "next_steps": "Send pricing proposal by Friday"
  }
}

Response:
{
  "activity_id": "uuid",
  "completed_at": "...",
  "outcome": {...},
  
  // Auto-updated entities
  "updated_initiative_progress": 68.5,
  "updated_goal_progress": [
    {"goal_id": "uuid", "new_progress": 85.0}
  ]
}

Side Effects:
- Initiative activity count incremented
- Goals progress auto-calculated
- KPIs referencing this activity recomputed
```

---

## 🎨 UI COMPONENT SPECIFICATIONS

### TeamCard Component
```javascript
// frontend/src/components/TeamCard.js
<div className="card p-6 hover:shadow-lg">
  <div className="flex items-center gap-3 mb-4">
    <div className="w-12 h-12 bg-indigo-100 rounded-lg">
      <Users className="w-6 h-6 text-indigo-600" />
    </div>
    <div>
      <h3 className="font-bold text-slate-900">{team.name}</h3>
      <p className="text-sm text-slate-500">{team.type}</p>
    </div>
  </div>
  
  <div className="space-y-2 text-sm">
    <div className="flex justify-between">
      <span className="text-slate-600">Owner:</span>
      <span className="font-medium">{team.owner.name}</span>
    </div>
    <div className="flex justify-between">
      <span className="text-slate-600">Members:</span>
      <span className="font-medium">{team.member_count}</span>
    </div>
    <div className="flex justify-between">
      <span className="text-slate-600">Portfolios:</span>
      <span className="font-medium">{team.portfolios_count}</span>
    </div>
  </div>
  
  <Button className="w-full mt-4" onClick={onViewDetails}>
    View Team
  </Button>
</div>
```

---

### PortfolioCard Component
```javascript
// frontend/src/components/PortfolioCard.js
<div className="card p-6 border-l-4 border-indigo-500">
  <div className="flex items-start justify-between mb-4">
    <div>
      <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-bold rounded">
        {portfolio.strategic_priority.toUpperCase()}
      </span>
      <h3 className="text-xl font-bold text-slate-900 mt-2">
        {portfolio.name}
      </h3>
      <p className="text-sm text-slate-600">
        {portfolio.owner.name} | {portfolio.team.name}
      </p>
    </div>
  </div>
  
  <div className="grid grid-cols-2 gap-4 mb-4">
    <div className="bg-blue-50 p-3 rounded">
      <p className="text-xs text-blue-600">Initiatives</p>
      <p className="text-2xl font-bold text-blue-900">
        {portfolio.metrics.active_initiatives}
      </p>
    </div>
    <div className="bg-emerald-50 p-3 rounded">
      <p className="text-xs text-emerald-600">Pipeline</p>
      <p className="text-2xl font-bold text-emerald-900">
        ${(portfolio.metrics.pipeline_value / 1000000).toFixed(1)}M
      </p>
    </div>
  </div>
  
  <div className="flex items-center justify-between text-sm">
    <span className="text-slate-600">
      KPIs: {portfolio.kpis_on_track}/{portfolio.total_kpis}
    </span>
    <Button size="sm" onClick={onViewDashboard}>
      Dashboard →
    </Button>
  </div>
</div>
```

---

## 🧪 TESTING REQUIREMENTS

### Unit Tests

**Backend:**
```python
# tests/test_teams.py
def test_create_team():
    # Given: Valid team data
    # When: POST /api/teams
    # Then: Team created, members added, owner assigned

def test_add_team_member():
    # Given: Existing team
    # When: POST /teams/{id}/members
    # Then: Member added, user.team_ids updated

def test_team_access_control():
    # Given: Non-owner user
    # When: POST /teams/{id}/members
    # Then: 403 Forbidden
```

**Frontend:**
```javascript
// tests/Teams.test.js
test('renders team list', () => {
  render(<Teams />);
  expect(screen.getByText('Application Security Team')).toBeInTheDocument();
});

test('creates new team', async () => {
  render(<Teams />);
  fireEvent.click(screen.getByText('New Team'));
  // Fill form and submit
  // Verify team appears in list
});
```

---

### Integration Tests

**Workflow Test:**
```python
# tests/integration/test_portfolio_workflow.py
async def test_complete_portfolio_workflow():
    # 1. Create team
    team = await create_team("AppSec Team")
    
    # 2. Add members
    await add_team_members(team.id, [user1, user2])
    
    # 3. Create portfolio
    portfolio = await create_portfolio({
        "name": "Application Security",
        "team_id": team.id
    })
    
    # 4. Create initiative
    initiative = await create_initiative({
        "name": "Q2 Campaign",
        "portfolio_id": portfolio.id
    })
    
    # 5. Create activity linked to initiative
    activity = await create_activity({
        "title": "Demo",
        "initiative_id": initiative.id
    })
    
    # 6. Verify linkages
    assert activity.portfolio_id == portfolio.id
    assert initiative.activity_count == 1
```

---

## 📊 SUCCESS METRICS - PHASE 1

**Quantitative:**
- 3+ teams created
- 5+ portfolios defined
- 10+ initiatives launched
- 50+ activities linked to initiatives
- 100% team members assigned

**Qualitative:**
- Product Directors can manage portfolios independently
- CEO has visibility into all portfolios
- Sales team can link activities to strategic initiatives
- Clear traceability from activity → initiative → portfolio → team

**Performance:**
- Portfolio dashboard loads in <500ms
- Initiative progress calculated in real-time
- Team member operations <100ms

---

## 🔒 SECURITY & ACCESS CONTROL

### Role-Based Permissions

**product_director:**
- Create/edit/delete portfolios they own
- Create/edit/delete initiatives in their portfolios
- Assign goals to team members
- View team performance

**ceo:**
- View all portfolios
- View all initiatives
- Create strategic goals
- Cannot edit portfolios (view-only)

**sales_manager:**
- View assigned portfolios
- Create activities linked to initiatives
- View team KPIs
- Cannot create portfolios/initiatives

**sales_rep:**
- View activities assigned to them
- Complete activities and record outcomes
- View linked initiative progress
- Cannot create portfolios/initiatives

---

## 🎯 PHASE 1 COMPLETION CHECKLIST

**Backend:**
- [ ] Team model and routes implemented
- [ ] Portfolio model and routes implemented
- [ ] Initiative model and routes implemented
- [ ] Activity linkage fields added
- [ ] API documentation complete
- [ ] Unit tests written (80%+ coverage)
- [ ] Integration tests for workflows

**Frontend:**
- [ ] Teams page with CRUD
- [ ] Portfolios page with dashboard
- [ ] Initiatives page with kanban
- [ ] Activity creation with linkages
- [ ] All components responsive
- [ ] Navigation updated

**Database:**
- [ ] teams collection created with indexes
- [ ] portfolios collection created
- [ ] initiatives collection created
- [ ] activities collection migrated
- [ ] Data integrity constraints

**Documentation:**
- [ ] API documentation
- [ ] User guide for Product Directors
- [ ] User guide for CEO
- [ ] Developer guide for future enhancements

---

**PRD Complete - Ready for Implementation!** 📋

**Document End**
