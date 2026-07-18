# Changelog

All notable changes to the Tayari Mobile App will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Each version corresponds to a `v*` git tag; pushing a tag builds and publishes the
split-per-ABI release APKs via the "Build and Release APK" workflow.

## [1.5.0] - 2026-07-19
### Added
- **Teacher and Student audiences.** Advisories can now be written for a teacher
  (safety of students and school property) or a student, alongside the existing
  farmer, pastoralist, county-officer, community-leader and general roles.

### Changed
- **Clearer, leak-free translations.** Non-English advisories are now checked for
  foreign-script characters and untranslated English, retried once when a leak is
  found, and scrubbed of any stray glyph before display — so problems like a
  Chinese character slipping into an Arabic advisory, or "within 2 days" left in a
  Somali one, no longer reach readers.
- The on-device advisory fallback now covers all 11 supported languages (it
  previously defaulted six of them to English when the backend was unreachable).

### Fixed
- **Advisory card no longer shows up empty.** When the backend serves a basin
  forecast without an inline advisory, the app now fetches it from the dedicated
  advisory endpoint instead of leaving the card blank.

## [1.4.1] - 2026-07-17
### Fixed
- **Release build (APK):** Removed a machine-specific `org.gradle.java.home`
  override from `android/gradle.properties` that pinned a local macOS JDK path
  (`/Library/Java/JavaVirtualMachines/jdk-25.jdk`). It broke the Ubuntu CI build
  with *"Java home supplied is invalid"*, so **1.4.0 never produced an APK**. The
  Android build now resolves the JDK from the environment and targets Java 21 on
  any machine.

### Changed
- Synced the app's internal version (`pubspec.yaml`) with the release-tag series
  — it had drifted to `1.2.1+5` while tags advanced to `v1.4.x`.

## [1.4.0] - 2026-07-17
> The APK for this tag failed to build in CI (see 1.4.1). Install **1.4.1**,
> which ships the same app plus the build fix.

### Added
- Per-endpoint API rate limiting to keep the backend stable under load.
- Optimized cron ping schedule to reduce redundant wake-ups.

### Fixed
- Corrected population-at-risk figures end-to-end so basin exposure numbers match
  official estimates.

## [1.3.0] - 2026-07-17
### Added
- Community advice threads: responders can reply to field reports in-app.
- Supabase phone authentication for secure alert dispatch.
- Two-step LLM translation pipeline with Hugging Face TTS voice notes for
  multilingual advisories.
- Responsive layouts and a chat-based advisory assistant.

### Fixed
- Mobile map and camera stability on low-end Android (cooperative gestures,
  resize handling).

## [1.2.0] - 2026-07-16
### Added
- Initial public release of the Tayari Mobile App.
- Core map visualization with flood-risk gradients across five African basins.
- Multilingual advisory fetching with on-device owner preferences (Isar).
- Community reporting with photo capture and geolocation.
