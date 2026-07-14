# 📱 Tayari Mobile App Architecture

Welcome to the Mobile Architecture branch of the Tayari project! 

While the main branch contains the FastAPI backend and Next.js PWA web dashboard, this directory outlines the comprehensive architectural blueprint for the **native mobile application**, designed specifically for the challenging operational constraints of the IGAD region (low connectivity, older devices, high data costs).

## 📄 Documentation Index

We have prepared three detailed documents outlining how this app will be built, function, and operate:

1. **[Product Requirements Document (PRD)](PRD.md)**
   - Details the target audience, core features (offline-first, multilingual advisories, low-bandwidth maps), and critical non-functional constraints.

2. **[Data Flow Architecture](DataFlow.md)**
   - Provides a sequence diagram and deep dive into the aggressive caching strategy using Isar DB. It explains how the app minimizes HTTP requests and handles offline queueing for community reports.

3. **[Execution & Development Plan](ExecutionPlan.md)**
   - Outlines the step-by-step technical execution, tech stack choices (Flutter, Riverpod, Isar), and strategies for aggressive bundle size reduction to keep the APK under 20MB.

## 🛠️ Tech Stack Summary

- **Framework:** Native Flutter (compiled to ARM binaries)
- **Local DB:** Isar Database (for offline caching)
- **Mapping:** MapLibre GL Native (vector tiles)
- **State Management:** Riverpod 2.0
- **Push Notifications:** Firebase Cloud Messaging (FCM)
