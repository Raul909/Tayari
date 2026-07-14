# Product Requirements Document (PRD): Tayari Mobile App

## 1. Vision & Purpose
Tayari Mobile brings AI-powered flood early warnings directly to the hands of those who need it most in the IGAD region (farmers, pastoralists, community leaders). Unlike the web dashboard, the mobile app is optimized for challenging connectivity environments—acting as a fast, offline-capable lifeline.

## 2. Target Audience
- **Primary:** Rural farmers and pastoralists living in flood-prone basins (Shabelle, Juba, Tana).
- **Secondary:** Local county officers, NGO workers, and community coordinators managing disaster response.
- **Constraints:** Older Android devices (Android Go, 1-2GB RAM), older iOS devices, intermittent 2G/3G network coverage, expensive mobile data.

## 3. Core Features

### 3.1. Offline-First Architecture & Caching
- **Requirement:** Users must be able to view the last known flood forecast, risk level, and AI advisory even with zero internet connectivity.
- **Implementation:** Data fetched from the FastAPI backend is immediately cached locally using Isar Database. Map tiles are aggressively cached for offline viewing within a 50km radius of the user's primary basin.

### 3.2. Multilingual AI Advisories
- **Requirement:** Advisories translated by Claude (in the backend) must be available natively in the app.
- **Languages:** Somali, Swahili, Amharic, Oromo, English.
- **Offline Fallback:** If an updated advisory cannot be fetched, the app displays the most recent cached advisory with a clear timestamp ("Last synced 14 hours ago").

### 3.3. Low-Bandwidth Map Engine
- **Requirement:** Visualizing the flood zones without massive data overhead.
- **Implementation:** Flutter integration with MapLibre GL native (vector tiles). No expensive raster imagery. OpenFreeMap base tiles are cached locally.

### 3.4. Community Feedback Loop (Geotagged Reports)
- **Requirement:** Locals can submit ground-truth reports (e.g., "Water levels rising rapidly here").
- **Implementation:** 
  - Form to capture text + GPS coordinates + photo.
  - Photos are compressed aggressively *on-device* before upload (max 150KB per image).
  - Background sync: If offline, reports are queued and automatically uploaded when the device reconnects to a reliable network.

### 3.5. Push Notifications
- **Requirement:** Critical alerts (Risk level changes from MODERATE to HIGH) wake the device and notify the user immediately.
- **Implementation:** Firebase Cloud Messaging (FCM) linked to the user's selected basin and role.

## 4. Technical Constraints & Non-Functional Requirements
- **Framework:** Native Flutter (compiles to ARM Android & iOS binaries).
- **App Size:** The final APK/AAB must be strictly under 25MB to ensure it is cheap and fast to download over cellular networks.
- **Memory Footprint:** Efficient map disposal and state management to prevent Out Of Memory (OOM) crashes on low-end phones.
- **Battery Usage:** No constant background polling. Data sync occurs only on push notification triggers or when the app is explicitly opened by the user.
