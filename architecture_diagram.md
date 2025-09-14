# 🏗️ Architecture Diagrams for Presentation

## System Architecture Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[HTML/CSS/JS]
        B[Bootstrap Framework]
        C[Responsive Design]
    end

    subgraph "Backend Layer"
        D[Flask Application]
        E[Business Logic]
        F[Authentication]
        G[Email Service]
    end

    subgraph "AI Processing Layer"
        H[Google Gemini AI]
        I[OpenRouter API]
        J[Vector Store FAISS]
        K[Knowledge Base]
    end

    subgraph "Data Layer"
        L[PostgreSQL Database]
        M[File Storage]
        N[Cache System]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    D --> F
    D --> G
    E --> H
    E --> I
    H --> J
    I --> J
    J --> K
    D --> L
    E --> L
    D --> M
    E --> N
```

## User Workflow Diagram

```mermaid
flowchart TD
    A[Candidate Visits Site] --> B{User Type?}
    B -->|New User| C[Register Account]
    B -->|Existing| D[Login]

    C --> E[Upload CV]
    D --> E

    E --> F[AI CV Analysis]
    F --> G[Skills Extraction]
    G --> H[Job Matching Algorithm]

    H --> I[View Matched Jobs]
    I --> J[Apply to Job]
    J --> K[Submit Application]

    K --> L[Recruiter Review]
    L --> M{Send Test?}
    M -->|Yes| N[Generate AI Questions]
    M -->|No| O[Direct Interview]

    N --> P[Send Test Email]
    P --> Q[Candidate Takes Test]
    Q --> R[AI Evaluation]
    R --> S[Generate Score & Feedback]

    S --> T[Recruiter Dashboard]
    T --> U[Review Results]
    U --> V{Decision}
    V -->|Accept| W[Send Offer]
    V -->|Reject| X[Send Rejection]
    V -->|Interview| Y[Schedule Interview]

    O --> Z[Traditional Process]
