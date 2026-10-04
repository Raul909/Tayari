# Tayari — Mobile App

The field-facing companion to **Tayari**, the multi-hazard early warning system.
Built with Flutter for low-bandwidth, offline-first use in the field.

## What's here

Four tabs along the bottom:

- **My area** (opens here) — use your location or search any town, and Tayari
  checks nine hazards there: flooding, earthquake, tsunami, volcanic activity,
  storms, heat, wildfire, drought and landslide. A plain-words banner gives the
  answer (*All clear for now*, *Stay alert*, *Take action*) with one tap to what
  to do about the most urgent hazard. Each hazard opens to advice for your role
  and language first, then the readings behind it. The last place and result are
  kept on the phone and shown instantly — with their age — so the screen is
  useful offline.
- **Basins** — the eight calibrated river basins on a MapLibre map with a
  cached list (risk level + flood probability). Tap a basin for its flood risk,
  impact assessment and a role/language-tailored advisory, all readable offline.
- **Reports** — community reports with advice threads. Snap a photo, capture
  GPS, pick a condition and submit; reports are compressed, queued locally and
  uploaded as soon as there's a connection.
- **Settings** — your role, language and home basin, plus feedback.

## Architecture

- **State:** Riverpod
- **Local store:** Isar (offline-first cache for basins, forecasts, and the
  report upload queue)
- **Networking:** Dio → the FastAPI backend
- **Map:** `maplibre_gl` (tiles from OpenFreeMap)
- **Media/Location:** `image_picker`, `geolocator`, `flutter_image_compress`

Basins and forecasts are read from Isar and rendered immediately; a background
sync refreshes them from the API when reachable. The multi-hazard profile
(`lib/services/hazard_api.dart`) uses the same `/api/hazards` endpoints as the
web app, with longer timeouts than the basin client because a place nobody has
asked about yet gathers seven live feeds, and a cold server start adds to that.

## Running

Start the backend first (see the root `README.md`), then:

```bash
flutter pub get
flutter run
```

### Pointing at the backend

The base URL resolves automatically per platform:

- **Android emulator** → `http://10.0.2.2:8000/api` (host loopback)
- **iOS simulator / desktop / web** → `http://127.0.0.1:8000/api`

For a physical device, override it:

```bash
flutter run --dart-define=API_BASE_URL=http://<your-computer-ip>:8000/api
```

## Tests

```bash
flutter test
```

## Permissions

Location is used for *My area* and to geotag reports; photos go through the
system camera app. Both are requested only when you tap the action that needs
them.

## Note

If you change the Isar models (`lib/models/*.dart`), regenerate the adapters:

```bash
dart run build_runner build --delete-conflicting-outputs
```
