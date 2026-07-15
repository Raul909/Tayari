# Tayari — Mobile App

The field-facing companion to **Tayari**, the flood early warning system. Built
with Flutter for low-bandwidth, offline-first use in the IGAD region.

## What's here

- **Dashboard** — a MapLibre map of the monitored basins with a live, cached
  basin list (risk level + flood probability). Tap a basin to open its detail.
- **Basin detail** — flood risk, an impact assessment (people, schools, health
  facilities at risk), and a role/language-tailored advisory. Everything is
  cached locally so it stays readable offline.
- **Community report** — snap a photo, auto-capture GPS, pick a condition, and
  submit. Reports are compressed, saved to a local queue, and uploaded to the
  backend as soon as there's a connection.

## Architecture

- **State:** Riverpod
- **Local store:** Isar (offline-first cache for basins, forecasts, and the
  report upload queue)
- **Networking:** Dio → the FastAPI backend
- **Map:** `maplibre_gl` (tiles from OpenFreeMap)
- **Media/Location:** `image_picker`, `geolocator`, `flutter_image_compress`

Basins and forecasts are read from Isar and rendered immediately; a background
sync refreshes them from the API when reachable.

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

## Permissions

Camera and location are required to submit geotagged reports. The app requests
them at the point of use.

## Note

If you change the Isar models (`lib/models/*.dart`), regenerate the adapters:

```bash
dart run build_runner build --delete-conflicting-outputs
```
