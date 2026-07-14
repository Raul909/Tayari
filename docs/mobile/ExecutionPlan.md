# Execution & Development Plan: Tayari Mobile App

This document outlines the step-by-step strategy for building the Tayari native mobile app using Flutter, ensuring a highly optimized, low-bandwidth, and offline-capable deliverable suitable for the IGAD region constraints.

## 1. Project Initialization & Tooling
- **Framework:** Flutter (latest stable release).
- **State Management:** Riverpod 2.0 (for predictable, reactive state tied to local DB).
- **Local Database:** Isar Database (extremely fast, typed NoSQL engine for Flutter, optimized for heavy offline read/writes).
- **Networking:** Dio (with interceptors for retry logic and network-state checking).
- **Mapping:** `maplibre_gl` Flutter package.

## 2. Development Phases

### Phase 1: Core Foundation & Offline Scaffolding (Days 1-3)
1. **Repository Setup:** Scaffold the Flutter project within `mobile/` directory.
2. **Isar Schema Design:** Create the local collections for `BasinForecast`, `CommunityReport`, and `Advisory`.
3. **Sync Engine:** Implement the background `SyncService` that fetches from the FastAPI backend and upserts into Isar.
4. **Theme & Localization:** Set up the color system (matching the Next.js web app) and the `intl` package for Somali, Swahili, Amharic, Oromo, and English string translations.

### Phase 2: User Interface & Maps (Days 4-7)
1. **Dashboard UI:** Build the main basin selector and the animated Risk Gauge.
2. **MapLibre Integration:** Integrate the native map viewer.
3. **Offline Tiles:** Implement the logic to pre-cache the OpenFreeMap vector tiles for the user's primary selected basin.
4. **Advisory View:** Build the language and role selector for the AI advisories.

### Phase 3: Community Reporting & Optimization (Days 8-10)
1. **Camera & Forms:** Build the community report submission UI.
2. **Image Compression:** Implement `flutter_image_compress` to aggressively shrink photos (e.g., from 5MB to 100KB) before saving to the pending queue.
3. **Offline Queue Sync:** Implement the logic that detects network restoration (`connectivity_plus`) and flushes the pending upload queue to the FastAPI backend.

### Phase 4: Push Notifications & Release (Days 11-14)
1. **Firebase Integration:** Add `firebase_messaging` for FCM.
2. **Background Handlers:** Write the Dart background isolates that process silent push notifications, sync Isar, and trigger local alarms.
3. **APK Generation & Profiling:**
   - Run Flutter DevTools to ensure memory usage is <150MB.
   - Use `flutter build apk --split-per-abi` to generate minimal binaries (targeting ~15-20MB).

## 3. Bundle Size Optimization Strategies
Given the high cost of mobile data in rural IGAD regions, the app size must be minimized:
- **Vector over Raster:** Using MapLibre vector maps eliminates the need to download large raster image files.
- **Font Subsetting:** Include only necessary glyphs for custom fonts.
- **Split ABIs:** Delivering `armeabi-v7a` and `arm64-v8a` separately reduces APK size by up to 50% compared to a fat APK.
