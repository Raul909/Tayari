import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import '../../models/report.dart';
import '../../providers/db_provider.dart';

class ReportScreen extends ConsumerStatefulWidget {
  final String basinId;
  const ReportScreen({super.key, required this.basinId});

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  final ImagePicker _picker = ImagePicker();
  File? _imageFile;
  Position? _position;
  String _status = 'Water rising';
  bool _isSubmitting = false;

  Future<void> _takePhoto() async {
    final XFile? photo = await _picker.pickImage(source: ImageSource.camera);
    if (photo != null) {
      setState(() => _imageFile = File(photo.path));
      _getLocation(); // Fetch location automatically when photo is taken
    }
  }

  Future<void> _getLocation() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return;

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return;
    }

    if (permission == LocationPermission.deniedForever) return;

    Position position = await Geolocator.getCurrentPosition();
    setState(() => _position = position);
  }

  Future<void> _submitReport() async {
    if (_imageFile == null || _position == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Please take a photo and allow location.")),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      // 1. Compress Image Aggressively (PRD Requirement for low bandwidth)
      final dir = await getApplicationDocumentsDirectory();
      final targetPath = '${dir.path}/compressed_${DateTime.now().millisecondsSinceEpoch}.jpg';
      
      final XFile? compressedFile = await FlutterImageCompress.compressAndGetFile(
        _imageFile!.path,
        targetPath,
        quality: 50, // 50% quality to reduce to ~100kb
        minWidth: 800,
        minHeight: 800,
      );

      // 2. Save to Isar Offline Queue
      final report = CommunityReport()
        ..basinId = widget.basinId
        ..latitude = _position!.latitude
        ..longitude = _position!.longitude
        ..status = _status
        ..compressedPhotoPath = compressedFile?.path ?? _imageFile!.path
        ..createdAt = DateTime.now()
        ..isSynced = false; // Important: Saved for background offline sync

      final isar = await ref.read(isarProvider.future);
      await isar.writeTxn(() async {
        await isar.communityReports.put(report);
      });

      // 3. Trigger SyncService in background
      ref.read(syncServiceProvider.future).then((service) => service.syncPendingReports());

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Report saved offline and will sync soon!")),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Error: $e")));
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Community Report")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_imageFile != null)
              Expanded(child: Image.file(_imageFile!, fit: BoxFit.cover))
            else
              Expanded(
                child: Container(
                  color: Colors.blueGrey.withOpacity(0.2),
                  child: Center(
                    child: IconButton(
                      icon: const Icon(Icons.camera_alt, size: 64),
                      onPressed: _takePhoto,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            if (_position != null)
              Text("📍 Location captured: ${_position!.latitude.toStringAsFixed(4)}, ${_position!.longitude.toStringAsFixed(4)}", style: const TextStyle(color: Colors.green)),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _status,
              decoration: const InputDecoration(labelText: "Current Condition"),
              items: const [
                DropdownMenuItem(value: 'Water rising', child: Text("Water rising rapidly")),
                DropdownMenuItem(value: 'Road flooded', child: Text("Road is flooded")),
                DropdownMenuItem(value: 'All clear', child: Text("Water levels normal")),
              ],
              onChanged: (val) => setState(() => _status = val!),
            ),
            const SizedBox(height: 32),
            ElevatedButton(
              onPressed: _isSubmitting ? null : _submitReport,
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
              child: _isSubmitting
                  ? const CircularProgressIndicator()
                  : const Text("Save & Sync Report", style: TextStyle(fontSize: 18)),
            ),
          ],
        ),
      ),
    );
  }
}