```

## Database Schema Diagram

```mermaid
erDiagram
    USERS ||--o{ RECRUITERS : "inherits"
    USERS ||--o{ CANDIDATES : "inherits"
    USERS ||--o{ ADMINS : "inherits"

    USERS {
        int id PK
        string username
        string email
        string password_hash
        string role
        datetime created_at
        datetime updated_at
    }

    RECRUITERS {
        int id PK,FK
        string profile_picture
        string company
        text bio
    }

    CANDIDATES {
        int id PK,FK
        string phone
        string location
        text bio
    }

    ADMINS {
        int id PK,FK
        string permissions
    }

    COMPANIES ||--o{ JOBS : "has"
    COMPANIES {
        int id PK
        string name
        string website
        string industry
        string size
        boolean remote_friendly
    }

    JOBS ||--o{ APPLICATIONS : "receives"
    JOBS {
        int id PK
        int company_id FK
        int recruiter_id FK
        string title
        text description
        string location
        string type
        decimal salary_from
        decimal salary_to
        string currency
        json skills
        datetime posted
        string status
    }

    APPLICATIONS ||--o{ RESUMES : "has"
    APPLICATIONS ||--o{ TESTS : "triggers"
    APPLICATIONS {
        int id PK
        int job_id FK
        int candidate_id FK
        datetime applied_at
        string status
        text cover_letter
    }

    RESUMES {
        int id PK
        int application_id FK
        string file_path
        text extracted_text
        json parsed_data
        datetime uploaded_at
    }

    TESTS ||--o{ QUESTIONS : "contains"
    TESTS ||--o{ ANSWERS : "receives"
    TESTS {
        int id PK
        int application_id FK
        string status
        datetime created_at
        datetime sent_at
        datetime completed_at
    }

    QUESTIONS {
        int id PK
        int test_id FK
        text question
        text correct_answer
        string difficulty
        json metadata
    }

    ANSWERS {
        int id PK
        int test_id FK
        int question_id FK
        text candidate_answer
        decimal score
        json evaluation
        text justification
    }
```

## AI Processing Pipeline

```mermaid
flowchart LR
    A[CV Upload] --> B[File Validation]
    B --> C[Text Extraction]
    C --> D[Preprocessing]
    D --> E[AI Analysis]

    E --> F[Skills Detection]
    E --> G[Experience Analysis]
    E --> H[Education Parsing]

    F --> I[JSON Output]
    G --> I
    H --> I

    I --> J[Database Storage]
    J --> K[Job Matching]
    K --> L[Results Display]
```

## Technology Stack Overview

```mermaid
mindmap
  root((Entretien Automatisé))
    Backend
      Flask
        Routes
        Controllers
        Middleware
      SQLAlchemy
        ORM
        Migrations
        Query Builder
      PostgreSQL
        Tables
        Relationships
        Indexes
    Frontend
      HTML5
        Semantic
        Accessible
      CSS3
        Responsive
        Modern
      JavaScript
        ES6+
        Async/Await
        DOM Manipulation
    AI Integration
      Google Gemini
        CV Analysis
        Question Generation
        Answer Evaluation
      OpenRouter
        Fallback API
        Multi-model
      FAISS
        Vector Search
        Similarity Matching
    DevOps
      Git
        Version Control
        Branching
      Docker
        Containerization
        Environment
      Testing
        Unit Tests
        Integration
        E2E
```

## Security Architecture

```mermaid
flowchart TD
    A[User Request] --> B{WAF Protection}
    B --> C{CSRF Token Valid?}
    C --> D{Session Valid?}
    D --> E{Role Authorized?}

    B -->|Blocked| F[403 Forbidden]
    C -->|Invalid| F
    D -->|Invalid| G[401 Unauthorized]
    E -->|No| H[403 Forbidden]

    E -->|Yes| I[Business Logic]
    I --> J[Database Query]
    J --> K[Response]

    K --> L{Input Sanitized?}
    L --> M[Safe Response]
    L --> N[Sanitized Response]
```

## Performance Metrics Dashboard

```mermaid
graph LR
    A[Application Metrics] --> B[Response Time]
    A --> C[Error Rate]
    A --> D[Throughput]
    A --> E[CPU Usage]
    A --> F[Memory Usage]

    B --> G[< 2s Target]
    C --> H[< 1% Target]
    D --> I[100 req/min]
    E --> J[< 15% Target]
    F --> K[< 256MB Target]

    G --> L[Monitoring]
    H --> L
    I --> L
    J --> L
    K --> L
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Production Environment"
        A[Load Balancer]
        B[Web Server 1]
        B2[Web Server 2]
        C[Application Server]
        D[Database Server]
        E[Cache Server]
        F[File Storage]
    end

    subgraph "External Services"
        G[Google Gemini AI]
        H[OpenRouter API]
        I[Gmail SMTP]
        J[Monitoring Tools]
    end

    A --> B
    A --> B2
    B --> C
    B2 --> C
    C --> D
    C --> E
    C --> F

    C --> G
    C --> H
    C --> I
    C --> J
```

## API Architecture

```mermaid
sequenceDiagram
    participant C as Client
    participant F as Flask App
    participant A as AI Service
    participant D as Database
    participant E as Email Service

    C->>F: POST /upload-cv
    F->>F: Validate File
    F->>A: Send to AI Analysis
    A-->>F: CV Parsed Data
    F->>D: Store CV Data
    F-->>C: Success Response

    C->>F: POST /apply/<job_id>
    F->>F: Validate Application
    F->>D: Save Application
    F->>E: Send Confirmation Email
    F-->>C: Application Submitted

    C->>F: GET /recruiter/dashboard
    F->>D: Fetch User Data
    F->>D: Fetch Applications
    F->>D: Fetch Statistics
    F-->>C: Dashboard Data
```

## Future Roadmap

```mermaid
timeline
    title Future Development Roadmap
    section Phase 1 (Current)
        Completed : Core Features
                    : AI Integration
                    : Basic UI/UX
                    : Database Setup
    section Phase 2 (3-6 months)
        Mobile App : React Native
                    : Push Notifications
                    : Offline Mode
        Advanced AI : Custom Models
                     : Better Matching
                     : Predictive Analytics
    section Phase 3 (6-12 months)
        Multi-tenant : SaaS Platform
                     : White-label
                     : API Marketplace
        Integrations : ATS Systems
                     : HR Software
                     : Video Platforms
    section Phase 4 (1-2 years)
        Global Scale : Multi-region
                     : Microservices
                     : Advanced ML
        Industry Focus : Healthcare
                       : Finance
                       : Tech-specific
```

## Code Quality Metrics

```mermaid
pie title Code Quality Distribution
    "Well Tested" : 25
    "Well Documented" : 20
    "Maintainable" : 30
    "Scalable" : 15
    "Needs Improvement" : 10
```

## User Journey Map

```mermaid
journey
    title Candidate User Journey
    section Discovery
      Visit Website : 5 : Visitor
      Browse Jobs : 4 : Interested
      Upload CV : 3 : Engaged
    section Application
      Find Matches : 5 : Excited
      Apply to Job : 5 : Committed
      Receive Confirmation : 4 : Satisfied
    section Testing
      Get Test Invite : 4 : Nervous
      Take Technical Test : 3 : Focused
      Submit Answers : 4 : Hopeful
    section Results
      Receive Score : 5 : Anxious
      Get Feedback : 4 : Learning
      Interview Invite : 5 : Successful
```

## Risk Assessment Matrix

```mermaid
quadrantChart
    title Risk Assessment
    x-axis Low Impact --> High Impact
    y-axis Low Probability --> High Probability
    quadrant-1 Critical Risks
    quadrant-2 High Priority
    quadrant-3 Medium Priority
    quadrant-4 Low Priority

    AI API Failure: [0.8, 0.9]
    Data Breach: [0.9, 0.7]
    User Adoption: [0.6, 0.8]
    Performance Issues: [0.7, 0.6]
    Integration Problems: [0.5, 0.7]
    Cost Overrun: [0.6, 0.5]
```

## Technology Radar

```mermaid
radar
    title Technology Adoption
    axes Python, Flask, PostgreSQL, AI/ML, React, Docker, Kubernetes, GraphQL
    axis Python : 5
    axis Flask : 4
    axis PostgreSQL : 4
    axis AI/ML : 5
    axis React : 2
    axis Docker : 3
    axis Kubernetes : 1
    axis GraphQL : 1
```

## Cost-Benefit Analysis

```mermaid
bar
    title Cost-Benefit Analysis (6 months)
    x-axis Development, Maintenance, AI APIs, Infrastructure, Training
    y-axis Cost (€)
    bar Development : 15000
    bar Maintenance : 3000
    bar AI APIs : 2000
    bar Infrastructure : 1000
    bar Training : 500

    bar Benefits : 25000
    bar Time Savings : 18000
    bar Quality Improvement : 12000
    bar User Satisfaction : 8000
    bar Competitive Advantage : 15000
```

## Performance Benchmarks

```mermaid
gantt
    title Development Timeline
    dateFormat YYYY-MM-DD
    section Planning
        Requirements Gathering : done, req, 2024-01-01, 2024-01-15
        Architecture Design : done, arch, 2024-01-15, 2024-02-01
    section Development
        Backend Development : done, backend, 2024-02-01, 2024-03-15
        Frontend Development : done, frontend, 2024-02-15, 2024-03-30
        AI Integration : done, ai, 2024-03-01, 2024-04-15
    section Testing
        Unit Testing : done, unit, 2024-04-01, 2024-04-30
        Integration Testing : done, integration, 2024-04-15, 2024-05-15
        User Acceptance : done, uat, 2024-05-01, 2024-05-30
    section Deployment
        Production Setup : active, prod, 2024-05-15, 2024-06-15
        Go-Live : milestone, golive, 2024-06-15, 1d
```

---

## 📊 Presentation Tips

### For Technical Audience:
1. **Focus on Architecture** - Show system design decisions
2. **Explain Trade-offs** - Why certain technologies were chosen
3. **Demonstrate Code Quality** - Show best practices implemented
4. **Highlight Scalability** - How the system can grow
5. **Discuss Performance** - Metrics and optimization techniques

### Visual Best Practices:
1. **Use Consistent Colors** - Black/white theme throughout
2. **Include Code Snippets** - Show actual implementation
3. **Add Architecture Diagrams** - Visual system representation
4. **Include Screenshots** - Real application interfaces
5. **Use Icons Consistently** - Professional iconography

### Content Structure:
1. **Start with Problem** - Why this project exists
2. **Show Solution** - How the system addresses the problem
3. **Dive Deep** - Technical implementation details
4. **Demonstrate Value** - Business and technical benefits
5. **End with Future** - Roadmap and improvements

---

**These diagrams provide visual representations of your system architecture, workflows, and technical decisions. Use them in your PDF presentation to make complex concepts more understandable for your technical audience.**